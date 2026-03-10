# frozen_string_literal: true

require 'open3'

module Users
  class SessionsController < Devise::SessionsController
    def allowed_ips
      ENV['ALLOWED_IPS'].to_s.split(',').map(&:strip)
    end

    def allowed_emails
      ENV['ALLOWED_EMAILS'].to_s.split(',').map(&:strip)
    end

    def ip_restriction_enabled?
      ENV['ENABLE_IP_RESTRICTION'].to_s.downcase == 'true'
    end

    rescue_from ActionController::InvalidAuthenticityToken, with: :handle_invalid_token

    # 既存のnewメソッドは変更なし
    def new
      Rails.logger.debug "New session requested"
      self.resource = resource_class.new
      clean_up_passwords(resource)
      yield resource if block_given?
      respond_with(resource, serialize_options(resource))
    end

    # 既存のcreateメソッドは変更なし
    def create
      Rails.logger.debug "Create session requested"
      Rails.logger.debug "Params: #{params.inspect}"
      @user = User.find_by(email: params[:user][:email])

      Rails.logger.debug "IP: #{request.remote_ip}"
      Rails.logger.debug "Email: #{params[:user][:email]}"
      Rails.logger.debug "IP allowed: #{ip_allowed?}"
      Rails.logger.debug "Email allowed: #{allowed_emails.include?(params[:user][:email].downcase)}"
      Rails.logger.debug "User found: #{@user.inspect}"
      Rails.logger.debug "Password provided: #{params[:user][:password].present?}"
      Rails.logger.debug "Password valid: #{@user&.valid_password?(params[:user][:password])}"

      unless ip_allowed? || allowed_emails.include?(params[:user][:email].downcase)
        Rails.logger.debug "Access denied due to IP or Email restrictions"
        flash.now[:alert] = '管理者以外はミツイ精密社外からログインできません'
        self.resource = resource_class.new
        render :new and return
      end

      if @user&.valid_password?(params[:user][:password])
        Rails.logger.debug "Password is valid"
        if ENV['minipc'] == 'true'
          Rails.logger.debug "Skipping 2FA due to minipc=true"
          sign_in(@user)
          redirect_to products_path and return
        else
          Rails.logger.debug "Proceeding to two-step verification"
          session[:otp_user_id] = @user.id
          redirect_to new_two_step_verification_path and return
        end
      else
        Rails.logger.debug "Invalid email or password"
        self.resource = resource_class.new(sign_in_params)
        clean_up_passwords(resource)
        flash.now[:alert] = '無効なEmail又はパスワードです。'
        render :new
      end
    end

    private

    def ip_allowed?
      return true unless ip_restriction_enabled?
      allowed_ips.include?(request.remote_ip)
    end

    def allowed_ips
      ENV['ALLOWED_IPS'].split(',').map(&:strip)
    end

    def allowed_emails
      ENV['ALLOWED_EMAILS'].split(',').map(&:strip)
    end

    def handle_invalid_token
      Rails.logger.debug "Invalid authenticity token detected"
      flash[:alert] = 'セッションの有効期限が切れました。もう一度お試しください。'
      redirect_to new_user_session_path
    end

    def handle_db_connection_error
      Rails.logger.error "Database connection error occurred"
      backup_file_path = backup_postgresql
      formatted_time = Time.zone.now.strftime('%Y年%m月%d日 %H時%M分')
      flash[:alert] = "前回までのデータベースが消失したため、#{formatted_time}のバックアップデータで再開します。"
      restore_database(backup_file_path)
      redirect_to new_user_session_path
    end

    def restore_database(backup_file_path)
      Rails.logger.info "Attempting to restore database from #{backup_file_path}"
      script_path = Rails.root.join('bin', 'restore_latest_backup.sh')
      
      unless File.exist?(script_path)
        Rails.logger.error "Restore script not found at #{script_path}"
        raise "リストアスクリプトが見つかりません"
      end

      result = ActiveRecord::Base.connection.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()")
      
      begin
        conn = ActiveRecord::Base.connection.raw_connection
        conn.exec("DROP DATABASE IF EXISTS #{db_config['database']}_temp")
        conn.exec("CREATE DATABASE #{db_config['database']}_temp")
        
        restore_command = "psql -h #{db_config['host']} -U #{db_config['username']} -d #{db_config['database']}_temp -f #{backup_file_path}"
        conn.exec(restore_command)
        
        conn.exec("ALTER DATABASE #{db_config['database']} RENAME TO #{db_config['database']}_old")
        conn.exec("ALTER DATABASE #{db_config['database']}_temp RENAME TO #{db_config['database']}")
        conn.exec("DROP DATABASE IF EXISTS #{db_config['database']}_old")
        
        Rails.logger.info "Database restoration completed successfully"
      rescue => e
        Rails.logger.error "Database restoration failed: #{e.message}"
        raise "データベースのリストアに失敗しました: #{e.message}"
      ensure
        conn&.close
      end
    end

    def backup_postgresql
      Rails.logger.info "Initiating PostgreSQL backup"
      backup_dir = Rails.root.join('db/backup').to_s
      FileUtils.mkdir_p(backup_dir)

      db_config = Rails.configuration.database_configuration[Rails.env]
      timestamp = Time.zone.now.strftime('%Y%m%d%H%M%S')
      backup_file = File.join(backup_dir, "backup_#{timestamp}.sql")

      begin
        conn = ActiveRecord::Base.connection.raw_connection
        File.open(backup_file, 'w') do |file|
          conn.copy_data "COPY (SELECT pg_dump_all()) TO STDOUT" do |copy_data|
            while chunk = copy_data.gets
              file.write(chunk)
            end
          end
        end

        Rails.logger.info "Backup created successfully: #{backup_file}"
        backup_file
      rescue => e
        Rails.logger.error "Backup creation failed: #{e.message}"
        raise "バックアップの作成に失敗しました: #{e.message}"
      ensure
        conn&.close if conn
      end
    end

    private

    def db_config
      @db_config ||= Rails.configuration.database_configuration[Rails.env]
    end
  end
end