# frozen_string_literal: true

# 内部監査是正処置報告書を Excel に集約するサービス。
# ProductsController#audit_correction_report から呼び出される。
class AuditCorrectionReportService
  include ExcelDateParser

  HEADERS = ['発行No.', '承認者', '作成者', '監査タイプ', '対象プロセス', '監査対応者', '監査実施日', '監査チーム',
             '不適合カ区分', '不適合内容', '条項', '不適合の根拠', '不適合の区分の根拠', '是正立案予定日', '監査リーダー',
             'エビデンス（不適合内容）', '修正内容', '封じ込め', '水平展開', 'エビデンス(修正)', '実施', 'プロセスオーナー',
             '発生原因', 'プロセスオーナー', '是正処置', 'エビデンス（是正処置）', '是正実施年月日', 'プロセスオーナー',
             '是正処置の有効性の確認', 'エビデンス', '確認年月日', '監査リーダー確認'].freeze

  FILE_PATTERN = '/myapp/db/documents/*内部監査是正処置報告書*.{xlsx,xls}'.freeze

  def self.call
    new.call
  end

  def call
    workbook  = RubyXL::Workbook.new
    worksheet = workbook.worksheets[0]
    worksheet.sheet_name = 'システム読込用フォーム'

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

    source_workbook  = open_workbook(file)
    source_worksheet = source_workbook.sheet('システム読込用フォーム')

    unless source_worksheet
      Rails.logger.error "「システム読込用フォーム」シートが見つかりません: #{File.basename(file)}"
      return
    end

    data = build_row_data(source_worksheet)
    data.each_with_index do |value, col_index|
      cell = worksheet.add_cell(row, col_index, value)
      cell.set_number_format('yyyy/mm/dd') if [6, 13, 20, 26, 30].include?(col_index)
    end
  rescue StandardError => e
    Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
    Rails.logger.error "#{e.class.name} - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end

  def open_workbook(file)
    File.extname(file) == '.xlsx' ? Roo::Excelx.new(file) : Roo::Excel.new(file)
  end

  def build_row_data(ws)
    [
      ws.cell(1, 'C'),                                                         # 発行No.
      ws.cell(3, 'P'),                                                         # 承認者
      ws.cell(3, 'Q'),                                                         # 作成者
      ws.cell(4, 'D'),                                                         # 監査タイプ
      ws.cell(6, 'C'),                                                         # 対象プロセス
      ws.cell(6, 'P'),                                                         # 監査対応者
      parse_date(ws.cell(7, 'C')),                                             # 監査実施日
      ws.cell(6, 'J'),                                                         # 監査チーム
      ws.cell(8, 'I'),                                                         # 不適合区分
      ws.cell(10, 'B'),                                                        # 不適合内容
      ws.cell(11, 'D'),                                                        # 条項
      ws.cell(13, 'B'),                                                        # 不適合の根拠
      ws.cell(15, 'B'),                                                        # 不適合の区分の根拠
      parse_date(ws.cell(10, 'Q')),                                            # 是正立案予定日
      ws.cell(13, 'Q'),                                                        # 監査リーダー
      ws.cell(10, 'P'),                                                        # エビデンス（不適合内容）
      ws.cell(18, 'B'),                                                        # 修正内容
      ws.cell(20, 'D') == '☑' ? '否' : '要',                                  # 封じ込め
      ws.cell(22, 'D') == '☑' ? '否' : '要',                                  # 水平展開
      ws.cell(18, 'P'),                                                        # エビデンス（修正）
      parse_date(ws.cell(18, 'Q')),                                            # 実施日
      ws.cell(20, 'Q'),                                                        # プロセスオーナー
      (25..29).map.with_index(1) { |r, i|
        v = ws.cell(r, 'C')
        v.present? ? "なぜ#{i}：#{v}" : nil
      }.compact.join("\n"),                                                    # 発生原因
      ws.cell(25, 'Q'),                                                        # プロセスオーナー
      ws.cell(31, 'B'),                                                        # 是正処置
      ws.cell(31, 'P'),                                                        # エビデンス（是正処置）
      parse_date(ws.cell(31, 'Q')),                                            # 是正実施年月日
      ws.cell(33, 'Q'),                                                        # プロセスオーナー
      ws.cell(36, 'B'),                                                        # 是正処置の有効性の確認
      ws.cell(37, 'P'),                                                        # エビデンス（有効性の確認）
      parse_date(ws.cell(37, 'Q')),                                            # 確認年月日
      ws.cell(39, 'Q')                                                         # 監査リーダー確認
    ]
  end
end
