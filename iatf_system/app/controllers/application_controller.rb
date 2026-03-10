# frozen_string_literal: true

class ApplicationController < ActionController::Base
  helper ChartDataHelper # ChartDataHelper をインクルード

  # データベース関連のエラーを捕捉
=begin
rescue_from ActiveRecord::StatementInvalid, PG::Error do |exception|
  # エラーをログに記録
  Rails.logger.error exception.message
  Rails.logger.error exception.backtrace.join("\n")

  # リストアスクリプトを実行して結果を確認
  if system('/root/restore_latest_backup.sh')
    flash[:notice] = I18n.t('application_controller.restore_notice')
    redirect_to request.referer || root_path
  else
    render plain: 'データベースのリストアに失敗しました。サポートに連絡してください。', status: :internal_server_error
  end
end
=end

  # ユーザー認証を要求する
  before_action :authenticate_user!

  # ログアウト後のリダイレクト先
  def after_sign_out_path_for(_resource_or_scope)
    new_user_session_path
  end

  # 2要素認証成功後にメールを送信
  def after_two_factor_authenticated
    password = generate_random_password

    session[:download_password] = password
    DownloadMailer.send_download_password(current_user.email, password).deliver_now
    # 下記のメールアドレスは実際のアプリケーションで使われているメールアドレスに置き換えてください
    DownloadMailer.send_download_password('yasuhiro-suzuki@mitsui-s.com', password).deliver_now

    Rails.logger.info("after_two_factor_authenticated called. Generated password: #{password}")
    Rails.logger.info("after_two_factor_authenticated called. Generated Session password: #{session[:download_password]}")
  end

  private

  # ランダムなパスワードを生成
  def generate_random_password
    chars = [('a'..'z'), ('A'..'Z'), ('0'..'9'), ['!', '@', '#', '$', '%', '^', '&', '*']].map(&:to_a).flatten
    (0...30).map { chars[rand(chars.length)] }.join
  end
end
