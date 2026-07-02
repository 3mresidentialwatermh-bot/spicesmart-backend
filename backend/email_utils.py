from flask_mail import Message
from flask import current_app
from threading import Thread
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            # For logging/debugging in case SMTP is not configured
            print(f"Failed to send email: {e}")
            print(f"To: {msg.recipients}, Subject: {msg.subject}, Body: {msg.body}")

def send_email(subject, sender, recipients, text_body, html_body=None):
    if not current_app.config.get('MAIL_USERNAME'):
        print(f"Mock Email -> To: {recipients}, Subject: {subject}")
        return
        
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
        
    # Send asynchronously so it doesn't block the request
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_order_confirmation(order):
    buyer_email = order.buyer.email
    subject = f"Order Confirmation #{order.id} - SpicesMart"
    body = f"Hello {order.buyer.name},\n\nYour order #{order.id} has been successfully placed.\nTotal Amount: ₹{order.total_amount}\n\nThank you for shopping with us!\nSpicesMart Team"
    
    send_email(
        subject=subject,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@spicesmart.com'),
        recipients=[buyer_email],
        text_body=body
    )

def send_inventory_alert(distributor, missed_amount):
    subject = f"Lost Business Opportunity Alert - SpicesMart"
    body = f"Hello {distributor.name},\n\nYou just missed a potential sale worth ₹{missed_amount} because you were out of stock!\n\nPlease log in to SpicesMart and order more inventory from the Admin warehouse to prevent losing more sales.\n\nBest,\nSpicesMart Team"
    
    send_email(
        subject=subject,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@spicesmart.com'),
        recipients=[distributor.email],
        text_body=body
    )
