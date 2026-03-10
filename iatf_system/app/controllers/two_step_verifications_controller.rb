# frozen_string_literal: true

class TwoStepVerificationsController < ApplicationController
  skip_before_action :authenticate_user!

  def new
    # セッションにotp_user_idが存在しない場合やユーザーが見つからない場合の処理を追加
    unless session[:otp_user_id] && User.exists?(id: session[:otp_user_id])
      flash[:alert] = 'ユーザーが見つかりませんでした。もう一度ログインしてください。'
      redirect_to new_user_session_path # これはDeviseのログインページへのパスです
      return
    end

    @user = User.find(session[:otp_user_id])

    @user.update!(otp_secret: User.generate_otp_secret(32)) unless @user.otp_secret

    issuer = 'IATF16949'
    label = "#{issuer}:#{@user.email}"

    uri = @user.otp_provisioning_uri(label, issuer:)

    Rails.logger.debug { "URI: #{uri}" }

    @qr_code = RQRCode::QRCode.new(uri)
                              .as_png(resize_exactly_to: 200)
                              .to_data_url

    # キャッシュジョブの開始をログに記録
    Rails.logger.info("Starting CacheDataJob for user ID: #{@user.id}")

    # QRコードが生成された直後にキャッシュジョブを呼び出す
    CacheDataJob.perform_async(@user.id)
    Rails.logger.info("Successfully started CacheDataJob for user ID: #{@user.id}")

    Rails.logger.debug { "QR Code: #{@qr_code}" }
  end

  def create
    @user = User.find(session[:otp_user_id])

    if @user.validate_and_consume_otp!(params[:otp_attempt])
      Rails.logger.info("Two-factor authentication succeeded for user #{@user.email}")

      @user.update!(otp_required_for_login: true)
      session.delete(:otp_user_id)

      flash.delete(:alert)

      after_two_factor_authenticated # ここでメール送信のメソッドを呼び出す
      Rails.logger.info('after_two_factor_authenticated method called.')

      # メッセージを設定してホームページにリダイレクト
      flash[:notice] = 'メールを送信しました。メール内のリンクからログインしてください。'
      redirect_to root_path
    else
      # ワンタイムパスワードが不正な場合のフラッシュメッセージを追加
      flash[:alert] = '間違ったパスワードが入力されました'

      issuer = 'IATF16949'
      label = "#{issuer}:#{@user.email}"

      uri = @user.otp_provisioning_uri(label, issuer:)

      @qr_code = RQRCode::QRCode.new(uri)
                                .as_png(resize_exactly_to: 200)
                                .to_data_url

      render :new
    end
  end

  def after_two_factor_authenticated
    password = generate_random_password
    token = SecureRandom.hex(10) # トークンを生成します
    expiry = 24.hours.from_now.in_time_zone

    # トークンとその有効期限をユーザーモデルに保存します
    @user.update(verification_token: token, token_expiry: expiry)

    session[:download_password] = password

    Rails.logger.info("Generated password: #{password}")
    Rails.logger.info("Session download_password: #{session[:download_password]}")

    # パスワードをvolumeフォルダのpass_word.txtに保存
    file_path = Rails.root.join('volume', 'pass_word.txt')

    # 既存のファイルが存在する場合は削除
    File.delete(file_path) if File.exist?(file_path)

    # 新しいパスワードをファイルに書き込む
    File.open(file_path, 'a') do |file|
      file.puts(password)
    end

    # トークンをメールに含めるようにDownloadMailerを更新します
    DownloadMailer.send_download_password(@user.email, password, token).deliver_now

    Rails.logger.info("Generated token: #{token}")
    Rails.logger.info("after_two_factor_authenticated called. Generated password: #{password}")
  end
end
