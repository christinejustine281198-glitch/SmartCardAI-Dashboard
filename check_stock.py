import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.blocking import BlockingScheduler

# ---------------- Configuration ----------------
SERVICE_ACCOUNT_FILE = "appscriptclone-3d7b5ef7ae6b.json"
SPREADSHEET_ID = "1LMIa_AuHXh-A1hAvEtelk1bi8K-OSD_surCKgrZW0b0"
SHEET_NAME = "Sheet1"  # adjust if your sheet has a different name

# Email settings
SENDER_EMAIL = "christinejustine281198@gmail.com"
RECEIVER_EMAIL = "christinejustine281198@gmail.com"
EMAIL_PASSWORD = "dmqmbavrkbrdpjni"

# ---------------- Function ----------------
def check_stock():
    try:
        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_records()

        # Check stock and send alerts
        for row in data:
            product = row.get("Sales")
            stock = row.get("Stock Quantity")
            rate = row.get("Rate")

            if stock is not None and int(stock) < 50:
                alert_message = f"⚠️ ALERT: {product} has low stock ({stock})! Rate: {rate}"
                print(alert_message)

                # Send email
                msg = MIMEText(alert_message)
                msg["Subject"] = f"Low Stock Alert: {product}"
                msg["From"] = SENDER_EMAIL
                msg["To"] = RECEIVER_EMAIL

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(SENDER_EMAIL, EMAIL_PASSWORD)
                    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

                print(f"✅ Email sent for {product}")

    except Exception as e:
        print("❌ Error:", e)

# ---------------- Scheduler ----------------
if __name__ == "__main__":
    scheduler = BlockingScheduler()

    check_stock()   # run immediately once

    # Run check_stock every 5 minutes
    scheduler.add_job(check_stock, "interval", minutes=5)
    print("🕒 Stock checker started. Runs every 5 minutes...")
    scheduler.start()
