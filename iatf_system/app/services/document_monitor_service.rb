class DocumentMonitorService
  def initialize
    @watch_path = Rails.root.join('db', 'latest_documents')
    @interval = ENV.fetch('DOCUMENT_CHECK_INTERVAL', 5).to_i  # インターバルを短くする
    Rails.logger.info "DocumentMonitorService: Initialized with watch path: #{@watch_path}"
    Rails.logger.info "DocumentMonitorService: Check interval: #{@interval} seconds"
  end

  def start
    ensure_watch_directory
    setup_listener
  end

  private

  def ensure_watch_directory
    unless Dir.exist?(@watch_path)
      FileUtils.mkdir_p(@watch_path)
      Rails.logger.info "DocumentMonitorService: Created directory #{@watch_path}"
    end
  end

  def setup_listener
    Rails.logger.info "DocumentMonitorService: Setting up listener..."
    
    # Docker環境での監視に最適化された設定
    @listener = Listen.to(
      @watch_path,
      force_polling: true,      # ポーリングモードを強制
      polling_fallback_message: false,
      wait_for_delay: 0.5,      # 変更検出後の待機時間を短縮
      latency: 0.1,             # レイテンシーを短縮
      only: /\.(pdf|doc|docx|xls|xlsx)$/i
    ) do |modified, added, removed|
      Rails.logger.tagged("DocumentMonitorService") do
        Rails.logger.info "Changes detected at #{Time.current}"
        Rails.logger.info "  - Added files: #{added.inspect}"
        Rails.logger.info "  - Modified files: #{modified.inspect}"
        Rails.logger.info "  - Removed files: #{removed.inspect}"
        
        handle_changes(modified, added, removed)
      end
    end

    @listener.start
    Rails.logger.info "DocumentMonitorService: Listener started successfully"
    
    # 定期的なポーリングを開始
    start_polling
  rescue => e
    Rails.logger.error "DocumentMonitorService: Error setting up listener - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    raise
  end

  def handle_changes(modified, added, removed)
    return if added.empty? && modified.empty? && removed.empty?

    Rails.logger.tagged("DocumentMonitorService") do
      Rails.logger.info "Processing changes..."
      
      added.each do |file_path|
        process_new_file(file_path)
      end
    end
  rescue => e
    Rails.logger.error "DocumentMonitorService: Error handling changes - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end

  def process_new_file(file_path)
    filename = File.basename(file_path)
    Rails.logger.tagged("DocumentMonitorService") do
      Rails.logger.info "Processing new file: #{filename}"
      
      return unless File.exist?(file_path)
      
      # ファイルが完全に書き込まれるまで少し待機
      sleep 0.5
      
      # ActiveStorageのBlobを検索
      existing_blob = ActiveStorage::Blob.find_by(filename: filename)
      
      if existing_blob.nil?
        Rails.logger.info "New file detected: #{filename}"
        broadcast_notification('new', filename)
      else
        Rails.logger.info "File already exists: #{filename}"
      end
    end
  rescue => e
    Rails.logger.error "Error processing file #{filename} - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end

  def broadcast_notification(type, filename)
    message = case type
              when 'new'
                "新規ファイルがあります: #{filename}"
              when 'updated'
                "更新ファイルがあります: #{filename}"
              end

    Rails.logger.tagged("DocumentMonitorService") do
      Rails.logger.info "Broadcasting notification: #{message}"
      ActionCable.server.broadcast('document_notifications_channel', { message: message })
      Rails.logger.info "Broadcast completed"
    end
  rescue => e
    Rails.logger.error "Error broadcasting notification - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end

  def start_polling
    Thread.new do
      Rails.logger.tagged("DocumentMonitorService") do
        loop do
          begin
            sleep @interval
            # 明示的にディレクトリをスキャン
            Dir.glob(File.join(@watch_path, '*.{pdf,doc,docx,xls,xlsx}')).each do |file|
              process_new_file(file) if File.mtime(file) > Time.current - @interval
            end
          rescue => e
            Rails.logger.error "Polling error - #{e.message}"
          end
        end
      end
    end
  end
end
