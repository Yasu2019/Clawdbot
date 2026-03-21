# frozen_string_literal: true

# 内部監査改善の機会一覧を Excel に集約するサービス。
# ProductsController#audit_improvement_opportunity から呼び出される。
class AuditImprovementOpportunityService
  include ExcelDateParser

  HEADERS = ['監査種類', '監査対象', '監査チームリーダー', '回答者（プロセスオーナー）', '監査チームリーダー完了確認',
             '記載日（監査チームリーダー記載）', '記載日（回答者記載）', '改善の機会内容', '処置内容',
             '完了予定日', '曜日', '回答者完了確認日', '曜日'].freeze

  FILE_PATTERN = '/myapp/db/documents/*内部監査改善の機会一覧表*.{xlsx,xls}'.freeze

  def self.call
    new.call
  end

  def call
    workbook  = RubyXL::Workbook.new
    worksheet = workbook.worksheets[0]
    worksheet.sheet_name = '内部監査改善の機会一覧'

    HEADERS.each_with_index { |header, index| worksheet.add_cell(0, index, header) }

    row = 1
    Dir.glob(FILE_PATTERN) do |file|
      process_file(file, worksheet, row)
      row = worksheet.sheet_data.size
    end

    workbook.stream.string
  end

  private

  def process_file(file, worksheet, row)
    Rails.logger.info "ファイルの処理を開始します: #{File.basename(file)}"

    source_workbook = open_workbook(file)
    sheet_name = source_workbook.sheets.find { |s| s.include?('改善の機会') }

    unless sheet_name
      Rails.logger.error "「改善の機会」を含むシートが見つかりません: #{File.basename(file)}"
      return
    end

    source_worksheet = source_workbook.sheet(sheet_name)
    audit_types, audit_target = audit_info(source_worksheet)
    start_row = row

    (12..31).each do |r|
      data = row_data(source_worksheet, r, audit_types, audit_target)
      next if data[7..12].all? { |cell| cell.nil? || cell.to_s.strip.empty? }

      data.each_with_index do |value, col_index|
        cell = worksheet.add_cell(row, col_index, value)
        cell.set_number_format('yyyy/mm/dd') if [5, 6, 9, 11].include?(col_index)
      end
      row += 1
    end

    merge_header_cells(worksheet, start_row, row - 1)
  rescue StandardError => e
    Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
    Rails.logger.error "#{e.class.name} - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end

  def open_workbook(file)
    File.extname(file) == '.xlsx' ? Roo::Excelx.new(file) : Roo::Excel.new(file)
  end

  def audit_info(worksheet)
    types  = []
    target = ''
    (5..7).each do |r|
      if worksheet.cell(r, 'C') == '☑'
        types  << worksheet.cell(r, 'A')
        target  = worksheet.cell(r, 'D')
      end
    end
    target = 'データなし' if target.nil? || target.to_s.strip.empty?
    [types.join(', '), target]
  end

  def row_data(worksheet, r, audit_types, audit_target)
    [
      audit_types,
      audit_target,
      worksheet.cell(4, 'I'),
      worksheet.cell(6, 'I'),
      worksheet.cell(5, 'O'),
      parse_date(worksheet.cell(10, 'D')),
      parse_date(worksheet.cell(10, 'L')),
      worksheet.cell(r, 'B'),
      worksheet.cell(r, 'K'),
      parse_date(worksheet.cell(r, 'M')),
      worksheet.cell(r, 'N'),
      parse_date(worksheet.cell(r, 'O')),
      worksheet.cell(r, 'P')
    ]
  end

  def merge_header_cells(worksheet, start_row, end_row)
    return unless start_row < end_row

    (0..6).each { |col| worksheet.merge_cells(start_row, col, end_row, col) }
  end
end
