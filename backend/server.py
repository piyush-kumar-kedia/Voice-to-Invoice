from fastapi import FastAPI, APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response as FastAPIResponse, HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import requests
import io
from emergentintegrations.llm.chat import LlmChat, UserMessage
import razorpay
from pdf_generator import generate_invoice_pdf
from translations import translate, get_whatsapp_messages
from email_service import send_invoice_email

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Twilio setup
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'your_twilio_account_sid_here')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_twilio_auth_token_here')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# Emergent LLM Key for text generation (GPT-4o)
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# AssemblyAI API Key for speech-to-text transcription
ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dummykey123456789')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'razorpay_test_secret_dummy123')
RAZORPAY_TEST_MODE = os.environ.get('RAZORPAY_TEST_MODE', 'True').lower() == 'true'

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Create the main app
app = FastAPI(title="VoiceBill API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Models ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone: str
    name: str
    business_name: str
    language: str = "en"  # en, hi
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    phone: str
    name: str
    business_name: str
    language: str = "en"

class Customer(BaseModel):
    """Customer database model"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Shopkeeper who added this customer
    name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    total_purchases: float = 0.0
    total_due: float = 0.0  # Outstanding amount
    language: str = "en"
    notes: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_purchase: Optional[datetime] = None

class CustomerCreate(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    language: str = "en"
    notes: Optional[str] = ""

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    price: float
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    user_id: str
    name: str
    price: float
    description: Optional[str] = ""

class InvoiceItem(BaseModel):
    name: str
    quantity: float
    price: float
    total: float

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    customer_id: Optional[str] = None  # Link to customer database
    invoice_number: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    customer_name: Optional[str] = "Walk-in Customer"
    customer_phone: Optional[str] = ""
    customer_email: Optional[str] = ""
    customer_address: Optional[str] = ""
    items: List[InvoiceItem]
    subtotal: float
    tax_rate: float = 0.0
    tax: float
    total: float
    amount_paid: float = 0.0  # Amount paid so far
    amount_due: float = 0.0  # Remaining amount
    status: str = "unpaid"  # unpaid, paid, partial
    payment_status: str = "pending"  # pending, completed
    payment_link: Optional[str] = ""
    payment_id: Optional[str] = ""
    transcription: Optional[str] = ""
    language: str = "en"  # Invoice language
    email_sent: bool = False  # Track if email was sent
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PendingInvoice(BaseModel):
    """Temporary storage for invoices awaiting price information"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    customer_name: str
    items: List[dict]  # Items with quantities but missing prices
    transcription: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceCreate(BaseModel):
    user_id: str
    customer_name: Optional[str] = "Walk-in Customer"
    customer_phone: Optional[str] = ""
    items: List[InvoiceItem]
    tax_rate: float = 0.0

# ==================== Helper Functions ====================

async def find_customer_by_name(user_id: str, customer_name: str):
    """Find customer by name with fuzzy matching for typos"""
    try:
        from difflib import SequenceMatcher
        
        # Try exact match first
        customer = await db.customers.find_one(
            {"user_id": user_id, "name": {"$regex": f"^{customer_name}$", "$options": "i"}},
            {"_id": 0}
        )
        
        if customer:
            logger.info(f"Found exact customer match: {customer['name']}")
            return customer
        
        # Try partial match
        customer = await db.customers.find_one(
            {"user_id": user_id, "name": {"$regex": customer_name, "$options": "i"}},
            {"_id": 0}
        )
        
        if customer:
            logger.info(f"Found partial customer match: {customer['name']}")
            return customer
        
        # Check default customers with exact match
        customer = await db.customers.find_one(
            {"user_id": "default-user", "name": {"$regex": f"^{customer_name}$", "$options": "i"}},
            {"_id": 0}
        )
        
        if customer:
            logger.info(f"Found customer in shared database: {customer['name']}")
            return customer
        
        # Fuzzy matching - get all customers and find best match
        all_customers = await db.customers.find(
            {"$or": [{"user_id": user_id}, {"user_id": "default-user"}]},
            {"_id": 0}
        ).to_list(100)
        
        best_match = None
        best_ratio = 0.0
        
        for cust in all_customers:
            ratio = SequenceMatcher(None, customer_name.lower(), cust['name'].lower()).ratio()
            if ratio > best_ratio and ratio >= 0.7:  # 70% similarity threshold
                best_ratio = ratio
                best_match = cust
        
        if best_match:
            logger.info(f"Found fuzzy customer match: '{customer_name}' → '{best_match['name']}' (similarity: {best_ratio:.2f})")
            return best_match
        
        logger.info(f"No customer match found for: {customer_name}")
        return None
    except Exception as e:
        logger.error(f"Error finding customer: {str(e)}")
        return None

async def get_or_create_user(phone: str) -> User:
    """Get existing user or create a new one"""
    phone_clean = phone.replace("whatsapp:", "")
    user_doc = await db.users.find_one({"phone": phone_clean}, {"_id": 0})
    
    if user_doc:
        if isinstance(user_doc['created_at'], str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        return User(**user_doc)
    
    # Create new user
    new_user = User(
        phone=phone_clean,
        name=f"User {phone_clean[-4:]}",
        business_name=f"Business {phone_clean[-4:]}"
    )
    doc = new_user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    return new_user

async def transcribe_audio(audio_url: str) -> str:
    """Transcribe audio using AssemblyAI"""
    try:
        # Download audio from Twilio
        response = requests.get(audio_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        response.raise_for_status()
        
        audio_content = response.content
        logger.info(f"Downloaded audio: {len(audio_content)} bytes")
        
        # Save audio temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name
        
        try:
            # Use AssemblyAI for transcription
            import assemblyai as aai
            
            aai.settings.api_key = ASSEMBLYAI_API_KEY
            
            # Create transcriber
            transcriber = aai.Transcriber()
            
            # Transcribe the audio file
            transcript = transcriber.transcribe(temp_audio_path)
            
            # Check if transcription was successful
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"AssemblyAI transcription error: {transcript.error}")
                return "[Transcription failed]"
            
            transcription_text = transcript.text or "[No speech detected]"
            logger.info(f"Transcription successful: {transcription_text}")
            return transcription_text
            
        finally:
            # Clean up temporary file
            import os as os_module
            try:
                os_module.unlink(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return "[Transcription failed]"

async def extract_invoice_data(transcription: str, user_id: str):
    """Extract invoice items from transcription using GPT-4o, product catalog, and customer database"""
    try:
        # Get user's products AND default/shared products
        user_products = await db.products.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        default_products = await db.products.find({"user_id": "default-user"}, {"_id": 0}).to_list(1000)
        
        # Combine both catalogs (user products take priority)
        all_products = default_products + user_products
        product_catalog = {}
        for p in all_products:
            product_catalog[p['name'].lower()] = p['price']
        
        logger.info(f"Loading catalog for user {user_id}: {len(user_products)} user products, {len(default_products)} shared products")
        logger.info(f"Combined catalog: {product_catalog}")
        
        # Get customer list for matching
        customers = await db.customers.find(
            {"$or": [{"user_id": user_id}, {"user_id": "default-user"}]},
            {"_id": 0}
        ).to_list(100)
        customer_names = [c['name'] for c in customers]
        
        customer_info = ""
        if customer_names:
            customer_info = f"\n\nKnown customers: {', '.join(customer_names[:20])}"
            logger.info(f"Passing customer list to GPT: {customer_names}")
        
        # Create a mapping for fuzzy matching (handle plurals and variations)
        def find_catalog_price(item_name: str):
            """Find price in catalog with fuzzy matching"""
            item_lower = item_name.lower().strip()
            
            # Direct match
            if item_lower in product_catalog:
                return product_catalog[item_lower]
            
            # Try removing common plural suffixes
            for suffix in ['s', 'es', 'ies']:
                if item_lower.endswith(suffix):
                    singular = item_lower[:-len(suffix)]
                    if suffix == 'ies':
                        singular = singular + 'y'
                    if singular in product_catalog:
                        logger.info(f"Matched '{item_name}' to '{singular}' in catalog")
                        return product_catalog[singular]
            
            # Try adding 's' (reverse check)
            plural = item_lower + 's'
            if plural in product_catalog:
                logger.info(f"Matched '{item_name}' to '{plural}' in catalog")
                return product_catalog[plural]
            
            # Partial match
            for catalog_item, price in product_catalog.items():
                if catalog_item in item_lower or item_lower in catalog_item:
                    logger.info(f"Partial match '{item_name}' to '{catalog_item}' in catalog")
                    return price
            
            return None
        
        # Create context for GPT with product catalog and customer list
        catalog_info = ""
        if product_catalog:
            catalog_info = f"\n\nAvailable products in catalog:\n"
            for name, price in product_catalog.items():
                catalog_info += f"- {name}: Rs. {price}\n"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"invoice_{user_id}_{datetime.now().timestamp()}",
            system_message=f"""You are an invoice extraction assistant. Extract billing information from voice transcriptions.
            
{catalog_info}{customer_info}

IMPORTANT: Return a JSON object with:
{{
  "customer_name": "EXACT customer name if mentioned (including 'to <name>', 'for <name>'), otherwise 'Walk-in Customer'",
  "items": [
    {{"name": "item name (normalized/singular)", "quantity": number, "price": null}}
  ]
}}

CRITICAL RULES FOR CUSTOMER NAME:
1. Look for patterns: "to <name>", "for <name>", "sold to <name>", "customer <name>"
2. Extract the EXACT name mentioned in transcription (even if misspelled)
3. Examples:
   - "sold 20 rice to piyush" → customer_name: "piyush"
   - "sold 20 rice and five almond to peyush" → customer_name: "peyush"
   - "for Rajesh" → customer_name: "Rajesh"
   - "sold 20 rice" → customer_name: "Walk-in Customer"

CRITICAL RULES FOR ITEMS & PRICES:
1. **ALWAYS set price to null** for items that might be in the catalog
2. **ONLY include a price number** if the user explicitly mentions a price in the transcription
3. Normalize to singular form (e.g., "rices" → "rice", "bags of rice" → "rice")
4. Extract accurate quantities

DO NOT guess prices. Set price to null if not explicitly mentioned.

Examples:
- "sold 2 rice to Rajesh Kumar" → {{"customer_name": "Rajesh Kumar", "items": [{{"name": "rice", "quantity": 2, "price": null}}]}}
- "sold 20 rice to piyush" → {{"customer_name": "piyush", "items": [{{"name": "rice", "quantity": 20, "price": null}}]}}
- "sold 2 rice" → {{"customer_name": "Walk-in Customer", "items": [{{"name": "rice", "quantity": 2, "price": null}}]}}
- "two rices for Amit" → {{"customer_name": "Amit", "items": [{{"name": "rice", "quantity": 2, "price": null}}]}}
- "sold 2 rice at 600 each" → {{"customer_name": "Walk-in Customer", "items": [{{"name": "rice", "quantity": 2, "price": 600}}]}}"""
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(
            text=f"Extract invoice items from this voice note transcription: {transcription}"
        )
        
        response = await chat.send_message(user_message)
        
        # Parse the response
        import json
        response_text = response.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        invoice_data = json.loads(response_text)
        
        logger.info(f"GPT extracted data: {invoice_data}")
        logger.info(f"Product catalog: {product_catalog}")
        
        # Apply catalog prices for items with null prices using fuzzy matching
        missing_prices = []
        for item in invoice_data.get("items", []):
            logger.info(f"Processing item: {item['name']}, price: {item.get('price')}")
            if item.get("price") is None:
                catalog_price = find_catalog_price(item['name'])
                if catalog_price is not None:
                    item['price'] = catalog_price
                    logger.info(f"✓ Using catalog price for '{item['name']}': Rs. {item['price']}")
                else:
                    logger.info(f"✗ No catalog match for '{item['name']}'")
                    missing_prices.append(item['name'])
        
        # Find customer in database if name mentioned
        customer_name = invoice_data.get("customer_name", "Walk-in Customer")
        customer_data = None
        if customer_name != "Walk-in Customer":
            customer_data = await find_customer_by_name(user_id, customer_name)
            if customer_data:
                invoice_data['customer_id'] = customer_data['id']
                invoice_data['customer_email'] = customer_data.get('email', '')
                invoice_data['customer_phone'] = customer_data.get('phone', '')
                invoice_data['customer_address'] = customer_data.get('address', '')
                logger.info(f"✓ Customer found in database: {customer_data['name']}, email: {customer_data.get('email')}, phone: {customer_data.get('phone')}")
            else:
                logger.info(f"✗ Customer '{customer_name}' not found in database")
        
        invoice_data['missing_prices'] = missing_prices
        logger.info(f"Final invoice data: {invoice_data}")
        logger.info(f"Missing prices: {missing_prices}")
        return invoice_data
        
    except Exception as e:
        logger.error(f"Invoice extraction error: {str(e)}")
        return {
            "customer_name": "Walk-in Customer",
            "items": [{"name": "Item from voice note", "quantity": 1, "price": 100}],
            "missing_prices": []
        }

async def generate_invoice_text(invoice: Invoice, language: str = 'en') -> str:
    """Generate formatted invoice text for WhatsApp with multi-language support"""
    t = lambda key: translate(key, language)
    
    lines = [
        f"📄 {t('invoice')}",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"{t('invoice_number')}: {invoice.invoice_number}",
        f"{t('date')}: {invoice.date.strftime('%Y-%m-%d %H:%M')}",
        f"{t('customer')}: {invoice.customer_name}",
    ]
    
    # Add customer phone if available
    if invoice.customer_phone:
        lines.append(f"📱 Phone: {invoice.customer_phone}")
    
    # Add customer email if available
    if invoice.customer_email:
        lines.append(f"📧 Email: {invoice.customer_email}")
    
    lines.extend([
        "",
        t('items') + ":"
    ])
    
    for item in invoice.items:
        lines.append(f"\n• {item.name}")
        lines.append(f"  {t('quantity')}: {item.quantity} × ₹{item.price:.2f} = ₹{item.total:.2f}")
    
    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"{t('subtotal')}:    ₹{invoice.subtotal:.2f}",
        f"{t('tax')} ({invoice.tax_rate*100:.0f}%):      ₹{invoice.tax:.2f}",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        f"{t('grand_total')}:       ₹{invoice.total:.2f}",
        ""
    ])
    
    # Add credit/due information if partial payment
    if invoice.amount_paid > 0:
        lines.extend([
            f"{t('amount_paid')}:  ₹{invoice.amount_paid:.2f}",
            f"{t('amount_due')}:   ₹{invoice.amount_due:.2f}",
            ""
        ])
    
    # Get backend URL for links
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://easy-billing-20.preview.emergentagent.com')
    pdf_link = f"{backend_url}/api/invoices/{invoice.id}/pdf"
    
    # Add PDF download link
    lines.extend([
        f"📄 {t('download_pdf')}:",
        pdf_link,
        ""
    ])
    
    # Add payment link if available
    if invoice.payment_link:
        lines.extend([
            f"💳 {t('pay_now')}:",
            invoice.payment_link,
            ""
        ])
    else:
        lines.append(f"💳 {t('payment_due')}")
        lines.append("")
    
    lines.append(t('thank_you'))
    
    return "\n".join(lines)

async def send_whatsapp_message(to: str, message: str):
    """Send WhatsApp message via Twilio"""
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to
        )
        logger.info(f"Message sent: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        return False

# ==================== API Routes ====================

@api_router.get("/")
async def root():
    return {"message": "VoiceBill API - Billing on WhatsApp"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "VoiceBill",
        "version": "1.0.0"
    }

# WhatsApp Webhook
@api_router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
):
    """Handle incoming WhatsApp messages"""
    try:
        form_data = await request.form()
        
        # Validate Twilio signature (skip in development)
        # twilio_signature = request.headers.get("X-Twilio-Signature", "")
        # if not validator.validate(str(request.url), form_data, twilio_signature):
        #     raise HTTPException(status_code=403, detail="Invalid signature")
        
        logger.info(f"Received message from {From} with {NumMedia} media")
        
        # Get or create user
        user = await get_or_create_user(From)
        
        response = MessagingResponse()
        
        # Handle voice messages
        if NumMedia > 0:
            for i in range(NumMedia):
                media_url = form_data.get(f"MediaUrl{i}")
                content_type = form_data.get(f"MediaContentType{i}", "")
                
                if content_type.startswith("audio/"):
                    response.message("🎤 Processing your voice message...")
                    
                    # Transcribe audio
                    transcription = await transcribe_audio(str(media_url))
                    logger.info(f"Transcription: {transcription}")
                    
                    # Extract invoice data
                    invoice_data = await extract_invoice_data(transcription, user.id)
                    
                    # Check if prices are missing
                    missing_prices = invoice_data.get("missing_prices", [])
                    if missing_prices:
                        # Store pending invoice for price completion
                        pending = PendingInvoice(
                            user_id=user.id,
                            customer_name=invoice_data.get("customer_name", "Walk-in Customer"),
                            items=invoice_data.get("items", []),
                            transcription=transcription
                        )
                        doc = pending.model_dump()
                        doc['created_at'] = doc['created_at'].isoformat()
                        await db.pending_invoices.insert_one(doc)
                        
                        # Ask for prices in a simple text message
                        missing_items_str = ", ".join(missing_prices)
                        response.message(
                            f"Almost done! 📝\n\n"
                            f"What's the price for: *{missing_items_str}*?\n\n"
                            f"Just reply with the price(s).\n"
                            f"Example: \"100\" or \"{missing_prices[0]} is 100 rupees\""
                        )
                        return FastAPIResponse(content=str(response), media_type="application/xml")
                    
                    # Check if any item has null price
                    has_null_price = any(item.get("price") is None for item in invoice_data.get("items", []))
                    if has_null_price:
                        null_items = [item['name'] for item in invoice_data.get("items", []) if item.get("price") is None]
                        response.message(
                            f"⚠️ Price not available for: {', '.join(null_items)}\n\n"
                            f"Please add these products to your catalog first or "
                            f"mention the price in your voice message."
                        )
                        return FastAPIResponse(content=str(response), media_type="application/xml")
                    
                    # Calculate totals
                    items = []
                    subtotal = 0
                    for item_data in invoice_data.get("items", []):
                        total = item_data["quantity"] * item_data["price"]
                        items.append(InvoiceItem(
                            name=item_data["name"],
                            quantity=item_data["quantity"],
                            price=item_data["price"],
                            total=total
                        ))
                        subtotal += total
                    
                    tax_rate = 0.18  # 18% GST
                    tax = subtotal * tax_rate
                    total = subtotal + tax
                    
                    # Generate invoice number
                    invoice_count = await db.invoices.count_documents({"user_id": user.id})
                    invoice_number = f"INV-{user.id[:8]}-{invoice_count + 1:04d}"
                    
                    # Get customer data if found
                    customer_id = invoice_data.get("customer_id")
                    customer_email = invoice_data.get("customer_email", "")
                    customer_phone = invoice_data.get("customer_phone", "")
                    customer_address = invoice_data.get("customer_address", "")
                    
                    # Create invoice with customer data
                    invoice = Invoice(
                        user_id=user.id,
                        customer_id=customer_id,
                        invoice_number=invoice_number,
                        customer_name=invoice_data.get("customer_name", "Walk-in Customer"),
                        customer_email=customer_email,
                        customer_phone=customer_phone,
                        customer_address=customer_address,
                        items=items,
                        subtotal=subtotal,
                        tax_rate=tax_rate,
                        tax=tax,
                        total=total,
                        amount_paid=0.0,
                        amount_due=total,
                        status="unpaid",
                        transcription=transcription,
                        language=user.language
                    )
                    
                    # Save to database first
                    doc = invoice.model_dump()
                    doc['date'] = doc['date'].isoformat()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.invoices.insert_one(doc)
                    
                    # Create payment link
                    try:
                        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://easy-billing-20.preview.emergentagent.com')
                        if RAZORPAY_TEST_MODE:
                            payment_link = f"{backend_url}/api/test-payment/{invoice.id}"
                        else:
                            payment_data = {
                                "amount": int(invoice.total * 100),
                                "currency": "INR",
                                "description": f"Invoice {invoice.invoice_number}",
                                "customer": {
                                    "name": invoice.customer_name,
                                    "contact": invoice.customer_phone,
                                },
                                "notify": {"sms": False, "email": False}
                            }
                            payment_link_obj = razorpay_client.payment_link.create(payment_data)
                            payment_link = payment_link_obj['short_url']
                        
                        # Update invoice with payment link
                        await db.invoices.update_one(
                            {"id": invoice.id},
                            {"$set": {"payment_link": payment_link, "payment_status": "pending"}}
                        )
                        invoice.payment_link = payment_link
                    except Exception as e:
                        logger.error(f"Payment link creation failed: {str(e)}")
                        payment_link = ""
                    
                    # Send email if customer has email
                    if customer_email:
                        try:
                            # Generate PDF
                            invoice_doc = invoice.model_dump()
                            invoice_doc['date'] = invoice.date.isoformat()
                            invoice_doc['created_at'] = invoice.created_at.isoformat()
                            pdf_buffer = generate_invoice_pdf(invoice_doc)
                            pdf_content = pdf_buffer.read()
                            
                            # Send email
                            email_sent = send_invoice_email(
                                to_email=customer_email,
                                customer_name=invoice.customer_name,
                                invoice_number=invoice.invoice_number,
                                total_amount=invoice.total,
                                pdf_content=pdf_content,
                                payment_link=invoice.payment_link,
                                language=user.language
                            )
                            
                            if email_sent:
                                await db.invoices.update_one(
                                    {"id": invoice.id},
                                    {"$set": {"email_sent": True}}
                                )
                                logger.info(f"✓ Invoice emailed to {customer_email}")
                            
                            # Update customer stats
                            if customer_id:
                                await db.customers.update_one(
                                    {"id": customer_id},
                                    {
                                        "$inc": {"total_purchases": invoice.total, "total_due": invoice.amount_due},
                                        "$set": {"last_purchase": datetime.now(timezone.utc).isoformat()}
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Email sending failed: {str(e)}")
                    
                    # Generate and send invoice with payment link
                    invoice_text = await generate_invoice_text(invoice, user.language)
                    await send_whatsapp_message(From, invoice_text)
                    
                    return {"status": "success", "message": "Invoice sent"}
                else:
                    response.message("📎 File received, but I only process voice messages.")
        else:
            # Handle text messages
            body_lower = Body.lower()
            
            # Check if user has pending invoice awaiting prices
            pending = await db.pending_invoices.find_one(
                {"user_id": user.id},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            if pending:
                # User is replying with prices for pending invoice
                try:
                    # Extract prices from text using GPT
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"price_{user.id}_{datetime.now().timestamp()}",
                        system_message="""Extract prices from user's text response.
                        
Return JSON with prices array:
{"prices": [100, 200]} for multiple items or {"prices": [150]} for single item.

Extract numbers mentioned as prices. Be lenient with format."""
                    ).with_model("openai", "gpt-4o")
                    
                    price_response = await chat.send_message(UserMessage(text=Body))
                    
                    import json
                    price_text = price_response.strip()
                    if "```json" in price_text:
                        price_text = price_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in price_text:
                        price_text = price_text.split("```")[1].split("```")[0].strip()
                    
                    price_data = json.loads(price_text)
                    prices = price_data.get("prices", [])
                    
                    # Apply prices to pending items
                    items_with_null = [item for item in pending['items'] if item.get('price') is None]
                    
                    if len(prices) >= len(items_with_null):
                        for i, item in enumerate(items_with_null):
                            item['price'] = prices[i]
                        
                        # Now generate the invoice
                        items = []
                        subtotal = 0
                        for item_data in pending['items']:
                            total = item_data["quantity"] * item_data["price"]
                            items.append(InvoiceItem(
                                name=item_data["name"],
                                quantity=item_data["quantity"],
                                price=item_data["price"],
                                total=total
                            ))
                            subtotal += total
                        
                        tax_rate = 0.18
                        tax = subtotal * tax_rate
                        total = subtotal + tax
                        
                        invoice_count = await db.invoices.count_documents({"user_id": user.id})
                        invoice_number = f"INV-{user.id[:8]}-{invoice_count + 1:04d}"
                        
                        invoice = Invoice(
                            user_id=user.id,
                            invoice_number=invoice_number,
                            customer_name=pending['customer_name'],
                            items=items,
                            subtotal=subtotal,
                            tax_rate=tax_rate,
                            tax=tax,
                            total=total,
                            transcription=pending['transcription']
                        )
                        
                        # Save invoice
                        doc = invoice.model_dump()
                        doc['date'] = doc['date'].isoformat()
                        doc['created_at'] = doc['created_at'].isoformat()
                        await db.invoices.insert_one(doc)
                        
                        # Create payment link
                        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://easy-billing-20.preview.emergentagent.com')
                        if RAZORPAY_TEST_MODE:
                            payment_link = f"{backend_url}/api/test-payment/{invoice.id}"
                        else:
                            payment_data = {
                                "amount": int(invoice.total * 100),
                                "currency": "INR",
                                "description": f"Invoice {invoice.invoice_number}",
                                "customer": {"name": invoice.customer_name}
                            }
                            payment_link_obj = razorpay_client.payment_link.create(payment_data)
                            payment_link = payment_link_obj['short_url']
                        
                        await db.invoices.update_one(
                            {"id": invoice.id},
                            {"$set": {"payment_link": payment_link}}
                        )
                        invoice.payment_link = payment_link
                        
                        # Delete pending invoice
                        await db.pending_invoices.delete_one({"id": pending['id']})
                        
                        # Send invoice
                        invoice_text = await generate_invoice_text(invoice)
                        await send_whatsapp_message(From, invoice_text)
                        
                        return FastAPIResponse(content=str(MessagingResponse()), media_type="application/xml")
                    else:
                        response.message("Please provide prices for all items.")
                        return FastAPIResponse(content=str(response), media_type="application/xml")
                        
                except Exception as e:
                    logger.error(f"Price extraction error: {str(e)}")
                    response.message("Couldn't understand the price. Please try again with just numbers.")
                    return FastAPIResponse(content=str(response), media_type="application/xml")
            
            # Regular text message handling
            messages = get_whatsapp_messages(user.language)
            
            # Language switching
            if "language" in body_lower:
                if "hindi" in body_lower or "हिंदी" in body_lower:
                    await db.users.update_one({"id": user.id}, {"$set": {"language": "hi"}})
                    user.language = "hi"
                    response.message("✅ भाषा हिंदी में बदल गई। अब मैं हिंदी में जवाब दूंगा।")
                elif "english" in body_lower or "अंग्रेजी" in body_lower:
                    await db.users.update_one({"id": user.id}, {"$set": {"language": "en"}})
                    user.language = "en"
                    response.message("✅ Language changed to English. I'll now respond in English.")
                return FastAPIResponse(content=str(response), media_type="application/xml")
            
            if "help" in body_lower:
                response.message(messages['help'])
            elif "invoice" in body_lower or "list" in body_lower or "चालान" in body_lower:
                # Get recent invoices
                invoices = await db.invoices.find(
                    {"user_id": user.id},
                    {"_id": 0}
                ).sort("date", -1).limit(5).to_list(5)
                
                if invoices:
                    msg = messages['recent_invoices']
                    for inv in invoices:
                        date = datetime.fromisoformat(inv['date']).strftime('%Y-%m-%d')
                        msg += f"• {inv['invoice_number']} - ₹{inv['total']:.2f} ({date})\n"
                    response.message(msg)
                else:
                    response.message(messages['no_invoices'])
            else:
                response.message(messages['welcome'])
        
        return FastAPIResponse(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        response = MessagingResponse()
        messages = get_whatsapp_messages('en')  # Default to English for errors
        response.message(messages['error'])
        return FastAPIResponse(content=str(response), media_type="application/xml")

# User routes
@api_router.post("/users", response_model=User)
async def create_user(user_input: UserCreate):
    user = User(**user_input.model_dump())
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    return user

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find({}, {"_id": 0}).to_list(100)
    for user in users:
        if isinstance(user['created_at'], str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    return users

# Invoice routes
@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(user_id: Optional[str] = None):
    query = {"user_id": user_id} if user_id else {}
    invoices = await db.invoices.find(query, {"_id": 0}).sort("date", -1).to_list(100)
    for invoice in invoices:
        if isinstance(invoice['date'], str):
            invoice['date'] = datetime.fromisoformat(invoice['date'])
        if isinstance(invoice['created_at'], str):
            invoice['created_at'] = datetime.fromisoformat(invoice['created_at'])
    return invoices

@api_router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice_doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if isinstance(invoice_doc['date'], str):
        invoice_doc['date'] = datetime.fromisoformat(invoice_doc['date'])
    if isinstance(invoice_doc['created_at'], str):
        invoice_doc['created_at'] = datetime.fromisoformat(invoice_doc['created_at'])
    return Invoice(**invoice_doc)

# Delete Invoice
@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete an invoice"""
    result = await db.invoices.delete_one({"id": invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"success": True, "message": "Invoice deleted successfully"}

# Update Invoice (for marking as paid, etc.)
@api_router.put("/invoices/{invoice_id}")
async def update_invoice(invoice_id: str, request: Request):
    """Update invoice details (status, payment info, etc.)"""
    try:
        # Get update data from request body
        update_data = await request.json()
        
        # Check if invoice exists
        invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not invoice_doc:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # If marking as paid, calculate amounts
        if update_data.get('status') == 'paid':
            total = invoice_doc.get('total', 0)
            update_data['amount_paid'] = total
            update_data['amount_due'] = 0
            update_data['status'] = 'paid'
        
        # Update in database
        result = await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0 and result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update customer's total_due if customer_id exists
        if invoice_doc.get('customer_id') and 'amount_due' in update_data:
            # Recalculate customer's total due from all invoices
            customer_invoices = await db.invoices.find(
                {"customer_id": invoice_doc['customer_id']},
                {"_id": 0}
            ).to_list(1000)
            
            total_customer_due = sum(inv.get('amount_due', 0) for inv in customer_invoices)
            
            await db.customers.update_one(
                {"id": invoice_doc['customer_id']},
                {"$set": {"total_due": total_customer_due}}
            )
        
        return {"success": True, "message": "Invoice updated successfully"}
    
    except Exception as e:
        logger.error(f"Error updating invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update invoice: {str(e)}")

# ==================== NEW FEATURES ====================

# PDF Invoice Download
@api_router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(invoice_id: str):
    """Generate and download PDF invoice"""
    try:
        # Get invoice from database
        invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not invoice_doc:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Generate PDF
        pdf_buffer = generate_invoice_pdf(invoice_doc)
        
        # Return as downloadable file
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{invoice_doc['invoice_number']}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

# Create Payment Link for Invoice
@api_router.post("/invoices/{invoice_id}/create-payment")
async def create_payment_link(invoice_id: str):
    """Create Razorpay payment link for invoice"""
    try:
        # Get invoice
        invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not invoice_doc:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://easy-billing-20.preview.emergentagent.com')
        
        if RAZORPAY_TEST_MODE:
            # In test mode, create our own test payment page
            payment_link = f"{backend_url}/api/test-payment/{invoice_id}"
            logger.info(f"Test mode: Generated test payment page {payment_link}")
        else:
            # Create actual Razorpay payment link
            payment_data = {
                "amount": int(invoice_doc['total'] * 100),  # Amount in paise
                "currency": "INR",
                "description": f"Invoice {invoice_doc['invoice_number']}",
                "customer": {
                    "name": invoice_doc.get('customer_name', 'Customer'),
                    "contact": invoice_doc.get('customer_phone', ''),
                },
                "notify": {
                    "sms": True,
                    "email": False
                },
                "reminder_enable": True,
                "callback_url": f"{backend_url}/api/payment-callback",
                "callback_method": "get"
            }
            
            payment_link_obj = razorpay_client.payment_link.create(payment_data)
            payment_link = payment_link_obj['short_url']
        
        # Update invoice with payment link
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"payment_link": payment_link}}
        )
        
        return {
            "success": True,
            "payment_link": payment_link,
            "invoice_id": invoice_id,
            "test_mode": RAZORPAY_TEST_MODE
        }
    
    except Exception as e:
        logger.error(f"Payment link creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(e)}")

# Payment Callback (for Razorpay)
@api_router.get("/payment-callback")
async def payment_callback(
    razorpay_payment_id: str,
    razorpay_payment_link_id: str,
    razorpay_payment_link_reference_id: str,
    razorpay_payment_link_status: str,
    razorpay_signature: str
):
    """Handle payment callback from Razorpay"""
    try:
        # Update invoice status
        invoice_id = razorpay_payment_link_reference_id
        
        if razorpay_payment_link_status == "paid":
            await db.invoices.update_one(
                {"id": invoice_id},
                {"$set": {
                    "status": "paid",
                    "payment_id": razorpay_payment_id
                }}
            )
            logger.info(f"Invoice {invoice_id} marked as paid")
        
        return {"status": "success", "message": "Payment processed"}
    
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}")
        return {"status": "error", "message": str(e)}

# Test Payment Page (for test mode)
@api_router.get("/test-payment/{invoice_id}")
async def test_payment_page(invoice_id: str):
    """Test payment page for demo/testing"""
    from fastapi.responses import HTMLResponse
    
    # Get invoice details
    invoice_doc = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice_doc:
        return HTMLResponse(content="<h1>Invoice not found</h1>", status_code=404)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Payment - VoiceBill</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #e0f2f1 0%, #b2dfdb 50%, #80cbc4 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .payment-card {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
                padding: 2rem;
            }}
            .header {{
                text-align: center;
                margin-bottom: 2rem;
            }}
            .logo {{
                font-size: 2rem;
                font-weight: 700;
                color: #00897b;
                margin-bottom: 0.5rem;
            }}
            .test-badge {{
                background: #fff3e0;
                color: #f57c00;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.875rem;
                font-weight: 600;
                display: inline-block;
            }}
            .invoice-details {{
                background: #f5f5f5;
                padding: 1.5rem;
                border-radius: 12px;
                margin-bottom: 1.5rem;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.75rem;
            }}
            .detail-label {{
                color: #666;
                font-weight: 500;
            }}
            .detail-value {{
                color: #333;
                font-weight: 600;
            }}
            .total {{
                font-size: 1.5rem;
                color: #00897b;
                border-top: 2px solid #00897b;
                padding-top: 1rem;
                margin-top: 1rem;
            }}
            .payment-methods {{
                margin: 1.5rem 0;
            }}
            .method-title {{
                font-size: 1rem;
                font-weight: 600;
                color: #333;
                margin-bottom: 1rem;
            }}
            .methods-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.75rem;
            }}
            .method-btn {{
                padding: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: white;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
                font-weight: 600;
                color: #666;
            }}
            .method-btn:hover {{
                border-color: #00897b;
                color: #00897b;
                transform: translateY(-2px);
            }}
            .pay-btn {{
                width: 100%;
                padding: 1rem;
                background: linear-gradient(135deg, #00897b, #00695c);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1.125rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                margin-top: 1rem;
            }}
            .pay-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 16px rgba(0, 137, 123, 0.3);
            }}
            .success-message {{
                display: none;
                background: #e8f5e9;
                color: #2e7d32;
                padding: 1.5rem;
                border-radius: 12px;
                text-align: center;
                font-weight: 600;
                margin-top: 1rem;
            }}
            .note {{
                text-align: center;
                color: #666;
                font-size: 0.875rem;
                margin-top: 1.5rem;
                padding-top: 1.5rem;
                border-top: 1px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <div class="payment-card">
            <div class="header">
                <div class="logo">VoiceBill</div>
                <div class="test-badge">TEST MODE</div>
            </div>
            
            <div class="invoice-details">
                <div class="detail-row">
                    <span class="detail-label">Invoice Number:</span>
                    <span class="detail-value">{invoice_doc['invoice_number']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Customer:</span>
                    <span class="detail-value">{invoice_doc['customer_name']}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Items:</span>
                    <span class="detail-value">{len(invoice_doc['items'])} item(s)</span>
                </div>
                <div class="detail-row total">
                    <span class="detail-label">Total Amount:</span>
                    <span class="detail-value">Rs. {invoice_doc['total']:.2f}</span>
                </div>
            </div>
            
            <div class="payment-methods">
                <div class="method-title">Select Payment Method</div>
                <div class="methods-grid">
                    <div class="method-btn">UPI</div>
                    <div class="method-btn">Card</div>
                    <div class="method-btn">NetBanking</div>
                </div>
            </div>
            
            <button class="pay-btn" onclick="processPayment()">
                Pay Rs. {invoice_doc['total']:.2f}
            </button>
            
            <div class="success-message" id="successMessage">
                ✅ Payment Successful!<br>
                Invoice marked as paid.
            </div>
            
            <div class="note">
                This is a test payment page. No real money will be charged.<br>
                For production, integrate with Razorpay live keys.
            </div>
        </div>
        
        <script>
            async function processPayment() {{
                const btn = document.querySelector('.pay-btn');
                btn.disabled = true;
                btn.textContent = 'Processing...';
                
                // Simulate payment processing
                setTimeout(async () => {{
                    // Mark invoice as paid
                    await fetch('/api/test-payment-success/{invoice_id}', {{
                        method: 'POST'
                    }});
                    
                    btn.style.display = 'none';
                    document.getElementById('successMessage').style.display = 'block';
                    
                    // Redirect after 3 seconds
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                }}, 2000);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Test Payment Success Handler
@api_router.post("/test-payment-success/{invoice_id}")
async def test_payment_success(invoice_id: str):
    """Handle test payment success"""
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "paid",
            "payment_id": f"test_payment_{invoice_id[:8]}"
        }}
    )
    return {"status": "success", "message": "Test payment completed"}

# Customer Management CRUD
@api_router.post("/customers", response_model=Customer)
async def create_customer(customer_input: CustomerCreate):
    """Create a new customer"""
    customer = Customer(**customer_input.model_dump())
    doc = customer.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('last_purchase'):
        doc['last_purchase'] = doc['last_purchase'].isoformat()
    await db.customers.insert_one(doc)
    return customer

@api_router.get("/customers", response_model=List[Customer])
async def get_customers(user_id: Optional[str] = None):
    """Get all customers, optionally filtered by user"""
    query = {"user_id": user_id} if user_id else {}
    customers = await db.customers.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    for customer in customers:
        if isinstance(customer['created_at'], str):
            customer['created_at'] = datetime.fromisoformat(customer['created_at'])
        if customer.get('last_purchase') and isinstance(customer['last_purchase'], str):
            customer['last_purchase'] = datetime.fromisoformat(customer['last_purchase'])
    return customers

@api_router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str):
    """Get a specific customer by ID"""
    customer_doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer_doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    if isinstance(customer_doc['created_at'], str):
        customer_doc['created_at'] = datetime.fromisoformat(customer_doc['created_at'])
    if customer_doc.get('last_purchase') and isinstance(customer_doc['last_purchase'], str):
        customer_doc['last_purchase'] = datetime.fromisoformat(customer_doc['last_purchase'])
    return Customer(**customer_doc)

@api_router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_input: CustomerCreate):
    """Update a customer"""
    customer_doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer_doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Update customer
    update_data = customer_input.model_dump()
    await db.customers.update_one(
        {"id": customer_id},
        {"$set": update_data}
    )
    
    # Return updated customer
    updated_doc = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if isinstance(updated_doc['created_at'], str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    if updated_doc.get('last_purchase') and isinstance(updated_doc['last_purchase'], str):
        updated_doc['last_purchase'] = datetime.fromisoformat(updated_doc['last_purchase'])
    return Customer(**updated_doc)

@api_router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """Delete a customer"""
    result = await db.customers.delete_one({"id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True, "message": "Customer deleted"}

@api_router.get("/customers/search/{query}")
async def search_customers(query: str, user_id: Optional[str] = None):
    """Search customers by name"""
    search_filter = {"name": {"$regex": query, "$options": "i"}}
    if user_id:
        search_filter["user_id"] = user_id
    
    customers = await db.customers.find(search_filter, {"_id": 0}).to_list(100)
    for customer in customers:
        if isinstance(customer['created_at'], str):
            customer['created_at'] = datetime.fromisoformat(customer['created_at'])
        if customer.get('last_purchase') and isinstance(customer['last_purchase'], str):
            customer['last_purchase'] = datetime.fromisoformat(customer['last_purchase'])
    return customers

# Product Catalog CRUD
@api_router.post("/products", response_model=Product)
async def create_product(product_input: ProductCreate):
    """Create a new product in catalog"""
    product = Product(**product_input.model_dump())
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.products.insert_one(doc)
    return product

@api_router.get("/products", response_model=List[Product])
async def get_products(user_id: Optional[str] = None):
    """Get all products, optionally filtered by user"""
    query = {"user_id": user_id} if user_id else {}
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    return products

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Get a specific product by ID"""
    product_doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product_doc:
        raise HTTPException(status_code=404, detail="Product not found")
    if isinstance(product_doc['created_at'], str):
        product_doc['created_at'] = datetime.fromisoformat(product_doc['created_at'])
    return Product(**product_doc)

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_input: ProductCreate):
    """Update a product"""
    product_doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product_doc:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update product
    update_data = product_input.model_dump()
    await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )
    
    # Return updated product
    updated_doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if isinstance(updated_doc['created_at'], str):
        updated_doc['created_at'] = datetime.fromisoformat(updated_doc['created_at'])
    return Product(**updated_doc)

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """Delete a product"""
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "message": "Product deleted"}

# Search products by name
@api_router.get("/products/search/{query}")
async def search_products(query: str, user_id: Optional[str] = None):
    """Search products by name"""
    search_filter = {"name": {"$regex": query, "$options": "i"}}
    if user_id:
        search_filter["user_id"] = user_id
    
    products = await db.products.find(search_filter, {"_id": 0}).to_list(100)
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    return products

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()