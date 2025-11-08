from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import io
import os
import qrcode

def generate_invoice_pdf(invoice_data):
    """
    Generate PDF invoice from invoice data
    Returns: BytesIO object containing PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#00897b'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#00695c'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    address_style = ParagraphStyle(
        'AddressStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.grey
    )
    
    normal_style = styles['Normal']
    
    # Company Header with dummy details
    company_header = Table([
        [
            Paragraph("<b>VoiceBill Solutions Pvt. Ltd.</b>", company_style),
            Paragraph("<b>TAX INVOICE</b>", title_style)
        ]
    ], colWidths=[3.5*inch, 3.5*inch])
    
    company_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(company_header)
    elements.append(Spacer(1, 0.1*inch))
    
    # Company Address
    company_address = Paragraph(
        "123 Business Plaza, MG Road<br/>"
        "Bangalore, Karnataka - 560001<br/>"
        "GSTIN: 29ABCDE1234F1Z5<br/>"
        "Phone: +91 80 1234 5678 | Email: billing@voicebill.com",
        address_style
    )
    elements.append(company_address)
    elements.append(Spacer(1, 0.2*inch))
    
    # Horizontal line
    line_table = Table([['', '']], colWidths=[7*inch])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#00897b')),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Invoice Info Table
    invoice_info = [
        ['Invoice Number:', invoice_data.get('invoice_number', 'N/A')],
        ['Date:', datetime.fromisoformat(invoice_data.get('date')).strftime('%d %B %Y') if isinstance(invoice_data.get('date'), str) else invoice_data.get('date').strftime('%d %B %Y')],
        ['Customer:', invoice_data.get('customer_name', 'Walk-in Customer')],
    ]
    
    # Add customer phone if available
    if invoice_data.get('customer_phone'):
        invoice_info.append(['Phone:', invoice_data.get('customer_phone')])
    
    # Add customer email if available
    if invoice_data.get('customer_email'):
        invoice_info.append(['Email:', invoice_data.get('customer_email')])
    
    # Add customer address if available
    if invoice_data.get('customer_address'):
        invoice_info.append(['Address:', invoice_data.get('customer_address')])
    
    # Add status
    invoice_info.append(['Status:', invoice_data.get('status', 'Unpaid').upper()])
    
    info_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0f2f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Items Heading
    items_heading = Paragraph("<b>ITEMS</b>", heading_style)
    elements.append(items_heading)
    elements.append(Spacer(1, 0.1*inch))
    
    # Items Table - Use Rs. instead of rupee symbol for better compatibility
    items_data = [['Item', 'Quantity', 'Price', 'Total']]
    for item in invoice_data.get('items', []):
        items_data.append([
            item['name'],
            str(item['quantity']),
            f"Rs. {item['price']:.2f}",
            f"Rs. {item['total']:.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[3*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00897b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Generate QR Code if payment link exists
    qr_image = None
    if invoice_data.get('payment_link'):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(invoice_data['payment_link'])
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR to BytesIO
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Create reportlab Image from QR
        qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
    
    # Summary Table with QR Code
    if qr_image:
        summary_data = [
            ['Subtotal:', f"Rs. {invoice_data.get('subtotal', 0):.2f}", ''],
            [f"GST ({invoice_data.get('tax_rate', 0)*100:.0f}%):", f"Rs. {invoice_data.get('tax', 0):.2f}", ''],
            ['', '', ''],
            ['TOTAL:', f"Rs. {invoice_data.get('total', 0):.2f}", '']
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch, 1.6*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 2), 'Helvetica'),
            ('FONTNAME', (0, 3), (1, 3), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 2), 10),
            ('FONTSIZE', (0, 3), (1, 3), 14),
            ('TEXTCOLOR', (0, 3), (1, 3), colors.HexColor('#00897b')),
            ('LINEABOVE', (0, 3), (1, 3), 2, colors.HexColor('#00897b')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('SPAN', (2, 0), (2, -1)),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('VALIGN', (2, 0), (2, -1), 'MIDDLE'),
        ]))
        
        # Add QR code to the summary table
        summary_table._cellvalues[0][2] = qr_image
        elements.append(summary_table)
    else:
        summary_data = [
            ['Subtotal:', f"Rs. {invoice_data.get('subtotal', 0):.2f}"],
            [f"GST ({invoice_data.get('tax_rate', 0)*100:.0f}%):", f"Rs. {invoice_data.get('tax', 0):.2f}"],
            ['', ''],
            ['TOTAL:', f"Rs. {invoice_data.get('total', 0):.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[4.6*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 2), 'Helvetica'),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 2), 10),
            ('FONTSIZE', (0, 3), (-1, 3), 14),
            ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor('#00897b')),
            ('LINEABOVE', (0, 3), (-1, 3), 2, colors.HexColor('#00897b')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(summary_table)
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Payment Instructions
    if invoice_data.get('payment_link'):
        payment_box = Table([
            ['Scan QR Code or Click Link to Pay via UPI/Cards/Net Banking'],
            [invoice_data['payment_link']]
        ], colWidths=[6.5*inch])
        payment_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2f1')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 1), 8),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#00897b')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#00897b')),
        ]))
        elements.append(payment_box)
        elements.append(Spacer(1, 0.2*inch))
    
    # Terms and Conditions
    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_LEFT
    )
    terms = Paragraph(
        "<b>Terms & Conditions:</b><br/>"
        "1. Payment due within 7 days of invoice date<br/>"
        "2. Late payments may incur additional charges<br/>"
        "3. Goods once sold cannot be returned<br/>"
        "4. Subject to Bangalore jurisdiction",
        terms_style
    )
    elements.append(terms)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    footer = Paragraph(
        "<b>Thank you for your business!</b><br/>"
        "This is a computer-generated invoice | Generated by VoiceBill",
        footer_style
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer