# frozen_string_literal: true

require_relative 'boot'
require 'rails'
# Pick the frameworks you want:
require 'active_model/railtie'
require 'active_job/railtie'
require 'active_record/railtie'
require 'active_storage/engine'
require 'action_controller/railtie'
require "action_mailer/railtie"
# require "action_mailbox/engine"
require 'action_text/engine'
require 'action_view/railtie'
require 'action_cable/engine'
# require "rails/test_unit/railtie"

# Require the gems listed in Gemfile, including any gems
# you've limited to :test, :development, or :production.
Bundler.require(*Rails.groups)

require 'rails/all'
require 'csv'
# require "importmap/rails"

# caxlsxを明示的に要求
require 'caxlsx'

module Myapp
  class Application < Rails::Application
    config.assets.enabled = true
    # Initialize configuration defaults for originally generated Rails version.
    config.load_defaults 7.0

    # SSL設定を完全に無効化
    config.ssl_options = { hsts: false, secure_cookies: false }
    config.force_ssl = false
    config.action_controller.default_url_options = { protocol: 'http' }

    # caxlsxを自動ロードパスに追加
    config.autoload_paths += %W(#{config.root}/lib)

    # その他の設定...
    config.i18n.default_locale = :ja
    config.time_zone = 'Tokyo'
    config.active_record.default_timezone = :local
    config.active_record.encryption.key_derivation_salt = ENV.fetch('KEY_DERIVATION_SALT', nil)
    config.active_record.encryption.primary_key = ENV.fetch('PRIMARY_KEY', nil)

    # メールのタイムゾーン設定
    config.action_mailer.default_options = { 
      from: 'mitsui.seimitsu.iatf16949@gmail.com',
      charset: 'UTF-8',
      time_zone: 'Tokyo'
    }

    # Don't generate system test files.
    config.generators.system_tests = nil
  end
end