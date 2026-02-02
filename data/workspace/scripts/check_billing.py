import os
import base64
from email.mime.text import MIMEText
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- CONFIG ---
BILLING_ACCOUNT_ID = "019DB0-4336C8-FFE190"
# Path inside container
SERVICE_ACCOUNT_FILE = '/home/node/clawd/D:/IATF_QA/billing_key.json' 
GMAIL_TOKEN_FILE = '/home/node/clawd/token.json' # Using the new working token in workspace root
TARGET_EMAIL = "y.suzuki.hk@gmail.com"
COST_THRESHOLD_JPY = 500 # Alert threshold

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
        print("--- Starting Billing Check ---")
        
        # 1. Billing Auth
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        billing_service = build('billingbudgets', 'v1', credentials=creds)
        
        # 2. Get Budget Info (Since we can't easily get exact cost without BigQuery, using Budget Metadata as proxy for connectivity first)
        # Note: To get ACTUAL cost, we'd traditionally need Cloud Monitoring metrics.
        # But let's try to see if the budget object contains 'current_spend' which some versions might have?
        # Actually, budgets.list only returns rules.
        # However, for a "Safety Guard", verifying that we CAN connect is step 1.
        # The user's concern is "Unknown usage".
        
        # Let's try to access Cloud Monitoring Method for Cost if possible?
        # Requires 'monitoring.googleapis.com' enabled.
        # For now, let's run the original logic but confirming connectivity.
        
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

        # 3. Calendar Auth (Since we have calendar write scope, but only gmail.readonly)
        import json
        with open(GMAIL_TOKEN_FILE, 'r') as tf:
            token_data = json.load(tf)
        
        CREDENTIALS_FILE = '/home/node/clawd/credentials.json'
        with open(CREDENTIALS_FILE, 'r') as cf:
            cred_data = json.load(cf)
            installed = cred_data.get('installed', cred_data.get('web', {}))
            
        info = {
            'refresh_token': token_data.get('refresh_token'),
            'client_id': installed.get('client_id'),
            'client_secret': installed.get('client_secret'),
            'token_uri': "https://oauth2.googleapis.com/token",
            'scopes': token_data.get('scope', '').split(' ')
        }
        
        creds_user = Credentials.from_authorized_user_info(info)
        calendar_service = build('calendar', 'v3', credentials=creds_user)

        # 4. Report / Alert via Calendar
        # Use UTC explicitly to avoid timezone errors
        now_utc = datetime.utcnow()
        start_str = now_utc.isoformat() + 'Z'
        end_str = (now_utc.replace(minute=(now_utc.minute + 10) % 60)).isoformat() + 'Z'
        
        event_body = {
            'summary': '🛡️ ClawdBot Security: Billing Check',
            'description': f"Billing ID: {BILLING_ACCOUNT_ID}\n\nConfigured Budgets:\n{budget_summary}\n\nStatus: SYSTEM_ALIVE\n\nVerify manually: https://console.cloud.google.com/billing/{BILLING_ACCOUNT_ID}/reports",
            'start': {'dateTime': start_str},
            'end': {'dateTime': end_str},
            'colorId': '11', # Red color
        }

        calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        print("Alert added to Google Calendar.")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
