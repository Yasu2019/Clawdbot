# frozen_string_literal: true

class DocumentReconciliationService
  REPORT_PATH = Rails.root.join("db/document_reconciliation_report.json")

  class << self
    def call
      new.call
    end
  end

  def call
    return empty_payload("document_reconciliation_report.json がまだ生成されていません。") unless File.exist?(REPORT_PATH)

    payload = JSON.parse(File.read(REPORT_PATH, encoding: "utf-8"), symbolize_names: true)
    payload[:core_mismatches] ||= []
    payload[:department_mismatches] ||= []
    payload[:summary] ||= {}
    payload
  rescue StandardError => e
    empty_payload("文書照合レポートを読み込めませんでした: #{e.message}")
  end

  private

  def empty_payload(message)
    {
      generated_at: nil,
      source_zip: nil,
      numbering_reference: { status: "unavailable", reason: message },
      source_files: {},
      summary: {
        qm_entry_count: 0,
        record_rule_count: 0,
        department_entry_count: 0,
        core_mismatch_count: 0,
        department_mismatch_count: 0
      },
      core_mismatches: [],
      department_mismatches: [],
      error_message: message
    }
  end
end
