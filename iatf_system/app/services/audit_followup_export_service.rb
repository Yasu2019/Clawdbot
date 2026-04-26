# frozen_string_literal: true

require "caxlsx"

class AuditFollowupExportService
  STATUS_LABELS = {
    complete: "完了",
    overdue: "期限超過",
    in_progress: "対応中",
    pending: "未着手",
    needs_review: "要確認"
  }.freeze

  SECTION_LABELS = {
    audit_corrections: "内部監査是正処置報告書",
    audit_opportunities: "内部監査改善の機会一覧",
    nonconformities: "是正・予防処置管理票"
  }.freeze

  def self.call(payload:, selected_year:)
    new(payload:, selected_year:).call
  end

  def initialize(payload:, selected_year:)
    @payload = payload || {}
    @selected_year = selected_year.presence&.to_i
  end

  def call
    package = Axlsx::Package.new
    workbook = package.workbook

    workbook.add_worksheet(name: "年度別サマリー") do |sheet|
      build_yearly_summary_sheet(sheet)
    end

    workbook.add_worksheet(name: "指摘一覧") do |sheet|
      build_entries_sheet(sheet)
    end

    workbook.add_worksheet(name: "JQA年度別") do |sheet|
      build_jqa_sheet(sheet)
    end

    package.to_stream.read
  end

  private

  attr_reader :payload, :selected_year

  def build_yearly_summary_sheet(sheet)
    sheet.add_row ["対象年度", selected_year || "全年度"]
    sheet.add_row []
    sheet.add_row ["年度", "JQA指摘件数", "是正処置", "改善の機会", "不適合管理", "完了", "期限超過", "対応中", "未着手", "要確認"]

    yearly_summary.each do |row|
      sheet.add_row [
        row[:year],
        row[:jqa_findings],
        row[:audit_corrections],
        row[:audit_opportunities],
        row[:nonconformities],
        row[:complete],
        row[:overdue],
        row[:in_progress],
        row[:pending],
        row[:needs_review]
      ]
    end
  end

  def build_entries_sheet(sheet)
    sheet.add_row ["対象年度", selected_year || "全年度"]
    sheet.add_row []
    sheet.add_row ["区分", "年度", "状態", "ファイル", "指摘No.", "プロセス", "指摘内容", "条項/監査種別", "期限日", "完了日", "証跡/メモ"]

    filtered_sections.each do |key, section|
      section.fetch(:entries, []).each do |entry|
        year = entry_year(entry)
        sheet.add_row [
          SECTION_LABELS.fetch(key),
          year,
          STATUS_LABELS.fetch(entry[:status], entry[:status].to_s),
          entry[:file_name],
          entry[:issue_no],
          entry[:process_name],
          entry[:finding],
          entry[:clause],
          stringify_date(entry[:due_date]),
          stringify_date(entry[:completed_on]),
          entry[:evidence_note]
        ]
      end
    end
  end

  def build_jqa_sheet(sheet)
    sheet.add_row ["対象年度", selected_year || "全年度"]
    sheet.add_row []
    sheet.add_row ["年度", "プロセス", "JQA指摘件数", "是正処置", "改善の機会", "不適合管理", "完了", "期限超過"]

    filtered_jqa_rows.each do |year_row|
      year_row.fetch(:process_rows, []).each do |row|
        sheet.add_row [
          year_row[:year],
          row[:process_name],
          row[:finding_count],
          row[:audit_correction_count],
          row[:opportunity_count],
          row[:nonconformity_count],
          row[:complete_count],
          row[:overdue_count]
        ]
      end
    end
  end

  def yearly_summary
    years = {}

    filtered_sections.each do |section_key, section|
      section.fetch(:entries, []).each do |entry|
        year = entry_year(entry)
        next unless year

        years[year] ||= {
          year: year,
          jqa_findings: jqa_finding_count(year),
          audit_corrections: 0,
          audit_opportunities: 0,
          nonconformities: 0,
          complete: 0,
          overdue: 0,
          in_progress: 0,
          pending: 0,
          needs_review: 0
        }

        bucket = years[year]
        bucket[:audit_corrections] += 1 if section_key == :audit_corrections
        bucket[:audit_opportunities] += 1 if section_key == :audit_opportunities
        bucket[:nonconformities] += 1 if section_key == :nonconformities
        bucket[entry[:status]] += 1 if bucket.key?(entry[:status])
      end
    end

    filtered_jqa_rows.each do |year_row|
      year = year_row[:year].to_i
      years[year] ||= {
        year: year,
        jqa_findings: year_row[:finding_count],
        audit_corrections: 0,
        audit_opportunities: 0,
        nonconformities: 0,
        complete: 0,
        overdue: 0,
        in_progress: 0,
        pending: 0,
        needs_review: 0
      }
    end

    years.values.sort_by { |row| -row[:year].to_i }
  end

  def filtered_sections
    @filtered_sections ||= begin
      {
        audit_corrections: filter_section(payload[:audit_corrections]),
        audit_opportunities: filter_section(payload[:audit_opportunities]),
        nonconformities: filter_section(payload[:nonconformities])
      }
    end
  end

  def filter_section(section)
    section ||= {}
    entries = Array(section[:entries]).select do |entry|
      selected_year.blank? || entry_year(entry) == selected_year
    end
    counts = Hash.new(0)
    entries.each { |entry| counts[entry[:status]] += 1 }
    section.merge(entries: entries, total: entries.length, counts: counts)
  end

  def filtered_jqa_rows
    Array(payload[:jqa_yearly_matrix]).select do |year_row|
      selected_year.blank? || year_row[:year].to_i == selected_year
    end
  end

  def jqa_finding_count(year)
    filtered_jqa_rows.find { |row| row[:year].to_i == year.to_i }&.fetch(:finding_count, 0).to_i
  end

  def entry_year(entry)
    [entry[:due_date], entry[:completed_on]].find { |value| value.respond_to?(:year) }&.year
  end

  def stringify_date(value)
    value.respond_to?(:strftime) ? value.strftime("%Y-%m-%d") : value.to_s
  end
end
