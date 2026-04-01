# frozen_string_literal: true

class AuditFollowupStatusService
  include ExcelDateParser

  DOC_DIR = "/myapp/db/documents"
  JQA_JSON_PATH = Rails.root.join("db/jqa_audit_reports.json")

  class << self
    def call
      new.call
    end
  end

  def call
    audit_corrections = summarize_entries(audit_correction_entries)
    audit_opportunities = summarize_entries(audit_opportunity_entries)
    nonconformities = summarize_entries(nonconformity_entries)

    {
      generated_at: Time.zone.now,
      audit_corrections: audit_corrections,
      audit_opportunities: audit_opportunities,
      nonconformities: nonconformities,
      jqa_yearly_matrix: build_jqa_yearly_matrix(audit_corrections[:entries], audit_opportunities[:entries], nonconformities[:entries])
    }
  end

  private

  def summarize_entries(entries)
    counts = Hash.new(0)
    entries.each { |entry| counts[entry[:status]] += 1 }

    {
      entries: entries.sort_by { |entry| [status_order(entry[:status]), stringify_date(entry[:due_date]) || "9999-12-31", entry[:file_name].to_s] },
      total: entries.length,
      counts: counts
    }
  end

  def status_order(status)
    { overdue: 0, pending: 1, in_progress: 2, complete: 3, needs_review: 4 }.fetch(status, 9)
  end

  def audit_correction_entries
    Dir.glob(File.join(DOC_DIR, "*内部監査是正処置報告書*.{xlsx,xls}")).filter_map do |file|
      ws = open_workbook(file).sheet("システム読込用フォーム")
      next unless ws

      due_date = parse_date(ws.cell(10, "Q"))
      corrective_date = parse_date(ws.cell(31, "Q"))
      confirm_date = parse_date(ws.cell(37, "Q"))
      corrective_action = ws.cell(31, "B").to_s.strip
      implementation = ws.cell(18, "B").to_s.strip
      leader_confirmation = ws.cell(39, "Q").to_s.strip

      {
        file_name: File.basename(file),
        category: "内部監査是正処置報告書",
        issue_no: ws.cell(1, "C").to_s.strip,
        process_name: ws.cell(6, "C").to_s.strip,
        finding: ws.cell(10, "B").to_s.strip,
        clause: ws.cell(11, "D").to_s.strip,
        due_date: due_date,
        completed_on: confirm_date.presence || corrective_date.presence,
        status: determine_status(
          due_date: due_date,
          completed_on: confirm_date.presence || corrective_date.presence,
          progress_markers: [corrective_action, implementation, leader_confirmation]
        ),
        evidence_note: [ws.cell(31, "P"), ws.cell(37, "P")].map(&:to_s).reject(&:blank?).join(" / ")
      }
    rescue StandardError => e
      {
        file_name: File.basename(file),
        category: "内部監査是正処置報告書",
        process_name: "",
        finding: "読込エラー: #{e.message}",
        clause: "",
        due_date: nil,
        completed_on: nil,
        status: :needs_review,
        evidence_note: ""
      }
    end
  end

  def audit_opportunity_entries
    Dir.glob(File.join(DOC_DIR, "*内部監査改善の機会一覧表*.{xlsx,xls}")).flat_map do |file|
      workbook = open_workbook(file)
      sheet_name = workbook.sheets.find { |name| name.include?("改善の機会") }
      next [] unless sheet_name

      ws = workbook.sheet(sheet_name)
      audit_types, audit_target = audit_info(ws)
      (12..31).filter_map do |row_index|
        opportunity = ws.cell(row_index, "B").to_s.strip
        action = ws.cell(row_index, "K").to_s.strip
        due_date = parse_date(ws.cell(row_index, "M"))
        completed_on = parse_date(ws.cell(row_index, "O"))
        next if [opportunity, action, due_date, completed_on].all?(&:blank?)

        {
          file_name: File.basename(file),
          category: "内部監査改善の機会一覧表",
          issue_no: "",
          process_name: audit_target,
          finding: opportunity,
          clause: audit_types,
          due_date: due_date,
          completed_on: completed_on,
          status: determine_status(
            due_date: due_date,
            completed_on: completed_on,
            progress_markers: [action, ws.cell(5, "O"), ws.cell(6, "I")]
          ),
          evidence_note: action
        }
      end
    rescue StandardError => e
      [{
        file_name: File.basename(file),
        category: "内部監査改善の機会一覧表",
        process_name: "",
        finding: "読込エラー: #{e.message}",
        clause: "",
        due_date: nil,
        completed_on: nil,
        status: :needs_review,
        evidence_note: ""
      }]
    end
  end

  def nonconformity_entries
    patterns = %w[*工程内不適合管理票*.xlsx *工程内不適合品管理票*.xlsx *不適合品管理票*.xlsx *不適合管理票*.xlsx *是正・予防処置管理票*.xlsx
                  *工程内不適合管理票*.xls *工程内不適合品管理票*.xls *不適合品管理票*.xls *不適合管理票*.xls *是正・予防処置管理票*.xls]
    files = patterns.flat_map { |pattern| Dir.glob(File.join(DOC_DIR, pattern)) }.uniq

    files.filter_map do |file|
      workbook = open_workbook(file)
      sheet_name = workbook.sheets.find { |name| name.include?("是正・予防処置管理票") }
      next unless sheet_name

      ws = workbook.sheet(sheet_name)
      due_dates = [parse_date(ws.cell(61, "J")), parse_date(ws.cell(76, "J")), parse_date(ws.cell(88, "F"))].compact
      actual_dates = [parse_date(ws.cell(62, "J")), parse_date(ws.cell(77, "J")), parse_date(ws.cell(88, "J")), parse_date(ws.cell(92, "J")), parse_date(ws.cell(96, "I"))].compact
      finding = section_content(ws, "不適合内容", "顧客在庫への影響")
      process_name = ws.cell(6, "C").to_s.strip

      {
        file_name: File.basename(file),
        category: "是正・予防処置管理票",
        issue_no: ws.cell(2, "K").to_s.strip,
        process_name: process_name,
        finding: finding.presence || ws.cell(4, "C").to_s.strip,
        clause: ws.cell(8, "G").to_s.strip,
        due_date: due_dates.min,
        completed_on: actual_dates.max,
        status: determine_nonconformity_status(due_dates: due_dates, actual_dates: actual_dates, ws: ws),
        evidence_note: [section_content(ws, "発生対策", "流出原因"), section_content(ws, "流出対策", "他の製品及びプロセスへの影響の有無")].reject(&:blank?).join(" / ")
      }
    rescue StandardError => e
      {
        file_name: File.basename(file),
        category: "是正・予防処置管理票",
        process_name: "",
        finding: "読込エラー: #{e.message}",
        clause: "",
        due_date: nil,
        completed_on: nil,
        status: :needs_review,
        evidence_note: ""
      }
    end
  end

  def determine_status(due_date:, completed_on:, progress_markers:)
    return :complete if completed_on.present?
    return :overdue if due_date.is_a?(Date) && due_date < Time.zone.today
    return :in_progress if progress_markers.any?(&:present?)

    :pending
  end

  def determine_nonconformity_status(due_dates:, actual_dates:, ws:)
    return :complete if actual_dates.any? && ws.cell(95, "O").present?
    return :overdue if due_dates.any? { |date| date.is_a?(Date) && date < Time.zone.today } && actual_dates.empty?
    return :in_progress if actual_dates.any? || section_content(ws, "原因と対策", "発生対策", column: "D").present?

    :pending
  end

  def open_workbook(file)
    File.extname(file) == ".xlsx" ? Roo::Excelx.new(file) : Roo::Excel.new(file)
  end

  def audit_info(worksheet)
    types = []
    target = ""
    (5..7).each do |row|
      if worksheet.cell(row, "C") == "☑"
        types << worksheet.cell(row, "A")
        target = worksheet.cell(row, "D")
      end
    end
    [types.join(", "), target.to_s.presence || "データなし"]
  end

  def section_content(worksheet, start_text, end_text, column: "B")
    content = []
    start_row = nil

    (1..worksheet.last_row).each do |row|
      value = worksheet.cell(row, "B")
      next unless value.present?
      if value.to_s.strip.include?(start_text)
        start_row = row + 1
        break
      end
    end
    return "" unless start_row

    (start_row..worksheet.last_row).each do |row|
      marker = worksheet.cell(row, "B")
      break if marker.present? && end_text.present? && marker.to_s.strip.include?(end_text)

      value = worksheet.cell(row, column)
      content << value if value.present?
    end

    content.join("\n").strip
  end

  def stringify_date(value)
    value.respond_to?(:strftime) ? value.strftime("%Y-%m-%d") : nil
  end

  def build_jqa_yearly_matrix(*sections)
    return [] unless File.exist?(JQA_JSON_PATH)

    jqa_payload = JSON.parse(File.read(JQA_JSON_PATH, encoding: "utf-8"))
    evidence_entries = sections.flatten

    jqa_payload.fetch("years", []).map do |year_bucket|
      process_rows = year_bucket.fetch("process_counts", {}).map do |process_name, finding_count|
        normalized_target = normalize_process_name(process_name)
        matching = evidence_entries.select do |entry|
          entry_year = [entry[:due_date], entry[:completed_on]].find { |value| value.respond_to?(:year) }&.year
          entry_year == year_bucket.fetch("year") && normalize_process_name(entry[:process_name]) == normalized_target
        end

        {
          process_name: process_name,
          finding_count: finding_count,
          audit_correction_count: matching.count { |entry| entry[:category] == "内部監査是正処置報告書" },
          opportunity_count: matching.count { |entry| entry[:category] == "内部監査改善の機会一覧表" },
          nonconformity_count: matching.count { |entry| entry[:category] == "是正・予防処置管理票" },
          complete_count: matching.count { |entry| entry[:status] == :complete },
          overdue_count: matching.count { |entry| entry[:status] == :overdue }
        }
      end.sort_by { |row| [-row[:finding_count].to_i, row[:process_name].to_s] }

      {
        year: year_bucket.fetch("year"),
        finding_count: year_bucket.fetch("finding_count"),
        process_rows: process_rows
      }
    end.sort_by { |item| -item[:year].to_i }
  rescue StandardError
    []
  end

  def normalize_process_name(value)
    value.to_s.gsub(/[[:space:]　]/, "").tr("（）", "()")
  end
end
