import smtplib
from email.mime.text import MIMEText
import json
import os

def test_send():
    # クラウドボット環境の制限や設定を確認するため、
    # まずは一般的なSMTP設定（もしあれば）を探すか、
    # 鈴木さんの指定したスクリプトの内容を推測してテストします。
    
    sender = "clawdbot@example.com"
    receiver = "y.suzuki.hk@gmail.com"
    msg = MIMEText("This is a debug mail from Clawdbot to check email connectivity.")
    msg['Subject'] = 'Clawdbot Email Debug'
    msg['From'] = sender
    msg['To'] = receiver

    print(f"Attempting to connect to mail server...")
    # ここでは実際のSMTPサーバがないため失敗することが予想されますが、
    # エラーメッセージから原因（接続拒否、タイムアウト、認証エラー等）を特定します。
    try:
        # 一般的なポートを試行
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            print("Connected to smtp.gmail.com:587")
    except Exception as e:
        print(f"Error connecting to smtp.gmail.com: {e}")

if __name__ == "__main__":
    test_send()
