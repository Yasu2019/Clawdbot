# frozen_string_literal: true

require "json"
require "roo"

class SupplierWorkbookExportService
  TARGETS = {
    management_plan: {
      source_name: "2025●供給者管理計画／実績表(KGM017).xlsx",
      output_name: "supplier_management_plan_2025.json",
      title: "2025供給者管理計画／実績表"
    },
    evaluation: {
      source_name: "●供給者評価表・供給者再評価記録台帳2025.xls",
      output_name: "supplier_evaluation_2025.json",
      title: "2025供給者評価表・供給者再評価記録台帳"
    }
  }.freeze

  class << self
    def export!(dataset:, source_path:, output_dir:)
      config = TARGETS.fetch(dataset.to_sym)
      workbook = Roo::Spreadsheet.open(source_path.to_s)
      sheets = workbook.sheets.map do |sheet_name|
        sheet = workbook.sheet(sheet_name)
        rows = trim_table(
          (1..sheet.last_row.to_i).map do |row_index|
            values = sheet.row(row_index)
            values.map { |value| normalize_value(value) }
          end
        )

        {
          "name" => sheet_name.to_s.strip,
          "row_count" => rows.length,
          "column_count" => rows.map(&:length).max || 0,
          "rows" => rows
        }
      end

      payload = {
        "title" => config[:title],
        "source_name" => config[:source_name],
        "exported_at" => Time.zone.now.iso8601,
        "sheet_count" => sheets.length,
        "sheets" => sheets
      }
      payload["summary"] = dataset.to_sym == :evaluation ? summarize_evaluation(payload) : summarize_management_plan(payload)

      output_path = output_dir.join(config[:output_name])
      output_path.write(JSON.pretty_generate(payload))
      output_path
    end

    private

    def normalize_value(value)
      return "" if value.nil?
      return value.strftime("%Y-%m-%d") if value.respond_to?(:strftime)

      text = value.is_a?(Float) && value.to_i == value ? value.to_i : value
      text.to_s.tr("\u3000", " ").strip
    end

    def trim_table(rows)
      rows = rows.dup
      rows.pop while rows.last&.all?(&:blank?)
      max_len = rows.map { |row| row.rindex { |cell| cell.present? }.to_i + 1 }.max.to_i
      return [] if max_len.zero?

      rows.map { |row| row.first(max_len) }
    end

    def summarize_management_plan(payload)
      action_totals = {
        "評価" => blank_action_totals,
        "QMS開発" => blank_action_totals,
        "監査" => blank_action_totals,
        "供給者開発" => blank_action_totals
      }
      suppliers = []

      payload.fetch("sheets").each do |sheet|
        rows = sheet.fetch("rows")
        next if rows.length < 18

        timeline = rows[9]&.drop(10) || []
        row_index = 10
        while row_index + 7 < rows.length
          lead = rows[row_index]
          if lead[0].blank? && lead[1].blank?
            row_index += 1
            next
          end

          supplier_name = lead[1].to_s.strip
          if supplier_name.blank?
            row_index += 8
            next
          end

          supplier_summary = {
            "sheet" => sheet.fetch("name"),
            "no" => lead[0],
            "supplier_name" => supplier_name,
            "status_mark" => lead[4],
            "actions" => []
          }

          [
            ["評価", rows[row_index], rows[row_index + 1]],
            ["QMS開発", rows[row_index + 2], rows[row_index + 3]],
            ["監査", rows[row_index + 4], rows[row_index + 5]],
            ["供給者開発", rows[row_index + 6], rows[row_index + 7]]
          ].each do |action_name, plan_row, actual_row|
            plan_cells = plan_row.drop(10)
            actual_cells = actual_row.drop(10)
            planned_labels = extract_timeline_labels(timeline, plan_cells)
            actual_labels = extract_timeline_labels(timeline, actual_cells)
            planned_count = planned_labels.length
            actual_count = actual_labels.length

            action_totals[action_name]["planned"] += planned_count
            action_totals[action_name]["actual"] += actual_count
            if planned_count.positive? && actual_count >= planned_count
              action_totals[action_name]["complete"] += 1
            elsif planned_count.positive?
              action_totals[action_name]["pending"] += 1
            end

            supplier_summary["actions"] << {
              "name" => action_name,
              "planned_count" => planned_count,
              "actual_count" => actual_count,
              "planned_labels" => planned_labels,
              "actual_labels" => actual_labels,
              "complete" => planned_count.positive? && actual_count >= planned_count
            }
          end

          suppliers << supplier_summary
          row_index += 8
        end
      end

      {
        "total_suppliers" => suppliers.length,
        "action_totals" => action_totals,
        "suppliers" => suppliers
      }
    end

    def summarize_evaluation(payload)
      sheet = payload.fetch("sheets").find { |entry| entry.fetch("name") == "評価票Ⅱ供給者" } || payload.fetch("sheets").first
      entries = []
      rank_counts = Hash.new(0)
      planned = 0
      executed = 0
      pending = 0

      sheet.fetch("rows").drop(8).each do |row|
        supplier_name = row[0].to_s.strip
        method = row[3].to_s.strip
        next if supplier_name.blank? || method.blank?

        plan_month = row[1]
        actual_date = row[2]
        evaluation_result = row[5].to_s.strip
        planned += 1 if plan_month.present?
        executed += 1 if actual_date.present?
        pending += 1 if plan_month.present? && actual_date.blank?
        rank_counts[evaluation_result] += 1 if evaluation_result.present?

        entries << {
          "supplier_name" => supplier_name,
          "plan_month" => plan_month,
          "actual_date" => actual_date,
          "method" => method,
          "complaint_count" => row[4],
          "evaluation_result" => evaluation_result,
          "iso_status" => row[10],
          "continue_trade" => row[11],
          "stop_trade" => row[12]
        }
      end

      {
        "sheet_name" => sheet.fetch("name"),
        "total_rows" => entries.length,
        "planned_count" => planned,
        "executed_count" => executed,
        "pending_count" => pending,
        "rank_counts" => rank_counts,
        "entries" => entries
      }
    end

    def extract_timeline_labels(timeline, cells)
      cells.each_with_index.filter_map do |cell, index|
        next if cell.blank? || timeline[index].blank?

        timeline[index].to_s.strip
      end
    end

    def blank_action_totals
      { "planned" => 0, "actual" => 0, "complete" => 0, "pending" => 0 }
    end
  end
end
