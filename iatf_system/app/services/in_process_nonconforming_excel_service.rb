# frozen_string_literal: true

# 工程内不適合品管理票・不適合品管理票・是正予防処置管理票を Excel に集約するサービス。
# ProductsController#in_process_nonconforming_product_control_form から呼び出される。
class InProcessNonconformingExcelService
  include ExcelDateParser

  HEADERS = ['発行部門', '品証受付番号', '発行日', '当該部門', '品名/図番', 'ロット№', '数量',
             '不適合の内容・性質', '原因（発生及び流出）', '処置日', '不適合品の処置', '処置者',
             '是正処置の必要性', '主管部門', '関連部門'].freeze

  HEADERS_CORRECTIVE = ['管理No.', '件名', '発行日', '起票者', '品番又はプロセス', '発生場所', '発生日', '責任部門',
                        '他部門要請', '不適合内容', '発生履歴', '顧客への影響', '現品処置', '処置結果', '実施日', '承認',
                        '担当', '在庫品の処置', '処置結果', '事実の把握', '5M1Eの変更点・変化点', '発生原因', '発生対策',
                        '予定日', '実施日', '実施者', '流出原因', '流出対策', '他の製品及びプロセスへの影響の有無', '予定日',
                        '実施日', '実施者', '効果の確認', '確認日', '承認', '担当', '歯止め', '予定日', '実施日', '実施者',
                        '水平展開', '水平展開（予防）の必要性', '実施日', '実施者', '処置活動のレビュー', 'レビュー日', '承認'].freeze

  FILE_GLOB = '/myapp/db/documents/*{工程内不適合管理票,工程内不適合品管理票,不適合品管理票,不適合管理票,是正・予防処置管理票}*.{xlsx,xls}'.freeze

  def self.call
    new.call
  end

  def call
    workbook   = RubyXL::Workbook.new
    worksheet1 = workbook.worksheets[0]
    worksheet1.sheet_name = '工程内不適合品管理票'
    worksheet2 = workbook.add_worksheet('不適合品管理票')
    worksheet3 = workbook.add_worksheet('是正・予防処置管理票')

    [worksheet1, worksheet2].each do |sheet|
      HEADERS.each_with_index { |h, i| sheet.add_cell(0, i, h) }
    end
    HEADERS_CORRECTIVE.each_with_index { |h, i| worksheet3.add_cell(0, i, h) }

    row1 = row2 = row3 = 1

    Dir.glob(FILE_GLOB) do |file|
      source = open_workbook(file)

      sheet_name = find_sheet(source, ['工程内不適合管理票', '工程内不適合品管理票'])
      if sheet_name
        row1 = process_sheet1(source.sheet(sheet_name), worksheet1, row1)
      end

      sheet_name = find_sheet(source, ['不適合品管理票', '不適合管理票'])
      if sheet_name && !sheet_name.include?('工程内')
        row2 = process_sheet1(source.sheet(sheet_name), worksheet2, row2)
      end

      sheet_name = find_sheet(source, '是正・予防処置管理票')
      if sheet_name
        row3 = process_sheet2(source.sheet(sheet_name), worksheet3, row3)
      else
        Rails.logger.error "シート '是正・予防処置管理票' が見つかりません: #{file}"
      end
    rescue StandardError => e
      Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
      Rails.logger.error "#{e.class.name} - #{e.message}"
      Rails.logger.error e.backtrace.join("\n")
    end

    workbook.stream.string
  end

  private

  def open_workbook(file)
    File.extname(file) == '.xlsx' ? Roo::Excelx.new(file) : Roo::Excel.new(file)
  end

  def find_sheet(workbook, keywords)
    keys = Array(keywords)
    workbook.sheets.find { |name| keys.any? { |k| name.include?(k) } }
  end

  def process_sheet1(source_worksheet, worksheet, row)
    audit_types              = audit_types_from(source_worksheet)
    content_nature, cause    = additional_info_from(source_worksheet)
    data                     = row_data1(source_worksheet, audit_types, content_nature, cause)
    max_widths               = Array.new(data.size, 0)

    [data, row_data1(source_worksheet, audit_types, content_nature, cause)].each_with_index do |d, offset|
      d.each_with_index do |value, col_index|
        cell = worksheet.add_cell(row + offset, col_index, value)
        cell.set_number_format('yyyy/mm/dd') if [2, 9].include?(col_index)
        cell.change_text_wrap(true)          if [7, 8].include?(col_index)
        max_widths[col_index] = [max_widths[col_index], value.to_s.length].max
      end
    end

    worksheet.change_column_width(7, 70)
    worksheet.change_column_width(8, 80)
    (0...max_widths.size).each do |col|
      next if [7, 8].include?(col)
      worksheet.change_column_width(col, 15)
    end

    Rails.logger.info "シートに行を追加しました: #{data.inspect}"
    row + 2
  end

  def process_sheet2(source_worksheet, worksheet, row)
    Rails.logger.info "process_sheet2 開始。現在の行: #{row}"
    data       = row_data2(source_worksheet)
    max_widths = Array.new(data.size, 0)

    data.each_with_index do |value, col_index|
      cell = worksheet.add_cell(row, col_index, value)
      cell.set_number_format('yyyy/mm/dd') if [2, 6, 14, 24, 25, 30, 31, 33, 38, 39, 42].include?(col_index)
      cell.change_text_wrap(true)          if [9, 12, 13, 17, 18, 19, 21, 22, 26, 27, 32, 36, 40, 44].include?(col_index)
      max_widths[col_index] = [max_widths[col_index], value.to_s.length].max
    end

    { 9 => 80, 12 => 80, 13 => 30, 17 => 60, 18 => 30, 19 => 80,
      21 => 80, 22 => 85, 26 => 80, 27 => 85, 36 => 80, 40 => 80 }.each do |col, width|
      worksheet.change_column_width(col, width)
    end
    skip_cols = [9, 12, 13, 17, 18, 19, 21, 22, 26, 27, 36, 40]
    (0...max_widths.size).each do |col|
      worksheet.change_column_width(col, 25) unless skip_cols.include?(col)
    end

    Rails.logger.info "process_sheet2 完了。次の行: #{row + 1}"
    row + 1
  rescue StandardError => e
    Rails.logger.error "process_sheet2 でエラーが発生しました: #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    row
  end

  def audit_types_from(worksheet)
    (20..23).each_with_object([]) do |r, types|
      val = worksheet.cell(r, 'A')
      types << val.to_s.strip[1..] if val.present? && val.to_s.strip.start_with?('□')
    end
  end

  def additional_info_from(worksheet)
    content_nature = []
    cause          = []
    section        = nil

    (1..worksheet.last_row).each do |r|
      val = worksheet.cell(r, 'A')
      next unless val.present?
      val = val.to_s.strip
      if    val.include?('不適合の内容・性質')     then section = :content_nature
      elsif val.include?('原因（発生及び流出）')   then section = :cause
      elsif val.include?('不適合品の処置')         then section = nil
      elsif section == :content_nature && !content_nature.include?(val) then content_nature << val
      elsif section == :cause          && !cause.include?(val)          then cause << val
      end
    end

    [content_nature.join("\n").strip, cause.join("\n").strip]
  end

  def find_value_in_column_e(worksheet, target)
    (1..worksheet.last_row).each do |row|
      val = worksheet.cell(row, 'A')
      return worksheet.cell(row, 'E') if val.present? && val.to_s.strip == target
    end
    nil
  end

  def find_value_in_column_ab(worksheet, target)
    (1..worksheet.last_row).each do |row|
      val = worksheet.cell(row, 'AB')
      return worksheet.cell(row + 1, 'AB') if val.present? && val.to_s.strip == target
    end
    nil
  end

  def find_product_row(worksheet)
    (1..worksheet.last_row).each do |row|
      val = worksheet.cell(row, 'A')
      return row if val.present? && val.to_s.strip == '品名/図番'
    end
    nil
  end

  def nonconforming_disposition(worksheet)
    start_row = nil
    (1..worksheet.last_row).each do |row|
      if worksheet.cell(row, 'A').to_s.strip == '処置日'
        start_row = row
        break
      end
    end
    return '' unless start_row

    ('E'..'K').filter_map do |col|
      header = worksheet.cell(start_row, col)
      value  = worksheet.cell(start_row + 1, col)
      "#{header}: #{value}" if value && !value.to_s.strip.empty?
    end.join(', ')
  end

  def row_data1(worksheet, audit_types, content_nature, cause)
    product_row  = find_product_row(worksheet)
    dept_value   = find_value_in_column_e(worksheet, '当該部門') ||
                   find_value_in_column_e(worksheet, '＊当該部門')

    [
      find_value_in_column_e(worksheet, '発行部門'),
      find_value_in_column_ab(worksheet, '品証受付番号'),
      parse_date(find_value_in_column_e(worksheet, '発行日')),
      dept_value,
      find_value_in_column_e(worksheet, '品名/図番'),
      product_row ? worksheet.cell(product_row, 'P')  : nil,
      product_row ? worksheet.cell(product_row, 'AA') : nil,
      content_nature,
      cause,
      parse_date(worksheet.cell(25, 'A')),
      nonconforming_disposition(worksheet),
      worksheet.cell(24, 'M'),
      worksheet.cell(22, 'E'),
      worksheet.cell(24, 'W'),
      worksheet.cell(25, 'W')
    ]
  end

  def section_content(worksheet, start_text, end_text, column: 'B', min_row: nil, max_rows: nil)
    content    = []
    start_row  = nil
    search_from = min_row || 1

    (search_from..worksheet.last_row).each do |r|
      val = worksheet.cell(r, 'B')
      next unless val.present?
      if val.to_s.strip.include?(start_text)
        start_row = r + 1
        break
      end
    end
    return '' unless start_row

    (start_row..worksheet.last_row).each do |r|
      b_val = worksheet.cell(r, 'B')
      if b_val.present? && end_text && b_val.to_s.strip.include?(end_text)
        break
      end
      val = worksheet.cell(r, column)
      content << val if val.present?
      break if max_rows && (r - start_row >= max_rows)
    end

    content.join("\n").strip
  end

  def row_data2(ws)
    [
      ws.cell(2, 'K'),
      ws.cell(4, 'C'),
      parse_date(ws.cell(5, 'H')),
      ws.cell(5, 'K'),
      ws.cell(6, 'C'),
      ws.cell(6, 'K'),
      parse_date(ws.cell(9, 'C')),
      ws.cell(8, 'G'),
      ws.cell(8, 'N'),
      section_content(ws, '不適合内容', '顧客在庫への影響'),
      ws.cell(10, 'N'),
      ws.cell(18, 'B'),
      section_content(ws, '現品処置', '処置結果'),
      section_content(ws, '処置結果', '在庫品の処置'),
      parse_date(ws.cell(28, 'H')),
      ws.cell(26, 'O'),
      ws.cell(28, 'O'),
      section_content(ws, '在庫品の処置', '処置結果'),
      section_content(ws, '処置結果', '事実の把握', min_row: 31),
      section_content(ws, '事実の把握', '原因と対策'),
      ws.cell(40, 'M'),
      section_content(ws, '原因と対策', '発生対策', column: 'D'),
      section_content(ws, '発生対策', '流出原因'),
      parse_date(ws.cell(61, 'J')),
      parse_date(ws.cell(62, 'J')),
      ws.cell(61, 'O'),
      section_content(ws, '流出原因', '流出対策', column: 'D'),
      section_content(ws, '流出対策', '他の製品及びプロセスへの影響の有無'),
      ws.cell(77, 'F'),
      parse_date(ws.cell(76, 'J')),
      parse_date(ws.cell(77, 'J')),
      ws.cell(77, 'O'),
      section_content(ws, '効果の確認', '歯止め'),
      parse_date(ws.cell(83, 'J')),
      ws.cell(81, 'O'),
      ws.cell(82, 'O'),
      section_content(ws, '歯止め', '水平展開'),
      parse_date(ws.cell(88, 'F')),
      parse_date(ws.cell(88, 'J')),
      ws.cell(87, 'O'),
      section_content(ws, '水平展開', '必要性'),
      ws.cell(92, 'E'),
      parse_date(ws.cell(92, 'J')),
      ws.cell(92, 'O'),
      section_content(ws, '処置活動のレビュー', nil, max_rows: 10),
      parse_date(ws.cell(96, 'I')),
      ws.cell(95, 'O')
    ]
  end
end
