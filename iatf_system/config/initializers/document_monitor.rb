Rails.application.config.after_initialize do
  if Rails.env.production? || ENV['ENABLE_DOCUMENT_MONITOR']
    DocumentMonitorService.new.start
  end
end
