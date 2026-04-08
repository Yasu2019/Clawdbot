# frozen_string_literal: true

require 'json'
require 'open3'
require 'time'
require 'roo'
require 'roo-xls'
require 'spreadsheet'

class ProcessMonitoringMeasurementRefreshService
  DATA_PATH = Rails.root.join('db', 'process_monitoring_measurement.json')
  DEFAULT_SOURCE_DIR = ENV.fetch('PMM_SOURCE_DIR', '/paperless_consume')
  PDFTEXT_CMD = ['pdftotext', '-layout', '-enc', 'UTF-8'].freeze
  PROCESS_NAMES = ProcessMonitoringMeasurementService::PROCESS_NAMES.freeze

  def self.call(year: nil)
    new(year: year).call
  end

  def initialize(year:)
    @requested_year = year.to_i if year.present?
  end

  def call
    return failure('PDF source directory was not found.') unless source_dir.exist?

    payload = load_payload
    years = target_years
    refreshed = []
    skipped = []

    years.each do |year|
      result = refresh_year(payload, year)
      refreshed << year if result[:updated]
      skipped.concat(result[:skipped_files])
    end

    payload['generated_at'] = Time.current.iso8601
    payload['source_dir'] = source_dir.to_s
    DATA_PATH.write(JSON.pretty_generate(payload))

    {
      success: true,
      updated_years: refreshed,
      skipped_files: skipped,
      generated_at: payload['generated_at']
    }
  rescue StandardError => e
    failure(e.message)
  end

  private

  attr_reader :requested_year

  def failure(message)
    { success: false, error: message, updated_years: [], skipped_files: [] }
  end

  def source_dir
    @source_dir ||= Pathname.new(DEFAULT_SOURCE_DIR)
  end

  def load_payload
    return {} unless DATA_PATH.exist?

    JSON.parse(DATA_PATH.read)
  rescue JSON::ParserError
    {}
  end

  def target_years
    return [requested_year] if requested_year.present? && requested_year >= 2025

    source_dir.children.select(&:directory?).map { |item| item.basename.to_s.to_i }.select { |year| year >= 2025 }.sort
  end

  def refresh_year(payload, year)
    # Excel (.xls) ファイルが優先的に存在するかチェック
    excel_path = Rails.root.join('db', 'documents', "プロセスの監視・測定記録_#{year}年.xls")

    if excel_path.exist?
      payload["year_#{year}"] = extract_excel_grid(excel_path, year)
      { updated: true, skipped_files: [] }
    else
      existing_by_month = Array(payload["year_#{year}"]).index_by { |item| item['month'].to_i }
      refreshed_by_month = {}
      skipped_files = []
      refresh_from_pdfs(year, refreshed_by_month, skipped_files)
      payload["year_#{year}"] = existing_by_month.merge(refreshed_by_month).values.sort_by { |item| item['month'].to_i }
      { updated: refreshed_by_month.any?, skipped_files: skipped_files }
    end
  end

  def refresh_from_excel(excel_path, year, refreshed_by_month)
    items = extract_excel_year_items(excel_path, year)
    items.each { |item| refreshed_by_month[item['month'].to_i] = item }
  end

  def refresh_from_pdfs(year, refreshed_by_month, skipped_files)
    year_dir = source_dir.join(year.to_s)
    return unless year_dir.exist?

    pdf_files = year_dir.children.select { |item| item.file? && item.extname.downcase == '.pdf' }
    pdf_files.sort_by { |item| detect_month(item.basename.to_s) || 99 }.each do |pdf_path|
      item = extract_pdf_item(pdf_path, year)
      if item[:entries].size < 10
        skipped_files << { source_file: pdf_path.basename.to_s, reason: "too_few_entries:#{item[:entries].size}" }
        next
      end

      refreshed_by_month[item[:month].to_i] = item
    end
  end

  def extract_pdf_item(pdf_path, default_year)
    full_text = extract_pdf_text(pdf_path)
    lines = full_text.lines.map { |line| line.to_s.tr("\u3000", ' ').rstrip }
    month = detect_month(pdf_path.basename.to_s) || detect_month(full_text)
    created_date = full_text[/作成日\s*[:：]\s*(\d{4}年\d{1,2}月\d{1,2}日)/, 1].to_s

    {
      'source_file' => pdf_path.basename.to_s,
      'year' => default_year,
      'month' => month,
      'created_date' => created_date,
      'entries' => parse_entries(lines),
      'observations' => extract_section(full_text, 'Ⅲ', 'Ⅳ'),
      'next_actions' => extract_section(full_text, 'Ⅳ', 'Ⅴ'),
      'adjustments' => extract_section(full_text, 'Ⅴ', nil),
      'raw_preview' => full_text[0, 2000]
    }
  end

  def extract_excel_grid(excel_path, year)
    # Switch to using Spreadsheet gem for better .xls fidelity
    book = Spreadsheet.open(excel_path.to_s)
    sheet = book.worksheet(0)

    # Get merged cells directly from the sheet
    # spreadsheet's merged_cells is an array of [r_from, r_to, c_from, c_to]
    merges = sheet.merged_cells

    max_row = 150 # Increased to capture full footer contents
    max_col = 25

    rows_data = (0...max_row).filter_map do |r|
      row_obj = sheet.row(r)
      # Skip rows that are explicitly hidden
      next if row_obj.hidden

      cells = (0...max_col).filter_map do |c|
        # Skip hidden columns
        next if sheet.column(c).hidden

        # Skip inner parts of merged cells (only process top-left)
        next if merged_inner_cell?(merges, r, c)

        val = row_obj[c]
        merge = find_merge(merges, r, c)

        {
          'col' => c + 1,
          'value' => format_excel_value(val),
          'rowspan' => merge ? (merge[1] - merge[0] + 1) : 1,
          'colspan' => merge ? (merge[3] - merge[2] + 1) : 1
        }
      end

      # Skip completely empty rows at the end to save space
      next if cells.all? { |c| c['value'].blank? }

      { 'row' => r + 1, 'cells' => cells }
    end

    {
      'source_file' => excel_path.basename.to_s,
      'sheet_name' => "プロセスの監視・測定記録 (#{year}年)",
      'max_row' => max_row,
      'max_col' => max_col,
      'rows' => rows_data
    }
  end

  def merged_inner_cell?(merges, r, c)
    merges.any? { |m| r >= m[0] && r <= m[1] && c >= m[2] && c <= m[3] && !(r == m[0] && c == m[2]) }
  end

  def find_merge(merges, r, c)
    merges.find { |m| m[0] == r && m[2] == c }
  end

  def format_excel_value(val)
    case val
    when Float
      (val % 1).zero? ? val.to_i.to_s : val.to_s
    when Spreadsheet::Link
      val.to_s.strip
    else
      # Remove non-printable characters and excess spaces that cause "extra characters" in UI
      val.to_s.gsub(/[[:cntrl:]]/, '').gsub(/[[:space:]]+/, ' ').strip
    end
  end

  def extract_excel_entries(sheet, data_col)
    entries = []
    current_process = nil

    # メトリクスのマッピング（2024年のレイアウトに合わせるため、主要な行をスキャン）
    # PDFパースと同様にプロセス名とメトリクス名を検索
    (9..150).each do |row_idx|
      process_val = sheet.cell(row_idx, 2).to_s.strip
      current_process = process_val if process_val.present? && PROCESS_NAMES.any? { |pn| process_val.include?(pn.delete('プロセス')) }

      metric_val = sheet.cell(row_idx, 4).to_s.strip
      next if metric_val.blank? || metric_val.include?('目標業務')

      target_val = sheet.cell(row_idx, 5).to_s.strip
      actual_val = sheet.cell(row_idx, data_col).to_s.strip
      # 累積値があれば結合する（PDFパース互換性のため「当月...累計...」形式にする）
      cumulative_val = sheet.cell(row_idx + 1, data_col).to_s.strip if sheet.cell(row_idx + 1, 9).to_s.include?('累積') || sheet.cell(row_idx + 1, 9).to_s.include?('実績')

      formatted_actual = "当月#{actual_val} 累計#{cumulative_val.presence || actual_val}"

      entries << {
        'process' => current_process.to_s,
        'metric' => metric_val,
        'target' => target_val,
        'actual' => formatted_actual
      }
    end
    entries
  end

  def extract_pdf_text(pdf_path)
    stdout, stderr, status = Open3.capture3(*PDFTEXT_CMD, pdf_path.to_s, '-')
    raise "pdftotext failed for #{pdf_path.basename}: #{stderr.presence || 'unknown error'}" unless status.success?

    stdout.to_s.encode('UTF-8', invalid: :replace, undef: :replace, replace: '')
  end

  def parse_entries(lines)
    entries = []
    current_process = nil
    pending_metric = nil
    in_table = false

    lines.each do |raw_line|
      line = raw_line.to_s.strip
      next if line.blank?

      in_table = true if line.include?('目 標 業 務') || line.include?('目標業務')
      next unless in_table
      break if section_boundary?(line)

      process_heading = detect_process_heading(line)
      if process_heading
        current_process = process_heading
        next
      end

      parts = line.split(/\s{2,}/).map(&:strip).reject(&:blank?)
      unless plausible_entry_parts?(parts)
        pending_metric = merge_metric_fragment(pending_metric, line)
        next
      end

      left = parts[0]
      left = "#{pending_metric}#{left}" if pending_metric.present?
      pending_metric = nil

      process_name = detect_process_prefix(left) || current_process
      metric = strip_process_prefix(left, process_name)
      target = parts[1].to_s.strip
      actual = parts[2..].join(' ').strip

      next if metric.blank? || target.blank? || actual.blank?

      entries << {
        'process' => process_name.to_s,
        'metric' => metric,
        'target' => target,
        'actual' => actual
      }
    end

    entries
  end

  def section_boundary?(line)
    line.start_with?('・') || line.match?(/\A[ⅢⅣⅤ]\z/) || line.start_with?('Ⅲ') || line.start_with?('Ⅳ') || line.start_with?('Ⅴ')
  end

  def detect_process_heading(line)
    normalized = line.delete(' ')
    PROCESS_NAMES.find do |name|
      compact = name.delete(' ')
      normalized == compact || normalized == compact.delete('プロセス')
    end
  end

  def detect_process_prefix(text)
    normalized = text.to_s.delete(' ')
    PROCESS_NAMES.find do |name|
      compact = name.delete(' ')
      normalized.start_with?(compact) || normalized.start_with?(compact.delete('プロセス'))
    end
  end

  def strip_process_prefix(text, process_name)
    return text.to_s.strip if process_name.blank?

    value = text.to_s.strip
    [process_name, process_name.delete('プロセス')].uniq.each do |prefix|
      next if prefix.blank?

      candidate = value.sub(/\A#{Regexp.escape(prefix)}\s*/, '').strip
      return candidate if candidate != value
    end
    value
  end

  def plausible_entry_parts?(parts)
    return false if parts.size < 3

    target = parts[1].to_s
    actual = parts[2..].join(' ')
    target_hint = target.match?(/[%％]|件|達成|以下|以上|年|ヶ月|校正|試作/)
    actual_hint = actual.include?('当月') || actual.include?('累計') || actual.include?('累積') || actual.include?('評価') || actual.include?('無し') || actual.match?(/\d/)

    target_hint && actual_hint
  end

  def merge_metric_fragment(pending_metric, line)
    return pending_metric if line.match?(/\A[ⅠⅡⅢⅣⅤ]+\z/)
    return pending_metric if line.length <= 2

    [pending_metric, line].compact.join
  end

  def detect_month(text)
    text.to_s[/(\d{4})年\s*(\d{1,2})月度/, 2]&.to_i
  end

  def extract_section(full_text, start_marker, end_marker)
    start_index = full_text.index(start_marker)
    return '' unless start_index

    from_start = full_text[start_index + start_marker.length..]
    end_index = end_marker.present? ? from_start.index(end_marker) : nil
    section = end_index ? from_start[0...end_index] : from_start

    section.lines.map(&:strip).reject(&:blank?).join("\n").strip
  end
end
