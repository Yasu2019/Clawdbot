# frozen_string_literal: true

class DownloadsController < ApplicationController
  def verify_password
    # リクエストパラメータのログ
    Rails.logger.info("=== Download Verification Process Started ===")
    Rails.logger.info("Request Parameters: #{params.inspect}")
    Rails.logger.info("Current Storage Path: #{Rails.root.join('storage')}")
    Rails.logger.info("Active Storage Service: #{Rails.application.config.active_storage.service}")

    @document = Product.find(params[:id])
    Rails.logger.info("Found Product: #{@document.inspect}")
    
    session[:download_blob_id] = params[:blob_id]
    Rails.logger.info("Stored blob_id in session: #{session[:download_blob_id]}")

    entered_password = params[:password]
    Rails.logger.info("Password verification: #{entered_password == session[:download_password] ? 'matched' : 'not matched'}")

    if entered_password == session[:download_password]
      file_attachment = ActiveStorage::Attachment.find_by(blob_id: session[:download_blob_id])
      Rails.logger.info("Looking for attachment with blob_id: #{session[:download_blob_id]}")
      Rails.logger.info("Found attachment: #{file_attachment.inspect}")

      if file_attachment
        file = file_attachment.blob
        Rails.logger.info("Associated blob: #{file.inspect}")
        Rails.logger.info("Blob key: #{file.key}")
        Rails.logger.info("Checking if blob file exists: #{file.service.exist?(file.key)}")
        
        begin
          @download_url = rails_blob_url(file)
          Rails.logger.info("Generated download URL: #{@download_url}")
        rescue => e
          Rails.logger.error("Error generating download URL: #{e.message}")
          Rails.logger.error(e.backtrace.join("\n"))
        end
      else
        Rails.logger.error("No attachment found for blob ID: #{session[:download_blob_id]}")
        flash[:alert] = 'ファイルが見つかりませんでした。'
        render :verify_password
        nil
      end
    else
      Rails.logger.warn("Invalid password attempt")
      flash[:alert] = 'Invalid password'
      render :verify_password
    end
  end

  def download
    Rails.logger.info("=== Download Process Started ===")
    blob_id = session[:download_blob_id]
    Rails.logger.info("Retrieved blob_id from session: #{blob_id}")

    file_attachment = ActiveStorage::Attachment.find_by(blob_id: blob_id)
    Rails.logger.info("Found attachment: #{file_attachment.inspect}")

    unless file_attachment
      Rails.logger.error("No attachment found for blob ID: #{blob_id} during download action")
      redirect_to root_path, alert: 'ダウンロードするファイルが見つかりませんでした。'
      return
    end

    begin
      file = file_attachment.blob
      Rails.logger.info("Blob details: #{file.inspect}")
      Rails.logger.info("Blob key: #{file.key}")
      Rails.logger.info("Blob filename: #{file.filename}")
      Rails.logger.info("Storage service: #{file.service.class.name}")
      Rails.logger.info("Checking if blob file exists: #{file.service.exist?(file.key)}")
      
      file_data = file.download
      Rails.logger.info("File successfully downloaded from storage")
      
      send_data file_data, filename: file.filename.to_s, disposition: 'attachment'
      Rails.logger.info("File sent to user: #{file.filename}")
    rescue => e
      Rails.logger.error("Error during file download: #{e.message}")
      Rails.logger.error(e.backtrace.join("\n"))
      redirect_to root_path, alert: 'ファイルのダウンロード中にエラーが発生しました。'
    end
  end
end
