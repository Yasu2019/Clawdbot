class DatabaseBackupService
    def self.perform
      new.perform
    end
  
    def perform
      timestamp = Time.zone.now.strftime("%Y%m%d%H%M%S")
      backup_path = Rails.root.join("db/backup/backup_#{timestamp}.sql")
      FileUtils.mkdir_p(File.dirname(backup_path))
  
      connection_config = Rails.configuration.database_configuration[Rails.env]
      
      command = {
        "host" => connection_config["host"],
        "port" => connection_config["port"],
        "username" => connection_config["username"],
        "dbname" => connection_config["database"],
        "file" => backup_path.to_s
      }
  
      begin
        ActiveRecord::Base.connection.raw_connection.copy_data "COPY (SELECT pg_dump('#{command['dbname']}')) TO STDOUT" do |copy_data|
          File.open(command["file"], "w") do |file|
            while slice = copy_data.readpartial(8192)
              file.write slice
            end
          end
        end
        
        true
      rescue => e
        Rails.logger.error "バックアップ作成中にエラーが発生しました: #{e.message}"
        false
      end
    end
  end