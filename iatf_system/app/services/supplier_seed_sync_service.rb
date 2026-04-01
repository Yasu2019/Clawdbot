# frozen_string_literal: true

require "csv"
require "fileutils"
require "json"

class SupplierSeedSyncService
  SOURCE_DIR = Rails.root.join("db/record/supplier_sources")
  HOST_CSV = Rails.root.join("db/record/attachedfile.csv")
  HOST_DOCS = Rails.root.join("db/documents")
  STATE_DOCS = Rails.root.join("../data/state/IATF_documents")
  STATUS_PATH = SOURCE_DIR.join("seed_sync_status.json")
  BACKUP_DIR = Rails.root.join("../backups/supplier_seed")

  FILES = [
    {
      filename: "供給者リスト.xlsx",
      documentcategory: "供給者リスト",
      documentnumber: "SUPPLIER-20260329-001"
    },
    {
      filename: "2025●供給者管理計画／実績表(KGM017).xlsx",
      documentcategory: "供給者管理計画実績",
      documentnumber: "SUPPLIER-20260329-002"
    },
    {
      filename: "●供給者評価表・供給者再評価記録台帳2025.xls",
      documentcategory: "供給者評価再評価台帳",
      documentnumber: "SUPPLIER-20260329-003"
    }
  ].freeze

  HEADERS = %w[
    filename
    category
    partnumber
    materialcode
    phase
    stage
    description
    status
    documenttype
    documentname
    documentrev
    documentcategory
    documentnumber
    start_time
    deadline_at
    end_at
    goal_attainment_level
    tasseido
    object
  ].freeze

  class << self
    def call
      new.call
    end
  end

  def call
    rows = build_rows
    appended = upsert_rows(rows)
    copied = copy_documents(rows)
    status = {
      source_dir: SOURCE_DIR.to_s,
      synced_at: Time.zone.now.iso8601,
      row_count: rows.length,
      appended_count: appended.length,
      copied_count: copied.length,
      files: rows.map { |row| row.slice("filename", "documentcategory", "documentnumber") }
    }
    STATUS_PATH.write(JSON.pretty_generate(status))
    status
  end

  private

  def build_rows
    FILES.map do |config|
      path = SOURCE_DIR.join(config.fetch(:filename))
      raise "Supplier source not found: #{path}" unless File.exist?(path)

      timestamp = File.mtime(path).strftime("%Y-%m-%d %H:%M:%S")
      {
        "filename" => path.basename.to_s,
        "category" => "2",
        "partnumber" => "",
        "materialcode" => "",
        "phase" => "",
        "stage" => "",
        "description" => "供給者データ seed asset",
        "status" => "完了",
        "documenttype" => path.extname.delete(".").downcase,
        "documentname" => path.basename(path.extname).to_s,
        "documentrev" => "",
        "documentcategory" => config.fetch(:documentcategory),
        "documentnumber" => config.fetch(:documentnumber),
        "start_time" => timestamp,
        "deadline_at" => timestamp,
        "end_at" => timestamp,
        "goal_attainment_level" => "100",
        "tasseido" => "100",
        "object" => "object1",
        "_source_path" => path.to_s
      }
    end
  end

  # attachedfile.csv has legacy rows that are not always strict CSV-safe.
  # Keep existing content as-is and only replace the known supplier seed rows.
  def upsert_rows(rows)
    backup_csv
    FileUtils.mkdir_p(HOST_CSV.dirname)

    header_line, body_lines = read_csv_lines
    supplier_filenames = rows.map { |row| row.fetch("filename") }.to_set
    filtered_lines = body_lines.reject { |line| supplier_seed_line?(line, supplier_filenames) }
    new_lines = rows.map { |row| serialize_row(row) }

    File.open(HOST_CSV, "wb") do |handle|
      handle.write("\uFEFF")
      handle.write(header_line)
      handle.write("\n")
      (filtered_lines + new_lines).each do |line|
        handle.write(line)
        handle.write("\n")
      end
    end

    rows.map { |row| row["filename"] }
  end

  def read_csv_lines
    return [CSV.generate_line(HEADERS).strip, []] unless File.exist?(HOST_CSV)

    text = File.binread(HOST_CSV).force_encoding("UTF-8")
    text = text.delete_prefix("\uFEFF").gsub("\r\n", "\n").gsub("\r", "\n")
    lines = text.lines(chomp: true)
    header_line = lines.shift.presence || CSV.generate_line(HEADERS).strip
    [header_line, lines]
  end

  def supplier_seed_line?(line, supplier_filenames)
    return false if line.blank?

    fields = CSV.parse_line(line)
    return false unless fields && fields.length >= 2

    supplier_filenames.include?(fields[0].to_s) && fields[1].to_s == "2"
  rescue CSV::MalformedCSVError
    false
  end

  def serialize_row(row)
    CSV.generate_line(HEADERS.map { |header| row[header].to_s }).strip
  end

  def copy_documents(rows)
    FileUtils.mkdir_p(HOST_DOCS)
    FileUtils.mkdir_p(STATE_DOCS)
    copied = []
    rows.each do |row|
      source_path = Pathname.new(row.fetch("_source_path"))
      [HOST_DOCS, STATE_DOCS].each do |target_dir|
        FileUtils.cp(source_path, target_dir.join(source_path.basename))
      end
      copied << source_path.basename.to_s
    end
    copied
  end

  def backup_csv
    return unless File.exist?(HOST_CSV)

    FileUtils.mkdir_p(BACKUP_DIR)
    stamp = Time.zone.now.strftime("%Y%m%d_%H%M%S")
    FileUtils.cp(HOST_CSV, BACKUP_DIR.join("attachedfile_#{stamp}.csv"))
  end
end
