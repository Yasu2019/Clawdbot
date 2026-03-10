# frozen_string_literal: true
# comment
class DownloadMailer < ApplicationMailer
  default from: 'mitsui.seimitsu.iatf16949@gmail.com'

  # app/mailers/download_mailer.rb
  def send_download_password(email, password, token = nil)
    @password = password
    @token = token
    @user = User.find_by(email: email)  # ユーザー情報を取得
    
    # デバッグ用のログ出力
    if @token
      Rails.logger.info("Generated email with token: #{@token}")
      Rails.logger.info("Generated verify_token_url: #{verify_token_url(token: @token, host: 'nys-web.net', protocol: 'https')}")
    end
    
    headers['Date'] = Time.current.in_time_zone('Asia/Tokyo').rfc2822
    
    mail(
      to: email,
      subject: 'Welcome to IATFシステム'
    ) do |format|
      format.text
    end
  end
end
