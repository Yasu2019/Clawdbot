# frozen_string_literal: true

module SuppliersHelper
  EXCEL_SERIAL_EPOCH = Date.new(1899, 12, 30)

  def supplier_tabs(active_tab)
    [
      { key: "list", label: "Supplier List", path: index_suppliers_path },
      { key: "management_plan", label: "Management Plan / Actual", path: workbooks_suppliers_path(dataset: "management_plan") },
      { key: "evaluation", label: "Evaluation / Re-evaluation", path: workbooks_suppliers_path(dataset: "evaluation") },
      { key: "uploads", label: "Data Update", path: uploads_suppliers_path }
    ].map do |tab|
      tab.merge(active: tab[:key] == active_tab)
    end
  end

  def supplier_excel_download_path(dataset = nil)
    dataset.present? ? download_excel_suppliers_path(dataset: dataset) : download_excel_suppliers_path
  end

  def supplier_workbook_cell_value(cell, row_index:, column_index:, row:)
    return cell if cell.blank?
    return cell unless supplier_actual_date_cell?(row_index: row_index, column_index: column_index, row: row)

    serial =
      case cell
      when Integer
        cell
      when /\A\d+\z/
        cell.to_i
      else
        nil
      end

    return cell unless serial && serial.between?(30_000, 60_000)

    (EXCEL_SERIAL_EPOCH + serial).strftime("%Y-%m-%d")
  end

  def supplier_layout_segments(row)
    non_blank_indexes = row.each_index.select { |index| row[index].present? }
    return [{ text: "", colspan: row.length }] if non_blank_indexes.empty?

    non_blank_indexes.each_with_index.map do |index, position|
      next_index = non_blank_indexes[position + 1] || row.length
      {
        text: row[index],
        colspan: [next_index - index, 1].max
      }
    end
  end

  private

  def supplier_actual_date_cell?(row_index:, column_index:, row:)
    row_index >= 10 && row[7].to_s.strip == "実績" && column_index.between?(8, 22)
  end
end
