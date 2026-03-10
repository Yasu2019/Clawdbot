import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import billing_v1
import datetime

# 設定
BILLING_ACCOUNT_ID = "019DB0-4336C8-FFE190"

def main():
    try:
        # Billing API サービスを作成
        # ※認証は、先ほどのロール設定が反映されていれば Google Cloud の環境から自動で行われます
        client = billing_v1.CloudBillingClient()
        
        # 請求アカウントの情報を取得してみるテスト
        name = f"billingAccounts/{BILLING_ACCOUNT_ID}"
        response = client.get_billing_account(name=name)
        
        print(f"成功！請求アカウント名: {response.display_name}")
        print("権限設定は正しく行われています。金額を読み取る準備ができました。")

    except Exception as e:
        print(f"まだ権限が足りないか、反映に時間がかかっています。")
        print(f"エラー内容: {e}")

if __name__ == "__main__":
    main()
