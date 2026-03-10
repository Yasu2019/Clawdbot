import consumer from "channels/consumer"

const subscription = consumer.subscriptions.create("DocumentNotificationsChannel", {
  connected() {
    console.log("Connected to DocumentNotificationsChannel");
    // 接続テスト用の通知を表示
    this.showNotification("接続テスト: 通知システムが正常に動作しています");
  },

  disconnected() {
    console.log("Disconnected from DocumentNotificationsChannel");
  },

  received(data) {
    console.log("Received notification data:", data);
    try {
      if (data && typeof data === 'object') {
        console.log("Data is an object");
        if (data.message) {
          console.log("Message found:", data.message);
          this.showNotification(data.message);
        } else {
          console.warn("No message in data:", Object.keys(data));
        }
      } else {
        console.error("Received data is not an object:", typeof data);
      }
    } catch (error) {
      console.error("Error in received handler:", error);
    }
  },

  showNotification(message) {
    try {
      console.log("showNotification called with message:", message);
      
      // 既存の通知を削除
      const existingNotifications = document.querySelectorAll('.document-notification');
      existingNotifications.forEach(notification => {
        notification.remove();
      });

      // 新しい通知を作成
      const notification = document.createElement('div');
      notification.className = 'document-notification';
      notification.textContent = message;
      
      // インライン CSS を適用
      const styles = {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '16px 24px',
        backgroundColor: '#4CAF50',
        color: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        zIndex: '9999',
        opacity: '0',
        transition: 'opacity 0.3s ease-in-out',
        fontSize: '16px',
        fontWeight: '500',
        maxWidth: '400px',
        wordBreak: 'break-word'
      };

      // スタイルを適用
      Object.assign(notification.style, styles);
      console.log("Styles applied to notification");

      // DOMに追加
      document.body.appendChild(notification);
      console.log("Notification element added to DOM");

      // フェードイン
      requestAnimationFrame(() => {
        notification.style.opacity = '1';
        console.log("Notification fade-in started");
      });

      // 通知の表示時間を取得
      const durationMeta = document.querySelector('meta[name="notification-duration"]');
      const duration = (durationMeta ? parseInt(durationMeta.content, 10) : 15) * 1000;
      console.log("Notification will be shown for", duration, "ms");

      // フェードアウトと削除
      setTimeout(() => {
        console.log("Starting notification fade-out");
        notification.style.opacity = '0';
        
        setTimeout(() => {
          if (notification && notification.parentNode) {
            notification.parentNode.removeChild(notification);
            console.log("Notification removed from DOM");
          }
        }, 300);
      }, duration);

    } catch (error) {
      console.error("Error in showNotification:", error);
    }
  }
});
