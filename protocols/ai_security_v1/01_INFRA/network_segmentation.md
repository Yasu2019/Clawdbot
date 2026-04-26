# NETWORK SEGMENTATION

## 推奨
- AI実行系は 127.0.0.1 バインドを基本とする
- 外部公開が必要なサービスだけ reverse proxy で限定公開
- 社内LANや家庭内LANの他端末へ横展開できないようにする

## 例
- OpenClaw: 127.0.0.1 のみ
- Ollama: 127.0.0.1 のみ
- Langfuse: 127.0.0.1 のみ
- Qdrant / DB: 127.0.0.1 または internal network のみ

## 追加策
- Windows Defender Firewall / ufw で outbound 制限
- VLAN 分離または専用 mini PC 化
- SSH は鍵認証 + 接続元制限
