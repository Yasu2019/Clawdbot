# frozen_string_literal: true

class CacheDataJob
  include Sidekiq::Worker

  def perform(user_id)
    # データを取得
    products = Product.includes(:documents_attachments)
    Rails.logger.info("Fetched #{products.count} products")

    touans = Touan.where(user_id:)
    Rails.logger.info("Fetched #{touans.count} touans for user ID: #{user_id}")

    user = User.find(user_id)
    Rails.logger.info("Fetched user with ID: #{user_id}")

    auditor = user.auditor
    Rails.logger.info("Fetched auditor for user ID: #{user_id}")

    iatf_data_audit = Iatf.where(audit: '2')
    Rails.logger.info("Fetched #{iatf_data_audit.count} iatf_data_audit")

    iatf_data_audit_sub = Iatf.where(audit: '1')
    Rails.logger.info("Fetched #{iatf_data_audit_sub.count} iatf_data_audit_sub")

    csrs = Csr.all
    Rails.logger.info("Fetched #{csrs.count} csrs")

    iatflists = Iatflist.all
    Rails.logger.info("Fetched #{iatflists.count} iatflists")

    # キャッシュに保存
    Rails.cache.write('products_all', products)
    Rails.logger.info('Saved products to cache')

    Rails.cache.write("touans_#{user_id}", touans)
    Rails.logger.info("Saved touans to cache for user ID: #{user_id}")

    Rails.cache.write("user_#{user_id}", user)
    Rails.logger.info("Saved user to cache for user ID: #{user_id}")

    Rails.cache.write("auditor_#{user_id}", auditor)
    Rails.logger.info("Saved auditor to cache for user ID: #{user_id}")

    Rails.cache.write("iatf_data_audit_#{user_id}", iatf_data_audit)
    Rails.logger.info("Saved iatf_data_audit to cache for user ID: #{user_id}")

    Rails.cache.write("iatf_data_audit_sub_#{user_id}", iatf_data_audit_sub)
    Rails.logger.info("Saved iatf_data_audit_sub to cache for user ID: #{user_id}")

    Rails.cache.write('csrs', csrs)
    Rails.logger.info('Saved csrs to cache')

    Rails.cache.write('iatflists', iatflists)
    Rails.logger.info('Saved iatflists to cache')
  rescue StandardError => e
    # エラーメッセージをログに記録
    Rails.logger.error("CacheDataJob failed for user ID: #{user_id}. Error: #{e.message}")

    # エラーメッセージをメールで送信
    ErrorMailer.send_cache_error(user_id, e.message).deliver_now
  end
end
