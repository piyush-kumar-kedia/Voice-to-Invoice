"""Translation module for multi-language support"""

# Invoice translations
INVOICE_TRANSLATIONS = {
    'en': {
        'invoice': 'INVOICE',
        'invoice_number': 'Invoice Number',
        'date': 'Date',
        'customer': 'Customer',
        'email': 'Email',
        'phone': 'Phone',
        'status': 'Status',
        'items': 'ITEMS',
        'item': 'Item',
        'quantity': 'Quantity',
        'price': 'Price',
        'total': 'Total',
        'subtotal': 'Subtotal',
        'tax': 'Tax',
        'grand_total': 'TOTAL',
        'amount_paid': 'Amount Paid',
        'amount_due': 'Amount Due',
        'payment_due': 'Payment Due: On delivery',
        'thank_you': 'Thank you for your business!',
        'download_pdf': 'Download PDF Invoice',
        'pay_now': 'Pay Now (UPI/Cards/Net Banking)',
        'paid': 'Paid',
        'unpaid': 'Unpaid',
        'partial': 'Partial',
        'terms': 'Terms & Conditions',
        'payment_methods': 'Payment Methods: Cash, UPI, Cards, Net Banking'
    },
    'hi': {
        'invoice': 'चालान',
        'invoice_number': 'चालान संख्या',
        'date': 'तारीख',
        'customer': 'ग्राहक',
        'email': 'ईमेल',
        'phone': 'फोन',
        'status': 'स्थिति',
        'items': 'वस्तुएं',
        'item': 'वस्तु',
        'quantity': 'मात्रा',
        'price': 'मूल्य',
        'total': 'कुल',
        'subtotal': 'उप-योग',
        'tax': 'कर',
        'grand_total': 'कुल योग',
        'amount_paid': 'भुगतान राशि',
        'amount_due': 'बकाया राशि',
        'payment_due': 'भुगतान: डिलीवरी पर',
        'thank_you': 'आपके व्यापार के लिए धन्यवाद!',
        'download_pdf': 'PDF चालान डाउनलोड करें',
        'pay_now': 'अभी भुगतान करें (UPI/कार्ड/नेट बैंकिंग)',
        'paid': 'भुगतान किया',
        'unpaid': 'अवैतनिक',
        'partial': 'आंशिक',
        'terms': 'नियम और शर्तें',
        'payment_methods': 'भुगतान विधि: नकद, UPI, कार्ड, नेट बैंकिंग'
    }
}

def translate(key: str, language: str = 'en') -> str:
    """Get translation for a key in specified language"""
    lang = language.lower()
    if lang not in INVOICE_TRANSLATIONS:
        lang = 'en'
    return INVOICE_TRANSLATIONS[lang].get(key, INVOICE_TRANSLATIONS['en'].get(key, key))

def get_whatsapp_messages(language: str = 'en'):
    """Get WhatsApp bot messages in specified language"""
    messages = {
        'en': {
            'processing': '🎤 Processing your voice message...',
            'ask_price': 'Almost done! 📝\n\nWhat\'s the price for: *{items}*?\n\nJust reply with the price(s).\nExample: "100" or "{item} is 100 rupees"',
            'welcome': 'Welcome to VoiceBill! 🎤\n\nSend me a voice message describing your sale:\ne.g., \'Sold 2 bags of rice at 500 rupees each\'\n\nI\'ll automatically generate an invoice for you!',
            'invoice_created': '✅ Invoice created successfully!',
            'error': 'Sorry, I encountered an error. Please try again.',
            'help': 'Welcome to VoiceBill! 🎤\n\nSend a voice message with your sale details.\n\nCommands:\n• "help" - Show this message\n• "invoice" - View recent invoices\n• "customers" - View customers\n• "language hindi" - Switch to Hindi',
            'recent_invoices': 'Your recent invoices:\n\n',
            'no_invoices': 'No invoices yet. Send a voice message to create one!',
            'language_changed': '✅ Language changed to English',
            'customer_added': '✅ Customer {name} added to database'
        },
        'hi': {
            'processing': '🎤 आपका वॉयस संदेश प्रोसेस हो रहा है...',
            'ask_price': 'लगभग पूरा! 📝\n\n*{items}* की कीमत क्या है?\n\nकेवल कीमत के साथ उत्तर दें।\nउदाहरण: "100" या "{item} 100 रुपये है"',
            'welcome': 'VoiceBill में आपका स्वागत है! 🎤\n\nअपनी बिक्री का विवरण देते हुए वॉयस संदेश भेजें:\nजैसे: \'2 बैग चावल 500 रुपये प्रत्येक में बेचे\'\n\nमैं स्वचालित रूप से चालान बना दूंगा!',
            'invoice_created': '✅ चालान सफलतापूर्वक बनाया गया!',
            'error': 'क्षमा करें, एक त्रुटि हुई। कृपया पुनः प्रयास करें।',
            'help': 'VoiceBill में आपका स्वागत है! 🎤\n\nअपनी बिक्री विवरण के साथ वॉयस संदेश भेजें।\n\nकमांड:\n• "help" - यह संदेश दिखाएं\n• "invoice" - हाल के चालान देखें\n• "customers" - ग्राहक देखें\n• "language english" - अंग्रेजी में बदलें',
            'recent_invoices': 'आपके हाल के चालान:\n\n',
            'no_invoices': 'अभी तक कोई चालान नहीं। वॉयस संदेश भेजकर बनाएं!',
            'language_changed': '✅ भाषा हिंदी में बदल गई',
            'customer_added': '✅ ग्राहक {name} डेटाबेस में जोड़ा गया'
        }
    }
    
    lang = language.lower()
    return messages.get(lang, messages['en'])