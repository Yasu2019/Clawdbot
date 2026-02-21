import os
import base64
import json
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- CONFIG ---
BILLING_ACCOUNT_ID = "019DB0-4336C8-FFE190"
SERVICE_ACCOUNT_FILE = '/home/node/clawd/billing_key.json'
GMAIL_TOKEN_FILE = '/home/node/clawd/token.json'
# Assuming credentials.json is also in the clawd directory for client_id/secret
CREDENTIALS_FILE = '/home/node/clawd/credentials.json'
TARGET_EMAIL = "y.suzuki.hk@gmail.com"
COST_THRESHOLD_JPY = 500

def send_email(service, subject, body):
    try:
        message = MIMEText(body)
        message['to'] = TARGET_EMAIL
        message['from'] = TARGET_EMAIL
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    try:
        print("-- Starting Billing Check ---")

        # 1. Billing Auth (Service Account)
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
             print(f"Error: Service account file not found at {SERVICE_ACCOUNT_FILE}")
             return

        creds_billing = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        billing_service = build('billingbudgets', 'v1', credentials=creds_billing)

        parent = f"billingAccounts/{BILLING_ACCOUNT_ID}"
        budget_summary = ""

        try:
            budgets = billing_service.billingAccounts().budgets().list(parent=parent).execute()
            if 'budgets' in budgets:
                for b in budgets['budgets']:
                    name = b.get('displayName', 'Unknown')
                    amount = b.get('amount', {}).get('specifiedAmount', {})
                    units = amount.get('units', '0')
                    budget_summary += f"- Budget: {name} ({units} JPY)\n"
            else:
                budget_summary = "No budget rules found."
        except Exception as e:
            budget_summary = f"[Access Error] Could not read budgets: {e}\n(Please ensure service account has 'Billing Account Viewer' role)"
            print(f"Billing API access error: {e}") # Log the billing specific error

        # 2. Calendar & Gmail Auth (User OAuth)
        if not os.path.exists(GMAIL_TOKEN_FILE):
             print(f"Error: Token file not found at {GMAIL_TOKEN_FILE}")
             return
        if not os.path.exists(CREDENTIALS_FILE):
             print(f"Error: Credentials file not found at {CREDENTIALS_FILE}. It's needed for client_id/secret.")
             return


        with open(GMAIL_TOKEN_FILE, 'r') as tf:
            token_data = json.load(tf)
        with open(CREDENTIALS_FILE, 'r') as cf:
            cred_data = json.load(cf)
            installed = cred_data.get('installed', cred_data.get('web', {}))

        creds_user = Credentials(
            token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=installed.get('client_id'),
            client_secret=installed.get('client_secret'),
            scopes=token_data.get('scope', '').split(' ')
        )

        calendar_service = build('calendar', 'v3', credentials=creds_user)
        # Note: Gmail service for sending email requires 'https://www.googleapis.com/auth/gmail.send' scope
        # If token.json doesn't have it, email sending might fail.
        gmail_service = build('gmail', 'v1', credentials=creds_user)

        # 3. Report / Alert via Calendar & Email
        now_utc = datetime.utcnow()
        start_str = now_utc.isoformat() + 'Z'
        end_str = (now_utc + timedelta(minutes=10)).isoformat() + 'Z' # Event for 10 minutes

        event_body = {
            'summary': '🛡️ ClawdBot Security: Billing Check',
            'description': f"Billing ID: {BILLING_ACCOUNT_ID}\n\nConfigured Budgets:\n{budget_summary}\n\nStatus: SYSTEM_ALIVE\n\nVerify manually: https://console.cloud.google.com/billing/{BILLING_ACCOUNT_ID}/reports",
            'start': {'dateTime': start_str},
            'end': {'dateTime': end_str},
            'colorId': '11',
        }

        calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        print("Alert added to Google Calendar.")

        # Send email report (basic version for now)
        email_subject = "ClawdBot API Billing Report"
        email_body = f"""鈴木さん、過去30分のAPI使用状況を報告します。

詳細情報:
{budget_summary}

Google Cloud Console: https://console.cloud.google.com/billing/{BILLING_ACCOUNT_ID}/reports"""
        send_email(gmail_service, email_subject, email_body)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
