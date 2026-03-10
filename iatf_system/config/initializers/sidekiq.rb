# frozen_string_literal: true

Sidekiq.configure_server do |config|
  config.redis = { url: 'redis://redis:6379/0' }

  # ログ設定を追加
  config.logger = ActiveSupport::Logger.new('log/sidekiq.log')
  config.logger.level = Logger::INFO
end

Sidekiq.configure_client do |config|
  config.redis = { url: 'redis://redis:6379/0' }
end
