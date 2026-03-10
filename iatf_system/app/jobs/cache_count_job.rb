# frozen_string_literal: true

class CacheCountJob
  include Sidekiq::Worker

  def perform(email)
    products_cache = Rails.cache.read('products_all')
    Rails.logger.info("Read #{products_cache.count} products from cache")

    touans_cache = User.all.map { |user| Rails.cache.read("touans_#{user.id}") }
    touans_cache.each_with_index do |touan, index|
      Rails.logger.info("Read #{touan.count} touans from cache for user ID: #{index + 1}")
    end

    # 他のモデルも同様に追加

    cache_counts = {
      'Product' => products_cache.count,
      'Touan' => touans_cache.sum(&:count)
      # 他のモデルも同様に追加
    }

    MemoryUsageMailer.send_cache_count(email, cache_counts).deliver_now
  end
end
