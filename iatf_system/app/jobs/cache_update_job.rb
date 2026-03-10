# frozen_string_literal: true

# app/jobs/cache_update_job.rb
class CacheUpdateJob
  include Sidekiq::Worker

  def perform
    # Productモデルのデータを取得してキャッシュに保存
    products = Product.includes(:documents_attachments)
    Rails.cache.write('products_all', products)

    # 全てのユーザーのTouanモデルのデータを取得してキャッシュに保存
    User.find_each do |user|
      touans = Touan.where(user_id: user.id)
      Rails.cache.write("touans_#{user.id}", touans)
    end
  end
end

# app/models/touan.rb
class Touan < ApplicationRecord
  after_save :update_cache

  private

  def update_cache
    # Touanが保存または更新されたときにキャッシュ更新ジョブをトリガー
    CacheUpdateJob.perform_async(user_id)
  end
end

# app/models/product.rb
class Product < ApplicationRecord
  after_save :update_cache

  private

  def update_cache
    # Productが保存または更新されたときにキャッシュ更新ジョブをトリガー
    CacheUpdateJob.perform_async
  end
end
