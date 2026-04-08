# frozen_string_literal: true

require "csv"
require "fileutils"
require "json"
require "pathname"
require "stringio"
require "zip"

class JqaAuditReportIngestService
  DOCUMENTS_DIR = Rails.root.join("db/documents")
  RECORD_CSV_PATH = Rails.root.join("db/record/attachedfile.csv")
  STATUS_PATH = Rails.root.join("db/jqa_audit_report_uploads_status.json")
  DOCUMENT_CATEGORY = "JQA審査報告書"
  DEFAULT_STATUS = "完了"
  DEFAULT_CATEGORY = "2"
  DEFAULT_OBJECT = "object1"

  class << self
    def call(files:, description: nil)
      new(files:, description:).call
    end
  end

  def initialize(files:, description: nil)
    @files = Array(files).compact
    @description = description.presence || "JQA審査報告書アップロード"
  end

  def call
    FileUtils.mkdir_p(DOCUMENTS_DIR)

    imported = []
    @files.each do |file|
      imported.concat(import_entries(file))
    end

    status_payload = {
      imported_at: Time.current.iso8601,
      imported_count: imported.length,
      imported_files: imported
    }
    File.write(STATUS_PATH, JSON.pretty_generate(status_payload))

    {
      imported_files: imported,
      imported_count: imported.length,
      status_path: STATUS_PATH.to_s
    }
  end

  private

  def import_entries(file)
    filename = Pathname.new(file.original_filename.to_s).basename.to_s
    ext = File.extname(filename).downcase

    result =
      if ext == ".zip"
        import_zip_entries(file)
      else
        [import_binary(filename: filename, bytes: file.read)]
      end
    result
  ensure
    file.rewind if file.respond_to?(:rewind)
  end

  def import_zip_entries(file)
    imported = []
    buffer = StringIO.new(file.read)
    Zip::File.open_buffer(buffer) do |zip_file|
      zip_file.each do |entry|
        next if entry.directory?
        next unless File.extname(entry.name).downcase == ".pdf"

        entry_name = Pathname.new(entry.name).basename.to_s
        imported << import_binary(filename: entry_name, bytes: entry.get_input_stream.read)
      end
    end
    imported
  ensure
    file.rewind if file.respond_to?(:rewind)
  end

  def import_binary(filename:, bytes:)
    stored_name = allocate_filename(filename)
    stored_path = DOCUMENTS_DIR.join(stored_name)
    File.binwrite(stored_path, bytes)

    metadata = build_metadata(stored_name)
    append_attachedfile_csv(metadata)
    product = find_or_create_product(metadata, stored_path)

    {
      stored_name: stored_name,
      stored_path: stored_path.to_s,
      product_id: product.id,
      category: metadata["category"],
      document_category: metadata["documentcategory"],
      document_number: metadata["documentnumber"]
    }
  end

  def allocate_filename(original_name)
    candidate = sanitize_filename(original_name)
    return candidate unless File.exist?(DOCUMENTS_DIR.join(candidate))
    return candidate unless csv_contains_filename?(candidate)

    stem = File.basename(candidate, ".*")
    ext = File.extname(candidate)
    suffix = Time.current.strftime("%Y%m%d_%H%M%S")
    "#{stem}_#{suffix}#{ext}"
  end

  def sanitize_filename(name)
    cleaned = name.to_s.encode("UTF-8", invalid: :replace, undef: :replace, replace: "_")
    cleaned.gsub(/[\\\/:*?"<>|]/, "_").strip
  end

  def build_metadata(filename)
    now_text = Time.current.strftime("%Y-%m-%d %H:%M:%S")
    base_name = File.basename(filename, File.extname(filename))
    inferred_year = infer_year(base_name)

    {
      "filename" => filename,
      "category" => DEFAULT_CATEGORY,
      "partnumber" => "",
      "materialcode" => "",
      "phase" => "",
      "stage" => "",
      "description" => @description,
      "status" => DEFAULT_STATUS,
      "documenttype" => File.extname(filename).delete(".").downcase,
      "documentname" => base_name,
      "documentrev" => "",
      "documentcategory" => DOCUMENT_CATEGORY,
      "documentnumber" => next_document_number(inferred_year),
      "start_time" => now_text,
      "deadline_at" => now_text,
      "end_at" => now_text,
      "goal_attainment_level" => "100",
      "tasseido" => "100",
      "object" => DEFAULT_OBJECT
    }
  end

  def infer_year(text)
    match = text.match(/(20\d{2})/)
    match && match[1].to_i
  end

  def next_document_number(year)
    base_year = year || Time.current.year
    max_sequence = 0
    if File.exist?(RECORD_CSV_PATH)
      File.foreach(RECORD_CSV_PATH, encoding: "UTF-8") do |line|
        next unless line.include?(",#{DOCUMENT_CATEGORY},")
        match = line.match(/#{base_year}-JQA-(\d{3})/)
        max_sequence = [max_sequence, match[1].to_i].max if match
      end
    end
    format("%<year>d-JQA-%<seq>03d", year: base_year, seq: max_sequence + 1)
  end

  def append_attachedfile_csv(metadata)
    headers = csv_headers
    ensure_record_csv_exists(headers)
    return if csv_contains_filename?(metadata["filename"])

    # バリデーションの実行
    validator = CsvValidationService.attachedfile_validator
    # DictReader形式をシミュレートするためHashとして検証
    unless validator.validate_row(metadata, "Internal Append")
      Rails.logger.error "JqaAuditReportIngest: Validation failed for #{metadata['filename']}. Errors: #{validator.errors.join(', ')}"
      return false
    end

    CSV.open(RECORD_CSV_PATH, "a", write_headers: false, encoding: "UTF-8") do |csv|
      csv << headers.map { |header| metadata[header] }
    end
  end

  def csv_contains_filename?(filename)
    return false unless File.exist?(RECORD_CSV_PATH)

    prefix = "#{filename},"
    File.foreach(RECORD_CSV_PATH, encoding: "UTF-8") do |line|
      return true if line.start_with?(prefix)
    end
    false
  end

  def csv_headers
    @csv_headers ||= begin
      if File.exist?(RECORD_CSV_PATH)
        CSV.open(RECORD_CSV_PATH, "r", &:readline)
      else
        %w[
          filename category partnumber materialcode phase stage description status documenttype
          documentname documentrev documentcategory documentnumber start_time deadline_at end_at
          goal_attainment_level tasseido object
        ]
      end
    end
  end

  def ensure_record_csv_exists(headers)
    return if File.exist?(RECORD_CSV_PATH)

    FileUtils.mkdir_p(RECORD_CSV_PATH.dirname)
    CSV.open(RECORD_CSV_PATH, "w", write_headers: true, headers: headers, encoding: "UTF-8") {}
  end

  def find_or_create_product(metadata, stored_path)
    existing = Product
      .joins(documents_attachments: :blob)
      .where(category: metadata["category"], documentcategory: metadata["documentcategory"])
      .where(active_storage_blobs: { filename: metadata["filename"] })
      .first
    return existing if existing.present?

    product = Product.new(
      category: metadata["category"],
      partnumber: metadata["partnumber"],
      materialcode: metadata["materialcode"],
      phase: metadata["phase"],
      stage: metadata["stage"],
      description: metadata["description"],
      status: metadata["status"],
      documenttype: metadata["documenttype"],
      documentname: metadata["documentname"],
      documentrev: metadata["documentrev"],
      documentcategory: metadata["documentcategory"],
      documentnumber: metadata["documentnumber"],
      start_time: metadata["start_time"],
      deadline_at: metadata["deadline_at"],
      end_at: metadata["end_at"],
      goal_attainment_level: metadata["goal_attainment_level"],
      tasseido: metadata["tasseido"],
      object: metadata["object"]
    )
    product.documents.attach(io: File.open(stored_path, "rb"), filename: metadata["filename"])
    product.save!
    product
  end
end
