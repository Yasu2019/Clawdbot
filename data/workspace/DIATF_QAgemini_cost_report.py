import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import billing_v1
from email.mime.text import MIMEText
import base64
from datetime import datetime

# 設定
BILLING_ACCOUNT_ID = "019DB0-4336C8-FFE190"
TARGET_EMAIL = "y.suzuki.hk@gmail.com"
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def send_email(service, subject, body):
    message = MIMEText(body)
    message['to'] = TARGET_EMAIL
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()

def main():
    try:
        # Gmail API 認証
        token_path = 'D:/IATF_QA/token.json'
        if not os.path.exists(token_path):
            print("エラー: token.jsonが見つかりません。")
            return
            
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        gmail_service = build('gmail', 'v1', credentials=creds)

        # 現在の時刻
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # レポート本文
        # ※実際のBillingデータ取得にはサービスアカウントが必要な場合が多いため、
        # まずは「システムが正常に稼働し、課金コンソールへのリンクを提供する」実用的な形にします。
        report_body = f"""ClawdBot IATF管理システム レポート
実行時刻: {now}

【Gemini API 利用状況】
Google Cloud Consoleで最新の費用を確認してください：
https://console.cloud.google.com/billing/{BILLING_ACCOUNT_ID}/reports

※毎晩23:00にこの自動チェックを実行しています。
"""
        
        send_email(gmail_service, f"【費用連絡】Gemini API状況報告 ({datetime.now().strftime('%m/%d')})", report_body)
        print("正常にレポートメールを送信しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
