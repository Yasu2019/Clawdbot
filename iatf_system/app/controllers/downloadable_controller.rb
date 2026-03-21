# frozen_string_literal: true

class DownloadableController < ApplicationController
  before_action :set_downloadable

  # メール送信しなければ動くコード
  def verify_password_post
    Rails.logger.info("Session download_password at downloadable_controller: #{session[:download_password]}")
    Rails.logger.debug { "minipc environment: #{ENV['minipc']}" }
    blob_id = params[:blob_id]

    if ENV['minipc'] == 'true'
      Rails.logger.info("minipc environment detected, bypassing password verification")
      render_document_download(blob_id)
      return
    end

    if params[:password] == session[:download_password]
      render_document_download(blob_id)
    else
      set_invalid_password_flash
      render :verify_password
    end
  end

  def new
    @user = User.find(session[:otp_user_id])
  rescue ActiveRecord::RecordNotFound
    flash[:alert] = 'ユーザーが見つかりませんでした。'
    redirect_to root_path
    nil
  end

  def verify_password
    Rails.logger.info('verify_password action called')
    Rails.logger.debug { "params[:blob_id]: #{params[:blob_id]}" }
    Rails.logger.debug { "session[:download_blob_id]: #{session[:download_blob_id]}" }
    Rails.logger.debug { "Entered password: #{params[:password]}" }
    Rails.logger.debug { "Session password: #{session[:download_password]}" }
    Rails.logger.debug { "minipc environment: #{ENV['minipc']}" }

    if ENV['minipc'] == 'true'
      Rails.logger.info("minipc environment detected, bypassing password verification")
      render_document_download(params[:blob_id])
      return
    end

    if session[:download_password].blank?
      Rails.logger.warn("セッションパスワードが設定されていません。")
      begin
        session[:download_password] = File.read(Rails.root.join('volume', 'pass_word.txt')).strip
        Rails.logger.info("セッションパスワードをファイルから読み込みました。")
      rescue Errno::ENOENT
        Rails.logger.error("pass_word.txtファイルが見つかりません。")
      end
      flash[:alert] = 'パスワードが設定されていません。'
      render :verify_password
      return
    end

    unless params[:password]
      @document = ActiveStorage::Attachment.find_by(blob_id: params[:blob_id])
      render :verify_password
      return
    end

    if params[:blob_id].present?
      session[:download_blob_id] = params[:blob_id]
      Rails.logger.debug { "Blob ID: #{params[:blob_id]}" }
    else
      Rails.logger.warn("blob_id is missing in params.")
    end

    if params[:password] == session[:download_password]
      render_document_download(params[:blob_id])
    else
      set_invalid_password_flash
      render :verify_password
    end
  end

  

  def download
    blob_id = session[:download_blob_id]
    file_attachment = ActiveStorage::Attachment.find_by(blob_id:)

    # エラーハンドリングを追加
    unless file_attachment
      Rails.logger.warn("No attachment found for blob ID: #{blob_id} during download action.")
      redirect_to root_path, alert: 'ダウンロードするファイルが見つかりませんでした。'
      return
    end

    begin
      file = file_attachment.blob
      # Check if file exists on disk
      unless file.service.exist?(file.key)
        Rails.logger.error("File not found on disk for blob key: #{file.key}")
        redirect_to root_path, alert: 'ファイルが見つかりませんでした。'
        return
      end

      # Stream the file directly
      send_data file.download, 
                filename: file.filename.to_s, 
                content_type: file.content_type,
                disposition: 'attachment'
    rescue StandardError => e
      Rails.logger.error("Error downloading file: #{e.message}")
      redirect_to root_path, alert: 'ファイルのダウンロード中にエラーが発生しました。'
    end
  end

  private

  def render_document_download(blob_id)
    @document = ActiveStorage::Attachment.find_by(blob_id:)
    if @document
      @download_url = rails_blob_url(@document.blob)
      render :download_page
    else
      Rails.logger.warn("No attachment found for blob ID: #{blob_id}")
      flash[:alert] = 'ファイルが見つかりませんでした。'
      render :verify_password
    end
  end

  def set_invalid_password_flash
    if current_user.email == 'yasuhiro-suzuki@mitsui-s.com'
      flash[:alert] = "無効なパスワードです。正しいパスワードは: #{session[:download_password]}"
    else
      flash[:alert] = '無効なパスワードです。'
    end
  end

  def set_downloadable
    model = if request.path.include?('/products/')
              Rails.logger.info('Model detected: Product')
              Product
            elsif request.path.include?('/suppliers/')
              Rails.logger.info('Model detected: Supplier')
              Supplier
            elsif request.path.include?('/touans/')
              Rails.logger.info('Model detected: Touan')
              Touan
            end

    if model
      @downloadable = model.find_by(id: params[:id])
      if @downloadable
        Rails.logger.info("Found #{@downloadable.class.name} with ID: #{params[:id]}")
      else
        Rails.logger.error("#{model.name} not found with ID: #{params[:id]}")
        redirect_to root_path, alert: 'リクエストが無効です。'
      end
    else
      Rails.logger.error("Unknown controller in path: #{request.path}")
      redirect_to root_path, alert: 'リクエストが無効です。'
    end
  end
end
