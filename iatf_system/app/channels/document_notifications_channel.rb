class DocumentNotificationsChannel < ApplicationCable::Channel
  def subscribed
    stream_from "document_notifications_channel"
  end

  def unsubscribed
    # Any cleanup needed when channel is unsubscribed
  end
end
