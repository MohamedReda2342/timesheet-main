import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def test_smtp_port_25():
    # Force Port 25
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = 25  # <--- CHANGED FROM 587
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", smtp_user)
    
    receiver_email = "Mohamed.Alsaidy@wavz.com.eg" 

    print(f"🔵 Connecting to {smtp_server}:{smtp_port} (No TLS)...")

    msg = MIMEMultipart()
    msg['From'] = smtp_from
    msg['To'] = receiver_email
    msg['Subject'] = "Test Email (Port 25)"
    msg.attach(MIMEText("Testing Port 25 Plain Auth", 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)
        
        # Note: NO starttls() call here
        
        print("🔵 Attempting Login...")
        server.login(smtp_user, smtp_password)
        
        print("🔵 Sending...")
        server.send_message(msg)
        print("✅ Success!")
        server.quit()
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == "__main__":
    test_smtp_port_25()