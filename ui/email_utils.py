import smtplib
import os
from typing import List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASS

def send_email_with_photos(recipient_email: str, photo_paths: List[str]) -> bool:
    """Sends an email with multiple photos attached."""
    if not recipient_email or "@" not in recipient_email:
        print(f"Error: Invalid recipient email '{recipient_email}'")
        return False

    if not photo_paths:
        print("Error: No photos to send.")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "Your GestureArcade Selfie Collection! 📸"

        body = f"Hi there!\n\nAttached are the {len(photo_paths)} awesome selfies you took in GestureArcade's Point Selfie mode. Enjoy!\n\n- The GestureArcade Team"
        msg.attach(MIMEText(body, 'plain'))

        # Attach each image
        for photo_path in photo_paths:
            if not os.path.exists(photo_path):
                print(f"Warning: Photo path '{photo_path}' does not exist. Skipping.")
                continue
                
            filename = os.path.basename(photo_path)
            with open(photo_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {filename}")
                msg.attach(part)

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()

        print(f"Email successfully sent to {recipient_email} with {len(photo_paths)} attachments.")
        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
