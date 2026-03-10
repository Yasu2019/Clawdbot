# frozen_string_literal: true

# app/controllers/verification_controller.rb
class VerificationController < ActionController::Base
  protect_from_forgery with: :exception
  include Devise::Controllers::Helpers

  def verify
    user = User.find_by(verification_token: params[:token])

    Rails.logger.info("DEBUG: Current server time: #{Time.current}")
    Rails.logger.info("Received token: #{params[:token]}")
    Rails.logger.info("DEBUG: Found user: #{user.inspect}")

    # ユーザーが存在する場合のみ、詳細な情報をログに出力
    if user
      Rails.logger.info("User's stored token: #{user.verification_token}")
      Rails.logger.info("User's token expiry: #{user.token_expiry}")
      Rails.logger.info("DEBUG: Token expiry time: #{user.token_expiry}")
    end

    Rails.logger.info("Called from: #{caller.first}")

    # /app/ ディレクトリからの呼び出しのみを取得
    application_calls = caller.select { |line| line.include?('/app/') }[0, 3]
    application_calls.each_with_index do |call, index|
      Rails.logger.info("Call #{index + 1}: #{call}")
    end

    if user.nil?
      redirect_to new_user_session_path, alert: 'トークンが存在しません。'
      return
    end

    if user.token_expiry < Time.current
      redirect_to new_user_session_path, alert: 'トークンが期限切れです。'
      return
    end

    if user.token_expiry > Time.current
      # トークンをリセット
      user.update(verification_token: nil, token_expiry: nil)
      sign_in(user)
      redirect_to new_user_session_path, notice: 'ログインしてください'
    else
      redirect_to new_user_session_path, alert: 'トークンが無効です。'
    end
  end
end
