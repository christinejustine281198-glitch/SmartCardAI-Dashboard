import smtplib
from email.message import EmailMessage

# SMTP settings
SMTP_SERVER = "mail.smartcardai.com"
SMTP_PORT = 587
SMTP_USER = "support@smartcardai.com"
SMTP_PASS = "Smart@Mail2025!"

# Create email
msg = EmailMessage()
msg['Subject'] = "Test Email from VS Code"
msg['From'] = SMTP_USER
msg['To'] = "christinejustine281198@gmail.com"  # Replace with your email
msg.set_content("reset your password here.")

# Send email
try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # Secure connection
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print("Email sent successfully!")
except Exception as e:
    print("Failed to send email:", e)
