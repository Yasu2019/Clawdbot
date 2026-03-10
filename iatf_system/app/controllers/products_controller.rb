# frozen_string_literal: true

require 'caxlsx'

# 下記Requireがないと、rubyXLが動かない
# revise
require 'roo'
require 'rubyXL/convenience_methods'
require 'rubyXL/convenience_methods/worksheet'
require 'rubyXL/convenience_methods/cell'
require 'csv'
require 'open-uri'
require 'nokogiri'
require 'net/http'
require 'uri'
require 'date'

class ProductsController < ApplicationController
  before_action :set_product, only: %i[show edit update destroy]
  before_action :phase,
                only: %i[apqp_approved_report apqp_plan_report process_design_plan_report graph calendar new edit show index index2
                         index3 index8 index9 download xlsx generate_xlsx]
  # before_action :restrict_ip_address
  before_action :set_q, only: [:index] # これを追加

  # 全てのIPからのアクセスを許可する場合
  # ALLOWED_IPS = ['0.0.0.0/0']

  # ミツイ精密社内IPアドレスのみアクセス許可
  # ALLOWED_IPS = ['192.168.5.0/24', '8.8.8.8']
  # ALLOWED_EMAILS = ['yasuhiro-suzuki@mitsui-s.com', 'n_komiya@mitsui-s.com']

  include ExcelTemplateHelper

  # Railsで既存のエクセルファイルをテンプレートにできる魔法のヘルパー
  # https://qiita.com/m-kubo/items/6b5beaaf2a59c0d75bcc#:~:text=Rails%E3%81%A7%E6%97%A2%E5%AD%98%E3%81%AE%E3%82%A8%E3%82%AF%E3%82%BB%E3%83%AB%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%82%92%E3%83%86%E3%83%B3%E3%83%97%E3%83%AC%E3%83%BC%E3%83%88%E3%81%AB%E3%81%A7%E3%81%8D%E3%82%8B%E9%AD%94%E6%B3%95%E3%81%AE%E3%83%98%E3%83%AB%E3%83%91%E3%83%BC%201%20%E3%81%AF%E3%81%98%E3%82%81%E3%81%AB%20%E4%BB%8A%E5%9B%9E%E3%81%AE%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AF%E3%80%81%E4%BB%A5%E4%B8%8B%E3%81%AE%E7%92%B0%E5%A2%83%E3%81%A7%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E3%81%97%E3%81%A6%E3%81%84%E3%81%BE%E3%81%99%E3%80%82%20...%202%201.%20rubyXL,7%206.%20%E3%81%8A%E3%81%BE%E3%81%91%20...%208%20%E7%B5%82%E3%82%8F%E3%82%8A%E3%81%AB%20%E4%BB%A5%E4%B8%8A%E3%80%81%E3%81%A9%E3%81%93%E3%81%8B%E3%81%AE%E6%A1%88%E4%BB%B6%E3%81%A7%E6%9B%B8%E3%81%84%E3%81%9F%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AE%E7%B4%B9%E4%BB%8B%E3%81%A7%E3%81%97%E3%81%9F%E3%80%82%20

  
  #def audit_correction_report
  #  Rails.logger.info "======================================="
  #  Rails.logger.info "audit_correction_report メソッドが呼び出されました"
  #  Rails.logger.info "======================================="
  
    # 内部監査是正処置報告書を含む製品のみを取得
  #  @products = Product.joins(documents_attachments: :blob)
  #                     .where("active_storage_blobs.filename LIKE ?", "%内部監査是正処置報告書%")
  #                     .distinct
  
   # Rails.logger.info "内部監査是正処置報告書を含む製品数: #{@products.count}"
 # 
  #  @products.each do |pro|
  #    Rails.logger.info "----------------------------------------"
  #    Rails.logger.info "製品ID: #{pro.id}"
  #    Rails.logger.info "パーツナンバー: #{pro.partnumber}"
  #    Rails.logger.info "カテゴリ: #{pro.category}"
  #    Rails.logger.info "ステージ: #{pro.stage}"
  
   #   pro.documents.each do |doc|
   #     if doc.filename.to_s.include?('内部監査是正処置報告書')
   #       Rails.logger.info "  ファイル名: #{doc.filename}"
   #       Rails.logger.info "  コンテンツタイプ: #{doc.content_type}"
   #       Rails.logger.info "  サイズ: #{doc.byte_size} bytes"
   #     end
 #     end
 #   end
  
 #   Rails.logger.info "======================================="
 #   Rails.logger.info "デバッグ情報の出力が完了しました"
 #   Rails.logger.info "======================================="
  
 #   render plain: "デバッグ情報がログに出力されました。log/development.log を確認してください。"
 # end


 require 'date'  # 日付フォーマット用

 def in_process_nonconforming_product_control_form
  Rails.logger.info "in_process_nonconforming_product_control_form メソッドが呼び出されました"

  workbook = RubyXL::Workbook.new

  # ワークシート設定
  worksheet1 = workbook.worksheets[0]
  worksheet1.sheet_name = "工程内不適合品管理票"
  worksheet2 = workbook.add_worksheet("不適合品管理票")
  worksheet3 = workbook.add_worksheet("是正・予防処置管理票")

  # 工程内不適合管理票と不適合品管理票のヘッダー
  #headers = ['発行部門','発行日', '当該部門', '品名/図番', 'ロット№', '数量', '不適合の内容・性質',
  #  '原因（発生及び流出）', '処置日','不適合品の処置', '処置者', '是正処置の必要性', '主管部門', '関連部門']

  headers = ['発行部門', '品証受付番号','発行日', '当該部門', '品名/図番', 'ロット№', '数量', '不適合の内容・性質',
    '原因（発生及び流出）', '処置日','不適合品の処置', '処置者', '是正処置の必要性', '主管部門', '関連部門']
  
  
  # 是正・予防処置管理票のヘッダー
  headers_corrective = ['管理No.', '件名', '発行日', '起票者', '品番又はプロセス', '発生場所', '発生日', '責任部門', '他部門要請',
                       '不適合内容', '発生履歴', '顧客への影響', '現品処置', '処置結果', '実施日', '承認', '担当', '在庫品の処置',
                       '処置結果', '事実の把握', '5M1Eの変更点・変化点', '発生原因', '発生対策', '予定日', '実施日', '実施者',
                       '流出原因', '流出対策', '他の製品及びプロセスへの影響の有無', '予定日', '実施日', '実施者', '効果の確認',
                       '確認日', '承認', '担当', '歯止め', '予定日', '実施日', '実施者', '水平展開', '水平展開（予防）の必要性',
                       '実施日', '実施者', '処置活動のレビュー', 'レビュー日', '承認']

  # ヘッダーの設定
  [worksheet1, worksheet2].each do |sheet|
    headers.each_with_index { |header, index| sheet.add_cell(0, index, header) }
  end

  headers_corrective.each_with_index { |header, index| worksheet3.add_cell(0, index, header) }

  row1 = 1
  row2 = 1
  row3 = 1

  # ファイルの処理
  Dir.glob("/myapp/db/documents/*{工程内不適合管理票,工程内不適合品管理票,不適合品管理票,不適合管理票,是正・予防処置管理票}*.{xlsx,xls}").each do |file|
    begin
      source_workbook = create_workbook(file)

      # 工程内不適合管理票の処理
      sheet_name = find_sheet_by_keyword(source_workbook, ["工程内不適合管理票", "工程内不適合品管理票"])
      if sheet_name
        source_worksheet = source_workbook.sheet(sheet_name)
        row1 = process_sheet1(source_worksheet, worksheet1, row1)
        Rails.logger.info "工程内不適合管理票を処理しました。現在の行: #{row1}"
      end

      # 不適合品管理票の処理
      sheet_name = find_sheet_by_keyword(source_workbook, ["不適合品管理票", "不適合管理票"])
      if sheet_name && !sheet_name.include?("工程内") # "工程内"を含む場合はスキップ
        source_worksheet = source_workbook.sheet(sheet_name)
        row2 = process_sheet1(source_worksheet, worksheet2, row2)
        Rails.logger.info "不適合品管理票を処理しました。現在の行: #{row2}"
      end

      # 是正・予防処置管理票の処理
      sheet_name = find_sheet_by_keyword(source_workbook, "是正・予防処置管理票")
      if sheet_name
        source_worksheet = source_workbook.sheet(sheet_name)
        row3 = process_sheet2(source_worksheet, worksheet3, row3)
        Rails.logger.info "是正・予防処置管理票を処理しました。現在の行: #{row3}"
      else
        Rails.logger.error "シート名 '是正・予防処置管理票' が見つかりませんでした: #{file}"
      end

    rescue => e
      handle_error(e, file)
    end
  end

  excel_data = workbook.stream.string
  send_data excel_data, filename: "品質管理票.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
end












def audit_improvement_opportunity
  Rails.logger.info "audit_improvement_opportunity メソッドが呼び出されました"

  headers = ['監査種類', '監査対象', '監査チームリーダー', '回答者（プロセスオーナー）', '監査チームリーダー完了確認', '記載日（監査チームリーダー記載）', '記載日（回答者記載）',
             '改善の機会内容', '処置内容', '完了予定日', '曜日', '回答者完了確認日', '曜日']

  @products = Product.joins(documents_attachments: :blob)
                     .where("active_storage_blobs.filename LIKE ?", "%内部監査改善の機会一覧表%")
                     .distinct

  Rails.logger.info "内部監査改善の機会一覧表を含む製品数: #{@products.count}"

  workbook = RubyXL::Workbook.new
  worksheet = workbook.worksheets[0]
  worksheet.sheet_name = "内部監査改善の機会一覧"

  headers.each_with_index do |header, index|
    worksheet.add_cell(0, index, header)
  end

  row = 1

  # ファイルを一度だけ検索
  pattern = "/myapp/db/documents/*内部監査改善の機会一覧表*.{xlsx,xls}"
  files = Dir.glob(pattern)
  Rails.logger.info "検出されたファイル数: #{files.count}"

  files.each do |file|
    process_file(file, worksheet, row)
    row = worksheet.sheet_data.size
  end

  Rails.logger.info "======================================="
  Rails.logger.info "デバッグ情報の出力が完了しました"
  Rails.logger.info "======================================="

  excel_data = workbook.stream.string

  send_data excel_data, filename: "audit_improvement_opportunity_list.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
end

def process_file(file, worksheet, row)
  begin
    Rails.logger.info "ファイルの処理を開始します: #{File.basename(file)}"

    source_workbook = if File.extname(file) == '.xlsx'
                        Roo::Excelx.new(file)
                      else
                        Roo::Excel.new(file)
                      end

    source_worksheet = source_workbook.sheets.find { |sheet_name| sheet_name.include?("改善の機会") }
    source_worksheet = source_workbook.sheet(source_worksheet) if source_worksheet

    unless source_worksheet
      Rails.logger.error "「改善の機会」を含むシートが見つかりません: #{File.basename(file)}"
      return
    end

    audit_types, audit_target = get_audit_info(source_worksheet)

    start_row = row

    (12..31).each do |r|
      data = get_row_data(source_worksheet, r, audit_types, audit_target)
      next if data[7..12].all? { |cell| cell.nil? || cell.to_s.strip.empty? }

      data.each_with_index do |value, col_index|
        cell = worksheet.add_cell(row, col_index, value)
        if [5, 6, 9, 11].include?(col_index)  # 日付列のインデックス
          cell.set_number_format('yyyy/mm/dd')
        end
      end

      row += 1
    end

    end_row = row - 1
    merge_cells(worksheet, start_row, end_row)

  rescue => e
    Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
    Rails.logger.error "エラー: #{e.class.name} - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end
end

def get_audit_info(source_worksheet)
  audit_types = []
  audit_target = ""

  (5..7).each do |r|
    if source_worksheet.cell(r, 'C') == '☑'
      audit_types << source_worksheet.cell(r, 'A')
      audit_target = source_worksheet.cell(r, 'D')
    end
  end

  audit_target = 'データなし' if audit_target.nil? || audit_target.to_s.strip.empty?

  [audit_types.join(', '), audit_target]
end

def get_row_data(source_worksheet, r, audit_types, audit_target)
  [
    audit_types,
    audit_target,
    source_worksheet.cell(4, 'I'),
    source_worksheet.cell(6, 'I'),
    source_worksheet.cell(5, 'O'),
    parse_date(source_worksheet.cell(10, 'D')),
    parse_date(source_worksheet.cell(10, 'L')),
    source_worksheet.cell(r, 'B'),
    source_worksheet.cell(r, 'K'),
    parse_date(source_worksheet.cell(r, 'M')),
    source_worksheet.cell(r, 'N'),
    parse_date(source_worksheet.cell(r, 'O')),
    source_worksheet.cell(r, 'P')
  ]
end

def parse_date(cell_value)
  case cell_value
  when Date, Time
    cell_value
  when String
    begin
      Date.parse(cell_value)
    rescue Date::Error
      cell_value
    end
  when Numeric
    begin
      base_date = Date.new(1899, 12, 30)
      base_date + cell_value.to_i
    rescue Date::Error
      cell_value
    end
  else
    cell_value
  end
end

def merge_cells(worksheet, start_row, end_row)
  if start_row < end_row
    (0..6).each do |col|
      worksheet.merge_cells(start_row, col, end_row, col)
    end
  end
end









def audit_correction_report
  Rails.logger.info "audit_correction_report メソッドが呼び出されました"

  headers = ['発行No.', '承認者', '作成者', '監査タイプ', '対象プロセス', '監査対応者', '監査実施日', '監査チーム',
             '不適合カ区分', '不適合内容', '条項','不適合の根拠', '不適合の区分の根拠', '是正立案予定日', '監査リーダー',
             'エビデンス（不適合内容）', '修正内容', '封じ込め', '水平展開', 'エビデンス(修正)','実施','プロセスオーナー','発生原因','プロセスオーナー', '是正処置',
             'エビデンス（是正処置）', '是正実施年月日','プロセスオーナー','是正処置の有効性の確認','エビデンス','確認年月日', '監査リーダー確認']

  @products = Product.joins(documents_attachments: :blob)
                     .where("active_storage_blobs.filename LIKE ?", "%内部監査是正処置報告書%")
                     .distinct

  Rails.logger.info "内部監査是正処置報告書を含む製品数: #{@products.count}"

  workbook = RubyXL::Workbook.new
  worksheet = workbook.worksheets[0]
  worksheet.sheet_name = "システム読込用フォーム"

  headers.each_with_index do |header, index|
    worksheet.add_cell(0, index, header)
  end

  row = 1
  pattern = "/myapp/db/documents/*内部監査是正処置報告書*.{xlsx,xls}"
  files = Dir.glob(pattern)
  Rails.logger.info "検出されたファイル数: #{files.count}"

  files.each do |file|
    process_correction_report_file(file, worksheet, row)
    row = worksheet.sheet_data.size
  end

  Rails.logger.info "======================================="
  Rails.logger.info "デバッグ情報の出力が完了しました"
  Rails.logger.info "======================================="

  excel_data = workbook.stream.string

  send_data excel_data, filename: "audit_correction_report.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
end

def process_correction_report_file(file, worksheet, row)
  begin
    Rails.logger.info "ファイルの処理を開始します: #{File.basename(file)}"

    source_workbook = if File.extname(file) == '.xlsx'
                        Roo::Excelx.new(file)
                      else
                        Roo::Excel.new(file)
                      end

    source_worksheet = source_workbook.sheet('システム読込用フォーム')

    unless source_worksheet
      Rails.logger.error "「システム読込用フォーム」シートが見つかりません: #{File.basename(file)}"
      return
    end

    data = get_correction_report_data(source_worksheet)

    data.each_with_index do |value, col_index|
      cell = worksheet.add_cell(row, col_index, value)
      if [6, 13, 20,26,30].include?(col_index) # 監査実施日, 是正立案予定日, 確認年月日の列インデックス
        cell.set_number_format('yyyy/mm/dd')
      end
    end

  rescue => e
    Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
    Rails.logger.error "エラー: #{e.class.name} - #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
  end
end

def get_correction_report_data(source_worksheet)
  [
    source_worksheet.cell(1, 'C'),  # 発行No.
    source_worksheet.cell(3, 'P'),  # 承認者
    source_worksheet.cell(3, 'Q'),  # 作成者
    source_worksheet.cell(4, 'D'),  # 監査タイプ
    source_worksheet.cell(6, 'C'),  # 対象プロセス
    source_worksheet.cell(6, 'P'),  # 監査対応者
    parse_date(source_worksheet.cell(7, 'C')),  # 監査実施日
    source_worksheet.cell(6, 'J'),  # 監査チーム
    source_worksheet.cell(8, 'I'),  # 不適合区分
    source_worksheet.cell(10, 'B'), # 不適合内容
    source_worksheet.cell(11, 'D'), # 条項
    source_worksheet.cell(13, 'B'), # 不適合の根拠
    source_worksheet.cell(15, 'B'), # 不適合の区分の根拠
    parse_date(source_worksheet.cell(10, 'Q')), # 是正立案予定日
    source_worksheet.cell(13, 'Q'), # 監査リーダー
    source_worksheet.cell(10, 'P'), # エビデンス（不適合内容）
    source_worksheet.cell(18, 'B'), # 修正内容
    source_worksheet.cell(20, 'D') == '☑' ? '否' : '要', # 封じ込め
    source_worksheet.cell(22, 'D') == '☑' ? '否' : '要', # 水平展開
    source_worksheet.cell(18, 'P'), # エビデンス（修正）
    parse_date(source_worksheet.cell(18, 'Q')), # 実施日
    source_worksheet.cell(20, 'Q'), # プロセスオーナー
    (25..29).map.with_index(1) { |row, index| 
      cell_value = source_worksheet.cell(row, 'C')
      cell_value.present? ? "なぜ#{index}：#{cell_value}" : nil
    }.compact.join("\n"), # 発生原因
    source_worksheet.cell(25, 'Q'), # プロセスオーナー
    source_worksheet.cell(31, 'B'), # 是正処置
    source_worksheet.cell(31, 'P'), # エビデンス（是正処置）
    parse_date(source_worksheet.cell(31, 'Q')), # 是正実施年月日
    source_worksheet.cell(33, 'Q'), # プロセスオーナー
    source_worksheet.cell(36, 'B'), # 是正処置の有効性の確認
    source_worksheet.cell(37, 'P'), # エビデンス（有効性の確認）
    parse_date(source_worksheet.cell(37, 'Q')), # 確認年月日
    source_worksheet.cell(39, 'Q')  # 監査リーダー確認
  ]
end

def parse_date(value)
  case value
  when Date, Time
    value
  when String
    begin
      Date.parse(value)
    rescue Date::Error
      value
    end
  when Numeric
    begin
      # Excelの日付は1900年1月1日からの経過日数
      base_date = Date.new(1899, 12, 30)
      base_date + value.to_i
    rescue Date::Error
      value
    end
  else
    value
  end
end










  def export_phases_to_excel
    Rails.logger.debug "Starting export_phases_to_excel method"
    puts "Starting export_phases_to_excel method"
    phase  # @dropdownlistを設定するためにphaseメソッドを呼び出す
  
    @products = Product.all  # または適切なスコープを使用
  
    workbook = RubyXL::Workbook.new
    
    sheets_data = {
      "フェーズ1" => ["顧客インプット", "顧客の声", "設計目標", "製品保証計画書", "製品・製造工程の前提条件", "製品・製造工程のベンチマークデータ", "製品の信頼性調査", "経営者の支援", "特殊製品特性・特殊プロセス特性の暫定リスト", "暫定材料明細表", "暫定プロセスマップフロー図", "信頼性目標・品質目標", "事業計画・マーケティング戦略"],
      "フェーズ2" => ["試作コントロールプラン", "設計検証", "設計故障モード影響解析（DFMEA）", "製造性・組立性を考慮した設計", "特殊製品特性・特殊プロセス特性", "材料仕様書", "技術仕様書", "実現可能性検討報告書および経営者の支援", "図面（数学的データを含む）", "図面・仕様書の変更", "デザインレビュー", "ゲージ・試験装置の要求事項"],
      "フェーズ3" => ["製品・プロセスの品質システムのレビュー", "経営者の支援(Phase3)", "特性マトリクス", "測定システム解析計画書", "梱包規格・仕様書", "工程能力予備調査計画書", "先行生産（Pre-launch,量産試作）コントロールプラン", "プロセス故障モード影響解析（PFMEA）", "プロセス指示書", "プロセスフロー図(Phase3)", "フロアプランレイアウト"],
      "フェーズ4" => ["量産コントロールプラン", "量産の妥当性確認試験", "生産部品承認(PPAP)", "測定システム解析", "梱包評価", "工程能力予備調査", "実質的生産", "品質計画承認署名"],
      "フェーズ5" => ["顧客満足の向上", "引渡しおよびサービスの改善", "学んだ教訓・ベストプラクティスの効果的な利用", "変動の減少"],
      "PPAP" => ["顧客技術承認", "顧客固有要求事項適合記録", "部品提出保証書（PSW)", "設計FMEA", "製品設計文書", "製品サンプル", "測定システム解析（MSA)", "検査補助具", "材料・性能試験結果", "有資格試験所文書", "技術変更文書（顧客承認）", "寸法測定結果", "外観承認報告書（AAR)", "初期工程調査結果", "マスターサンプル", "プロセスフロー図", "プロセスFMEA", "バルク材料チェックリスト", "コントロールプラン"],
      "8.3製品の設計・開発" => ["顧客要求事項検討会議事録_営業", "金型製造指示書_営業", "金型製作依頼票_金型設計", "進捗管理票_生産技術", "試作製造指示書_営業", "設計計画書_金型設計", "設計検証チェックリスト_金型設計", "設計変更会議議事録_金型設計", "製造実現可能性検討書", "妥当性確認記録_金型設計", "初期流動検査記録", "レイアウト/歩留まり_営業", "DR構想検討会議議事録_生産技術", "DR会議議事録_金型設計"]
    }
  
    sheets_data.each do |sheet_name, headers|
      worksheet = workbook.add_worksheet(sheet_name)
      
      # ヘッダー行の追加
      headers.unshift("図番")
      headers.each_with_index do |header, index|
        worksheet.add_cell(0, index, header)
      end
  
      # データ行の追加
      grouped_products = @products.group_by(&:partnumber)
      row = 1
      grouped_products.each do |partnumber, products|
        worksheet.add_cell(row, 0, partnumber)
        
        products.each do |product|
          next unless @dropdownlist[product.phase.to_i] == sheet_name
          
          Rails.logger.debug "Processing product: #{product.partnumber}, Phase: #{product.phase}"
          
          headers[1..-1].each_with_index do |header, col|
            if @dropdownlist[product.stage.to_i] == header
              status = case product.status
                       when "完了"
                         "完"
                       when "仕掛中"
                         "仕"
                       else
                         "―"
                       end
              worksheet.add_cell(row, col + 1, status)
              Rails.logger.debug "Header: #{header}, Status: #{status}"
            end
          end
        end
        row += 1
      end
    end
  
    send_data workbook.stream.string, filename: "phases_data.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  end

  def process_design_plan_report
    @products = Product.where(partnumber: params[:partnumber]) # link_to用
    @all_products = Product.all
    Rails.logger.debug { "params: #{params.inspect}" } # 追加
    # @products = Product.where(partnumber: params[:product][:partnumber]) #form_to用

    create_data
    send_data(
      excel_render('lib/excel_templates/process_design_plan_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_製造工程設計計画／実績書.xlsx"
    )
  end


  

  def apqp_plan_report
    @products = Product.where(partnumber: params[:partnumber]) # link_to用
    @all_products = Product.all
    Rails.logger.debug { "params: #{params.inspect}" } # 追加
    # @products = Product.where(partnumber: params[:product][:partnumber]) #form_to用

    create_data_apqp_plan_report
    send_data(
      excel_render('lib/excel_templates/apqp_plan_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_APQP計画書.xlsx"
    )
  end

  def apqp_approved_report
    @products = Product.where(partnumber: params[:partnumber]) # link_to用
    @all_products = Product.all
    Rails.logger.debug { "params: #{params.inspect}" } # 追加
    # @products = Product.where(partnumber: params[:product][:partnumber]) #form_to用

    create_data_apqp_approved_report
    send_data(
      excel_render('lib/excel_templates/apqp_approved_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_APQP総括・承認書.xlsx"
    )
  end

  # kここにあった
  
  def iot
    # 【Rails】Time.currentとTime.nowの違い
    # https://qiita.com/kodai_0122/items/111457104f83f1fb2259

    timetoday = Time.current.strftime('%Y_%m_%d')

    # CSVで取り込んだデータを綺麗なグラフで表示する
    # https://toranoana-lab.hatenablog.com/entry/2018/11/27/182518

    # ファイルやディレクトリが存在するか調べる (File.exist?, Dir.exist?)
    # https://maku77.github.io/ruby/io/file-exist.html
    data = []
    data_temp = []
    if File.file?("/myapp/db/record/iot/#{timetoday}SHT31Temp.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}SHT31Temp.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_temp.push(data)
      end
      @temp = data_temp
    end

    data = []
    data_humi = []
    if File.file?("/myapp/db/record/iot/#{timetoday}SHT31Humi.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}SHT31Humi.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_humi.push(data)
      end
      @humi = data_humi
    end

    #----- Komatsu25トン3号機

    data = []
    data_komatsu25t3_shot = []
    if File.file?("/myapp/db/record/iot/#{timetoday}ShotKomatsu25t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}ShotKomatsu25t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_komatsu25t3_shot.push(data)
      end
      @komatsu25t3_shot = data_komatsu25t3_shot
    end

    data = []
    data_komatsu25t3_spm = []
    if File.file?("/myapp/db/record/iot/#{timetoday}SPMKomatsu25t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}SPMKomatsu25t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_komatsu25t3_spm.push(data)
      end
      @komatsu25t3_spm = data_komatsu25t3_spm
    end

    data = []
    data_komatsu25t3_chokotei = []
    if File.file?("/myapp/db/record/iot/#{timetoday}StampingchokoteiKomatsu25t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}StampingchokoteiKomatsu25t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_komatsu25t3_chokotei.push(data)
      end
      @komatsu25t3_chokotei = data_komatsu25t3_chokotei
    end

    data = []
    data_komatsu25t3_jyotai = []
    if File.file?("/myapp/db/record/iot/#{timetoday}JYOTAIKomatsu25t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}JYOTAIKomatsu25t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_komatsu25t3_jyotai.push(data)
      end
      @komatsu25t3_jyotai = data_komatsu25t3_jyotai
    end

    #----- Dobby3トン4号機

    data = []
    data_chokoteiDobby30t4 = []
    if File.file?("/myapp/db/record/iot/#{timetoday}chokoteiDobby30t4.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}chokoteiDobby30t4.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_chokoteiDobby30t4.push(data)
      end
      @chokoteiDobby30t4 = data_chokoteiDobby30t4
    end

    data = []
    data_JYOTAIDobby30t4 = []
    if File.file?("/myapp/db/record/iot/#{timetoday}JYOTAIDobby30t4.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}JYOTAIDobby30t4.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_JYOTAIDobby30t4.push(data)
      end
      @JYOTAIDobby30t4 = data_JYOTAIDobby30t4
    end

    #----- Amada80トン3号機

    data = []
    data_StampingJYOTAIAmada80t3 = []
    if File.file?("/myapp/db/record/iot/#{timetoday}StampingJYOTAIAmada80t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}StampingJYOTAIAmada80t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_StampingJYOTAIAmada80t3.push(data)
      end
      @StampingJYOTAIAmada80t3 = data_StampingJYOTAIAmada80t3
    end

    data = []
    data_StampingchokoteiAmada80t3 = []
    if File.file?("/myapp/db/record/iot/#{timetoday}StampingchokoteiAmada80t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}StampingchokoteiAmada80t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_StampingchokoteiAmada80t3.push(data)
      end
      @StampingchokoteiAmada80t3 = data_StampingchokoteiAmada80t3
    end

    data = []
    data_SPMAmada80t3 = []
    if File.file?("/myapp/db/record/iot/#{timetoday}SPMAmada80t3.csv")
      CSV.foreach("/myapp/db/record/iot/#{timetoday}SPMAmada80t3.csv", headers: true) do |row|
        data = [row[0], row[1]]
        data_SPMAmada80t3.push(data)
      end
      @SPMAmada80t3 = data_SPMAmada80t3
    end

    data = []
    data_ShotAmada80t3 = []
    return unless File.file?("/myapp/db/record/iot/#{timetoday}ShotAmada80t3.csv")

    CSV.foreach("/myapp/db/record/iot/#{timetoday}ShotAmada80t3.csv", headers: true) do |row|
      data = [row[0], row[1]]
      data_ShotAmada80t3.push(data)
    end
    @ShotAmada80t3 = data_ShotAmada80t3

    # timetoday=Time.now.strftime("%Y_%m_%d")
    # file = Dir.glob("C:/Users/mec21/20230213_iot_csv_training_tailwind_daisyui_ancestry_importmap/db/record/"+timetoday+"SHT31Humi.csv")
    # file = Dir.glob("/myapp/db/record/iot/2023_02_18SHT31Temp.csv")
    # IOTデータページ

    # @iots=Iot.all
  end

  def import
    # fileはtmpに自動で一時保存される
    Product.import(params[:file])
    redirect_to products_url
  end

  # def iot_import
  # fileはtmpに自動で一時保存される

  # 【Rails】ファイルのフルパス、ファイル名を取得する
  # https://opiyotan.hatenablog.com/entry/rails-glob

  # time=Time.now.strftime("%Y_%m_%d")

  # file = Dir.glob("C:/Users/mec21/20230213_iot_csv_training_tailwind_daisyui_ancestry_importmap/db/record/test.csv")

  # file = params[:file]

  # datas = []
  # unless file.nil?
  #  ActiveRecord::Base.transaction do
  #    CSV.foreach(file.path, headers: true) do |row|
  #      datas.append(Hash[row])
  #    end
  #  end
  # end
  # @chartkickgraph = {"1": 1000,"3": 20000,"5": 1500,"7": 18000}
  # @chartkickgraph = datas[0]

  # redirect_to products_url
  # end

  # RailsでAxlsxを使ってxlsxを生成
  # https://qiita.com/necojackarc/items/0dbd672b2888c30c5a38

  def xlsx
    @products = Product.all
    respond_to do |format|
      format.html
      format.xlsx do
        generate_xlsx
      end
    end
  end

  def search
    @qd = Product.ransack(params[:qd])
    # @products = @qd.result
    @products = @qd.result(distinct: true)
    # @user = current_user
    # binding.pry
  end

  def graph
    # @products=Product.all.page(params[:page]).per(10)
    @products = Product.all
    # @user = current_user
  end

  def calendar
    # @products=Product.all.page(params[:page]).per(10)
    @products = Product.all
    # @user = current_user
  end

  def training
    # @products=Product.all.page(params[:page]).per(10)
    # @products=Product.all
    @products = Product.includes(:documents_attachments).all
    # @products = Product.includes(:documents_attachments).page(params[:page]).per(10)

    # @user = current_user
  end
  
  def index

    # PDFリンクの取得
    get_pdf_links(['https://www.iatfglobaloversight.org/iatf-169492016/iatf-169492016-sis/', 'https://www.iatfglobaloversight.org/iatf-169492016/iatf-169492016-faqs/'])

    allowed_emails = ['yasuhiro-suzuki@mitsui-s.com', 'n_komiya@mitsui-s.com']

    # セッションパスワードをログに記録
    Rails.logger.info "MainPage_index_Session download_password: #{session[:download_password]}"


    # Add user IP to allowed list if user's email is allowed
    if Rails.env.development? && current_user&.email&.in?(allowed_emails)
      user_ip = request.remote_ip
      Rails.application.config.web_console.permissions = user_ip
    end

    @user = current_user

    @q = Product.ransack(params[:q])
    
    # デバッグ情報
    Rails.logger.debug "Ransack params: #{params[:q].inspect}"
    Rails.logger.debug "Ransack object: #{@q.inspect}"
    
    # 数値型カラムに対する検索条件を別途処理
    numeric_columns = [:goal_attainment_level] # 他の数値型カラムがあればここに追加
    
    numeric_columns.each do |column|
      if params[:q] && params[:q]["#{column}_cont"].present?
        value = params[:q]["#{column}_cont"]
        @q.build_condition("#{column}_eq".to_sym => value.to_i)
        params[:q].delete("#{column}_cont")
      end
    end
    
    #@products = @q.result(distinct: true).includes(:documents_attachments).page(params[:page]).per(12)
    @products = @q.result(distinct: true)
               .includes(documents_attachments: :blob)
               .page(params[:page])
               .per(12)


    # 追加のデバッグ情報
    Rails.logger.debug "SQL query: #{@products.to_sql}"
    Rails.logger.debug "Results on this page: #{@products.count}"
    Rails.logger.debug "First result: #{@products.first.inspect}" if @products.any?
  end
  

  def show
    # @product = Product.find(params[:id])
    return unless @product.documents.attached?

    @product.documents.each do |image|
      fullfilename = rails_blob_path(image)
      @ext = File.extname(fullfilename).downcase
      @Attachment_file = @ext == '.jpg' || @ext == '.jpeg' || @ext == '.png' || @ext == '.gif'
    end
  end

  def new
    @product = Product.new
  end

  def index2
    # @products = Product.where(partnumber:params[:partnumber])
    @products = Product.includes(:documents_attachments).where(partnumber: params[:partnumber])
  end

  def index3
    # こちらを選択していた@products=Product.select("DISTINCT ON (partnumber,food) *").page(params[:page]).per(4)
    @products = Product.select('DISTINCT ON (partnumber,stage) *')

    @mark_complate = '完'
    @mark_WIP = '仕掛'

    # @user = current_user
  end

  def index4
    # IATF要求事項説明ページ
  end

  def index8
    @products = Product.where(partnumber: params[:partnumber])
  end

  def index9
    @products = Product.select('DISTINCT ON (partnumber,stage) *')

    # @user = current_user
  end

  # RailsでExcel出力しないといけなくなった時の対処法
  # https://www.timedia.co.jp/tech/railsexcel/

  def download
    response.headers['Content-Type'] = 'application/excel'
    response.headers['Content-Disposition'] = 'attachment; filename="製品データ.xls"'
    # @date_from = Date.new(2014,3,1)
    # @date_to = Date.new(2014,3,31)
    # @product = Product.find(params[:id])
    @products = Product.all

    # @stocks = ProductStock
    #  .where(product_id: @product.id)
    #  .where(date: @date_from..@date_to)
    #  .order(:date)
    render 'data_download.xls.erb'
  end

  # RailsでExcel出力しないといけなくなった時の対処法
  # https://www.timedia.co.jp/tech/railsexcel/
  # def process_design_download
  #  response.headers["Content-Type"] = "application/excel"
  #  response.headers["Content-Disposition"] = "attachment; filename=\"製造工程設計計画書／実績書.xls\""
  #  @products = Product.where(partnumber:params[:partnumber])
  #  render 'process_design_download.xls.erb'
  # end

  #  def process_design_download
  #    response.headers["Content-Type"] = "application/excel"
  #    response.headers["Content-Disposition"] = "attachment; filename=\"製造工程設計計画書／実績書.xls\""
  #    @products = Product.where(partnumber: params[:partnumber])
  #    render 'products/process_design_download', formats: [:xls]
  #  end

  def process_design_download
    require 'axlsx'
    template_path = Rails.root.join('app/views/products/process_design_download.xlsx').to_s
    # テンプレートファイルを読み込む
    template = Axlsx::Package.new
    workbook = template.workbook
    workbook = workbook.open(template_path)
    worksheet = workbook.worksheets.first

    @products = Product.where(partnumber: params[:partnumber])

    # データを挿入する行のインデックス
    start_row = 2

    # データを挿入する
    @products.each_with_index do |product, index|
      row = start_row + index
      worksheet.add_row [
        product.category,
        product.created_at,
        product.deadline_at,
        product.description,
        product.documentcategory,
        product.documentname,
        product.documentnumber,
        product.documentrev,
        product.documenttype,
        product.end_at,
        product.goal_attainment_level,
        product.id,
        product.materialcode,
        product.object,
        product.partnumber,
        product.phase,
        product.stage,
        product.start_time,
        product.status,
        product.tasseido,
        product.updated_at
      ], row_offset: row
    end

    # ダウンロード用の一時ファイルを作成
    temp_file = Tempfile.new('process_design_download.xlsx')

    # テンプレートを保存してダウンロードファイルを作成
    template.serialize(temp_file.path)

    # ダウンロードファイルを送信
    send_file temp_file.path, filename: '製造工程設計計画書／実績書.xlsx'

    # 一時ファイルを削除
    temp_file.close
    temp_file.unlink
  end

  def edit
    # @product = Product.find(params[:id])
    @title = Product.find(params[:id])
    return unless @product.documents.attached?

    @product.documents.each do |image|
      fullfilename = rails_blob_path(image)
      @ext = File.extname(fullfilename).downcase
      @Attachment_file = @ext == '.jpg' || @ext == '.jpeg' || @ext == '.png' || @ext == '.gif'
    end
  end

  def create
    @product = Product.new(product_params)
    if @product.save
      redirect_to @product, notice: '登録しました。'
    else
      render :new
    end
  end

  #  def update
  #    #Rails7で画像の保存にActiveStorage使ってみよう(導入からリサイズまで)
  #    #https://qiita.com/asasigure/items/311473d25fb3ec97f126
  #
  #    #ActiveStorage で画像を複数枚削除する方法
  #    #https://h-piiice16.hatenablog.com/entry/2018/09/24/141510#
  #
  #    #Active Storageを使用して添付ファイル(アップロード)を簡単に管理する
  #    #https://www.petitmonte.com/ruby/rails_attachment.html
  #
  #    #@product = Product.find(params[:id])
  #    #@product.update params.require(:product).permit(:partnumber, documents: []) # POINT
  #    #redirect_to @product
  #
  #
  #    product = Product.find(params[:id])
  #    #if params[:product][:detouch]=='1'
  #    if params[:product][:detouch]
  #       params[:product][:detouch].each do |image_id|
  #       #image = product.files.find(image_id)
  #        image = @product.documents.find(image_id)
  #        image.purge
  #       end
  #    end
  #   #【rails】update_attributes→updateを使う
  #   #update_attributesはrails6.1から削除されたそうです。
  #   #https://qiita.com/yuka_nari/items/b04c872d4eb2e5347fdb
  #
  #   if product.update(product_params)
  #     flash[:success] = "編集しました"
  #    redirect_to @product
  #   else
  #    render :edit
  #   end
  #  end

  # ChatGPT修正版
  def update
    @product = Product.find_by(id: params[:id])

    if @product.nil?
      flash[:error] = 'Product not found'
      redirect_to root_path # Or wherever you want to redirect
      return
    end

    params[:product][:detouch]&.each do |image_id|
      image = @product.documents.find(image_id)
      image.purge
    end

    @product.documents.attach(params[:product][:documents]) if params[:product][:documents]

    if @product.update(product_params.except(:documents))
      flash[:success] = '編集しました'
      redirect_to @product
    else
      render :edit
    end
  end

  def destroy
    # @product = Product.find(params[:id])
    @product.destroy
    respond_to do |format|
      format.html { redirect_to products_url, notice: 'Product was successfully destroyed.' }
      format.json { head :no_content }
    end
  end

  private

  

  # def restrict_ip_address
  #   # 現在のユーザーが ALLOWED_EMAILS のいずれかでログインしている場合、制限をスキップ
  #   return if current_user && ALLOWED_EMAILS.include?(current_user.email)

  # 許可されていないIPアドレスからのアクセスを制限
  #   unless ALLOWED_IPS.include? request.remote_ip
  #     render text: 'Access forbidden', status: 403
  #     return
  #   end
  # end

  # Railsで既存のエクセルファイルをテンプレートにできる魔法のヘルパー
  # https://qiita.com/m-kubo/items/6b5beaaf2a59c0d75bcc#:~:text=Rails%E3%81%A7%E6%97%A2%E5%AD%98%E3%81%AE%E3%82%A8%E3%82%AF%E3%82%BB%E3%83%AB%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%82%92%E3%83%86%E3%83%B3%E3%83%97%E3%83%AC%E3%83%BC%E3%83%88%E3%81%AB%E3%81%A7%E3%81%8D%E3%82%8B%E9%AD%94%E6%B3%95%E3%81%AE%E3%83%98%E3%83%AB%E3%83%91%E3%83%BC%201%20%E3%81%AF%E3%81%98%E3%82%81%E3%81%AB%20%E4%BB%8A%E5%9B%9E%E3%81%AE%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AF%E3%80%81%E4%BB%A5%E4%B8%8B%E3%81%AE%E7%92%B0%E5%A2%83%E3%81%A7%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E3%81%97%E3%81%A6%E3%81%84%E3%81%BE%E3%81%99%E3%80%82%20...%202%201.%20rubyXL,7%206.%20%E3%81%8A%E3%81%BE%E3%81%91%20...%208%20%E7%B5%82%E3%82%8F%E3%82%8A%E3%81%AB%20%E4%BB%A5%E4%B8%8A%E3%80%81%E3%81%A9%E3%81%93%E3%81%8B%E3%81%AE%E6%A1%88%E4%BB%B6%E3%81%A7%E6%9B%B8%E3%81%84%E3%81%9F%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AE%E7%B4%B9%E4%BB%8B%E3%81%A7%E3%81%97%E3%81%9F%E3%80%82%20
  def create_data
    @excel_template_initial = true # Excelテンプレートを初期値にする
    @insert_rows_to_excel_template = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @insert_rows_to_excel_template_msa = true # MSA GRRを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @insert_rows_to_excel_template_dr_setsubi = true # 初回のファイルのみ挿入サブルーチンに飛ぶ
    @insert_rows_to_excel_template_progress_management = true # 初回のファイルのみ挿入サブルーチンに飛ぶ

    @datetime = Time.zone.now
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
    @cp_check = '☐'
    @datou_check = '☐'
    @scr_check = '☐'
    @pfmea_check = '☐'
    @dr_check = '☐'
    @msa_check = '☐'
    @msa_crosstab_check = '☐'
    @msa_grr_check = '☐'
    @cpk_check = '☐'
    @shisaku_check = '☐'
    @kanagata_check = '☐'
    @dr_setsubi_check = '☐'
    @grr_check = '☐'
    @feasibility_check = '☐'
    @kataken_check = '☐'
    @visual_inspection_tejyunsho_check = '☐'
    @visual_inspection_youryousho_check = '☐'
    @stamping_instruction_check = '☐'
    @process_inspection_record_check = '☐'
    @drawing_check = '☐'
    @specifications_check = '☐'
    @parts_inspection_report_check = '☐'
    @material_specification_check = '☐'
    @shoki_check = '☐'
    @controlplan_check = '☐'
    @processflow_inspection_check = '☐'
    @processflow_mold_check = '☐'

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= #{@partnumber}" # 追加
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= #{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= #{pro.stage}"

      if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'
        
        @processflow_check = if pro.documents.attached?
          '☑'
           
          begin
            # プレスファイルの確認
            press_file_found = false
            mold_file_found = false
            
            # 最初にプレスファイルを探す
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              if filename.include?('プロセスフロー') && filename.include?('プレス')
                press_file_found = true
                begin
                  temp_file = Tempfile.new(['temp', File.extname(filename)])
                  temp_file.binmode
                  temp_file.write(doc.download)
                  temp_file.rewind

                  workbook = case File.extname(filename).downcase
                            when '.xlsx' then Roo::Excelx.new(temp_file.path)
                            when '.xls'  then Roo::Excel.new(temp_file.path)
                            else
                              next
                            end

                  Rails.logger.info "=== ワークシート情報 ==="
                  Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                  
                  # 適切なシートを探す
                  target_sheet = nil
                  workbook.sheets.each do |sheet_name|
                    workbook.default_sheet = sheet_name
                    Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                    
                    # セル(2,21)とセル(2,22)の値を確認
                    cell_2_21 = workbook.cell(2, 21)
                    cell_2_22 = workbook.cell(2, 22)
                    
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                    
                    if cell_2_21.present? || cell_2_22.present?
                      target_sheet = sheet_name
                      Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                      break
                    end
                  end

                  unless target_sheet
                    Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                    next
                  end

                  workbook.default_sheet = target_sheet
                  Rails.logger.info "選択したシート: #{target_sheet}"
                  Rails.logger.info "最終行: #{workbook.last_row}"
                  Rails.logger.info "最終列: #{workbook.last_column}"

                  # セルの値を文字列として取得し、デバッグ情報を出力
                  @processflow_stamping_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_stamping_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_stamping_check = '☑'

                  Rails.logger.info "=== セルの値確認 ==="
                  Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                  Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_stamping_person_in_charge.inspect}"
                  Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                  Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_stamping_dept.inspect}"

                  Rails.logger.info "プレス承認者: \#{?processflow_stamping_person_in_charge}"
                  Rails.logger.info "プレス部署: \#{?processflow_stamping_dept}"
                rescue StandardError => e
                  Rails.logger.error "プレスファイル処理エラー: #{e.message}"
                ensure
                  workbook&.close if defined?(workbook) && workbook
                  temp_file.close
                  temp_file.unlink
                end
                break
              end
            end

            # プレスファイルがない場合は成形ファイルを探す
            unless press_file_found
              pro.documents.each do |doc|
                filename = doc.filename.to_s
                if filename.include?('プロセスフロー') && filename.include?('成形')
                  mold_file_found = true
                  begin
                    temp_file = Tempfile.new(['temp', File.extname(filename)])
                    temp_file.binmode
                    temp_file.write(doc.download)
                    temp_file.rewind

                    workbook = case File.extname(filename).downcase
                              when '.xlsx' then Roo::Excelx.new(temp_file.path)
                              when '.xls'  then Roo::Excel.new(temp_file.path)
                              else
                                next
                              end

                    Rails.logger.info "=== ワークシート情報 ==="
                    Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                    
                    # 適切なシートを探す
                    target_sheet = nil
                    workbook.sheets.each do |sheet_name|
                      workbook.default_sheet = sheet_name
                      Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                      
                      # セル(2,21)とセル(2,22)の値を確認
                      cell_2_21 = workbook.cell(2, 21)
                      cell_2_22 = workbook.cell(2, 22)
                      
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                      
                      if cell_2_21.present? || cell_2_22.present?
                        target_sheet = sheet_name
                        Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                        break
                      end
                    end

                    unless target_sheet
                      Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                      next
                    end

                    workbook.default_sheet = target_sheet
                    Rails.logger.info "選択したシート: #{target_sheet}"
                    Rails.logger.info "最終行: #{workbook.last_row}"
                    Rails.logger.info "最終列: #{workbook.last_column}"

                    # セルの値を文字列として取得し、デバッグ情報を出力
                    @processflow_mold_person_in_charge = workbook.cell(2, 21).to_s.strip
                    @processflow_mold_dept = workbook.cell(4, 13).to_s.strip
                    @processflow_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
                    @processflow_mold_kanryou = pro.end_at.strftime('%y/%m/%d')
                    @processflow_mold_check = '☑'

                    Rails.logger.info "=== セルの値確認 ==="
                    Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                    Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_mold_person_in_charge.inspect}"
                    Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                    Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_mold_dept.inspect}"

                    Rails.logger.info "成形承認者: \#{?processflow_mold_person_in_charge}"
                  rescue StandardError => e
                    Rails.logger.error "成形ファイル処理エラー: #{e.message}"
                  ensure
                    workbook&.close if defined?(workbook) && workbook
                    temp_file.close
                    temp_file.unlink
                  end
                  break
                end
              end
            end

            # 営業、工程設計、検査のファイルは毎回確認
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              next unless filename.include?('プロセスフロー')

              begin
                temp_file = Tempfile.new(['temp', File.extname(filename)])
                temp_file.binmode
                temp_file.write(doc.download)
                temp_file.rewind

                workbook = case File.extname(filename).downcase
                          when '.xlsx' then Roo::Excelx.new(temp_file.path)
                          when '.xls'  then Roo::Excel.new(temp_file.path)
                          else
                            next
                          end

                Rails.logger.info "=== ワークシート情報 ==="
                Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                
                # 適切なシートを探す
                target_sheet = nil
                workbook.sheets.each do |sheet_name|
                  workbook.default_sheet = sheet_name
                  Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                  
                  # セル(2,21)とセル(2,22)の値を確認
                  cell_2_21 = workbook.cell(2, 21)
                  cell_2_22 = workbook.cell(2, 22)
                  
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                  
                  if cell_2_21.present? || cell_2_22.present?
                    target_sheet = sheet_name
                    Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                    break
                  end
                end

                unless target_sheet
                  Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                  next
                end

                workbook.default_sheet = target_sheet
                Rails.logger.info "選択したシート: #{target_sheet}"
                Rails.logger.info "最終行: #{workbook.last_row}"
                Rails.logger.info "最終列: #{workbook.last_column}"

                # セルの値を文字列として取得し、デバッグ情報を出力
                if filename.include?('営業')
                  @processflow_sales_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_sales_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_sales_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_sales_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_sales_check='☑'
                  Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
                elsif filename.include?('工程設計')
                  @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_design_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_design_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_design_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_design_check='☑'
                  Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
                elsif filename.include?('検査')
                  @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_inspection_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_inspection_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_inspection_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_inspection_check='☑'
                  Rails.logger.info "検査引渡し承認者: \#{?processflow_inspection_person_in_charge}"
                end
              rescue StandardError => e
                Rails.logger.error "その他ファイル処理エラー: #{e.message}"
              ensure
                workbook&.close if defined?(workbook) && workbook
                temp_file.close
                temp_file.unlink
              end
            end

          rescue StandardError => e
            Rails.logger.error "ファイル処理エラー: #{e.message}"
          end
        else
          '☐'
        end
      end

      if stage == 'フロアプランレイアウト'
        @floor_plan_layout_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @floor_plan_layout_kanryou = pro.end_at.strftime('%y/%m/%d')
        @floor_plan_layout_person_in_charge = "鈴木"
        @floor_plan_layout_check = if pro.documents.attached?

          '☑'
        else
          '☐'
        end
      end

      if %w[量産コントロールプラン 試作コントロールプラン].include?(stage)
        @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
        @cp_check = if pro.documents.attached?
                      '☑'
                    else
                      '☐'
                    end
      end

      if stage == '特性マトリクス'
        @special_characteristics_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @special_characteristics_kanryou = pro.end_at.strftime('%y/%m/%d')
        @special_characteristics_person_in_charge = "鈴木"
        @special_characteristics_check = if pro.documents.attached?

          '☑'
        else
          '☐'
        end
      end

      if stage == '妥当性確認記録_金型設計'
        @datou_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @datou_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @datou_check = '☑'

          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*妥当性確認記録*"
          Rails.logger.info "Path= #{pattern}"

          files = Dir.glob(pattern)
          files.each do |file|
            workbook = nil
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file)
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file)
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # X36のセルの値を取得
            # RubyXLライブラリでExcelのセルを参照する際、行と列のインデックスは0から始まります。
            # したがって、1行1列目のセルは worksheet.cell(1, 1) としてアクセスされます。
            # したがって、セルX36を指定する場合:
            # 行番号: 36 - 1 = 35
            # 列番号: Xは24番目の列なので、24 - 1 = 23
            @datou_result = worksheet.cell(36, 24).presence || worksheet.cell(41, 13)
            @datou_person_in_charge = worksheet.cell(39, 22)
            @datou_kanryou = worksheet.cell(37, 6).presence || worksheet.cell(43, 4)
            Rails.logger.info '妥当性確認' # 追加
            Rails.logger.info "@partnumber= #{@partnumber}" # 追加
            Rails.logger.info "@datou_result #{@datou_result}" # 追加
          end

        else
          @datou_check = '☐'
        end
      end

      if stage == '顧客要求事項検討会議事録_営業'
        @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
        @scr_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == '梱包規格・仕様書'
        @packing_instruction_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @packing_instruction_kanryou = pro.end_at.strftime('%y/%m/%d')
        @packing_instruction_check = if pro.documents.attached?
          '☑'
        else
          '☐'
        end
      end

      if stage == '部品検査成績書'
        @parts_inspection_report_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @parts_inspection_report_kanryou = pro.end_at.strftime('%y/%m/%d')
        @parts_inspection_report_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == '技術仕様書'
        @specifications_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @specifications_kanryou = pro.end_at.strftime('%y/%m/%d')
        @specifications_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == '図面（数学的データを含む）' || stage == '図面・仕様書の変更'
        @drawing_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @drawing_kanryou = pro.end_at.strftime('%y/%m/%d')
        @drawing_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == 'プレス作業手順書'
        @stamping_instruction_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @stamping_instruction_kanryou = pro.end_at.strftime('%y/%m/%d')
        @stamping_instruction_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == '工程検査記録票'
        @process_inspection_record_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @process_inspection_record_kanryou = pro.end_at.strftime('%y/%m/%d')
        @process_inspection_record_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end



      if stage == '外観検査要領書'
        @visual_inspection_youryousho_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @visual_inspection_youryousho_kanryou = pro.end_at.strftime('%y/%m/%d')
        @visual_inspection_youryousho_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end

      if stage == '検査手順書'
        @visual_inspection_tejyunsho_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @visual_inspection_tejyunsho_kanryou = pro.end_at.strftime('%y/%m/%d')
        @visual_inspection_tejyunsho_check = if pro.documents.attached?
                       '☑'
                     else
                       '☐'
                     end
      end
      



      if stage == '製造実現可能性検討書'
        @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
        @feasibility_check = if pro.documents.attached?
                               '☑'
                             else
                               '☐'
                             end
      end

      
if stage == 'プロセスFMEA' || stage == 'プロセス故障モード影響解析（PFMEA）'
  @pfmea_yotei = pro.deadline_at.strftime('%y/%m/%d')
  @pfmea_kanryou = pro.end_at.strftime('%y/%m/%d')
  
  if pro.documents.attached?
    begin
      # 変数の設定
      partnumber = pro.partnumber # ここには実際の値を設定してください
      # パスとファイル名のパターンを作成（プロジェクトルートからの相対パス）
      pattern = Rails.root.join('db', 'documents', "*#{partnumber}*PFMEA*").to_s
      Rails.logger.info "PFMEA検索パス: #{pattern}"

      files = Dir.glob(pattern)
      files.each do |file|
        begin
          workbook = case File.extname(file).downcase
                    when '.xlsx'
                      Roo::Excelx.new(file)
                    when '.xls'
                      Roo::Excel.new(file)
                    else
                      next
                    end

          worksheet = workbook.sheet(0)
          @pfmea_check = '☑'
          #@pfmea_person_in_charge = worksheet.cell(6, 13)
          cell_value = worksheet.cell(6, 13)
          Rails.logger.info "PFMEA担当者セル(M6)の値: #{cell_value.inspect}"
          @pfmea_person_in_charge = cell_value
          
          Rails.logger.info "PFMEA処理中"
          Rails.logger.info "品番: #{partnumber}"
          Rails.logger.info "担当者: \#{?pfmea_person_in_charge}"
          
        rescue StandardError => e
          Rails.logger.error "PFMEAファイル(#{file})の処理中にエラーが発生: #{e.message}"
          Rails.logger.error e.backtrace.join("\n")
        end
      end
    rescue StandardError => e
      Rails.logger.error "PFMEA処理全体でエラーが発生: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")
    end
  end
  
  # ファイルが添付されていない、またはエラーが発生した場合のデフォルト値
  @pfmea_check ||= '☐'
end

      if stage == 'DR会議議事録_金型設計'
        @dr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @dr_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*D.R会議議事録*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break

            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得

            # @dr_kanagata_shiteki = worksheet.cell(12, 1).nil? ? "" : worksheet.cell(12, 1).to_s + worksheet.cell(13, 1).to_s
            # @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s}.compact.join("\n")
            # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
            # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
            # 以下のように変更します：
            
            @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_shochi = (12..28).map { |row| worksheet.cell(row, 6)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_try_kekka = (12..28).map { |row| worksheet.cell(row, 11)&.to_s }.compact.reject(&:empty?).join("\n")
          end

          @dr_check = '☑'
        else
          @dr_check = '☐'
        end
      end

      if stage == '測定システム解析（MSA)' # GRR
        @grr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @grr_kanryou = pro.end_at.strftime('%y/%m/%d')

        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*ゲージR&R*#{partnumber}*"
          Rails.logger.info "Path= #{pattern}"
          files = Dir.glob(pattern)
          @grr_count = files.size

          if @insert_rows_to_excel_template_msa == true # 初回のファイルのみサブルーチン処理
            insert_rows_to_excel_template_msa # ファイルの数だけ行を挿入するサブルーチン処理
          end

          # 各記号の初期化
          @grr = 0
          @ndc = 0

          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            if file.end_with?('.xlsx')
              workbook = Roo::Excelx.new(file)
            elsif file.end_with?('.xls')
              workbook = Roo::Excel.new(file)
            else
              raise 'Unsupported file format'
            end

            worksheet = workbook.sheet(0)

            @debagtest = ''
            # if worksheet.cell(4, 24) != nil

            instance_variable_set("@grr_kanryou_#{i + 1}", worksheet.cell(2, 8))
            instance_variable_set("@grr_yotei_#{i + 1}", worksheet.cell(2, 8))
            instance_variable_set("@grr_person_in_charge_#{i + 1}", worksheet.cell(36, 9))
            instance_variable_set("@grr_approved_#{i + 1}", worksheet.cell(36, 9))

            # end
            instance_variable_set("@grr_no_#{i + 1}", worksheet.cell(4, 2).to_s)

            instance_variable_set("@grr_#{i + 1}", worksheet.cell(23, 8).round(2))
            instance_variable_set("@ndc_#{i + 1}", worksheet.cell(31, 8).round(2))

            if worksheet.cell(23, 8) <= 10
              instance_variable_set("@grr_result_#{i + 1}", '合格')
            elsif worksheet.cell(23, 8) > 10 && worksheet.cell(23, 8) < 30
              instance_variable_set("@grr_result_#{i + 1}", '十分ではないが合格')
            else
              instance_variable_set("@grr_result_#{i + 1}", '不合格')
            end

            if worksheet.cell(31, 8) >= 5
              instance_variable_set("@ndc_result_#{i + 1}", '合格')
            else
              instance_variable_set("@ndc_result_#{i + 1}", '不合格')
            end
          end

          @grr_check = '☑'
        else
          @grr_check = '☐'

        end
        Rails.logger.info "@grr_person_in_charge_1= #{@grr_person_in_charge_1}" # 追加
        Rails.logger.info "@grr_result_1= #{@grr_result_1}"  # 追加
        Rails.logger.info "@ndc_result_1= #{@ndc_result_1}"  # 追加

        Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

      end

      if stage == '測定システム解析（MSA)' # クロスタブ
        @msa_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @msa_kanryou = pro.end_at.strftime('%y/%m/%d')

        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*計数値MSA報告書*"
          Rails.logger.info "Path= #{pattern}"
          files = Dir.glob(pattern)
          @msa_crosstab_count = files.size

          if @insert_rows_to_excel_template == true # 初回のファイルのみサブルーチン処理
            insert_rows_to_excel_template # ファイルの数だけ行を挿入するサブルーチン処理
          end

          # 各記号のカウントを初期化
          @maru_count = 0
          @batsu_count = 0
          @sankaku_count = 0
          @oomaru_count = 0

          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            workbook = Roo::Excelx.new(file)
            worksheet = workbook.sheet(0)

            @debagtest = ''
            # if worksheet.cell(4, 24) != nil

            instance_variable_set("@msa_crosstab_kanryou_#{i + 1}", worksheet.cell(4, 24))
            instance_variable_set("@msa_crosstab_recorder_#{i + 1}", worksheet.cell(6, 24))
            instance_variable_set("@msa_crosstab_person_in_charge_#{i + 1}", worksheet.cell(120, 29))
            instance_variable_set("@msa_crosstab_approved_#{i + 1}", worksheet.cell(120, 27))
            @debagtest = worksheet.cell(76, 29)
            Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加
            Rails.logger.info "i= #{i}" # 追加

            # end

            instance_variable_set("@inspector_name_a_#{i + 1}", worksheet.cell(8, 10))
            instance_variable_set("@inspector_name_b_#{i + 1}", worksheet.cell(8, 16))
            instance_variable_set("@inspector_name_c_#{i + 1}", worksheet.cell(8, 22))
            instance_variable_set("@inspector_a_result_#{i + 1}", worksheet.cell(131, 7))
            instance_variable_set("@inspector_b_result_#{i + 1}", worksheet.cell(131, 11))
            instance_variable_set("@inspector_c_result_#{i + 1}", worksheet.cell(131, 15))
          end

          @msa_crosstab_check = '☑'
        else
          @msa_crosstab_check = '☐'
          @msa_crosstab_count = 0
        end
        Rails.logger.info "@msa_crosstab_person_in_charge_0= #{@msa_crosstab_person_in_charge_0}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_1= #{@msa_crosstab_person_in_charge_1}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_2= #{@msa_crosstab_person_in_charge_2}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_3= #{@msa_crosstab_person_in_charge_3}"  # 追加
        Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

      end

      if stage == '寸法測定結果' # 型検
        @kataken_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @kataken_kanryou = pro.end_at.strftime('%y/%m/%d')

        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*検定報告書*"
          Rails.logger.info "Path= #{pattern}"

          files = Dir.glob(pattern)
          files.each do |file|
            workbook = nil
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file)
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file)
            else
              break
            end

            # シートの名前が"data"または"データ"を含むかどうかを確認
            matching_sheets = workbook.sheets.select do |name|
              name.downcase.include?('data') || name.include?('データ')
            end

            if matching_sheets.any?
              worksheet = workbook.sheet(matching_sheets.first)

              @kataken_person_in_charge = worksheet.cell(50, 71)
              @cpk_manager = worksheet.cell(50, 76)

              @kataken_kanryou = worksheet.cell(3, 27) if worksheet.cell(3, 27) != nil

              @kataken_cpk_OK = 0
              @kataken_cpk_NG = 0
              (1..200).each do |row|
                next unless worksheet.cell(row, 2) == 'Cpk' # B列はインデックス2

                (3..30).each do |col| # C列からAD列はインデックス3から30
                  raw_value = worksheet.cell(row, col)
                  next unless raw_value.is_a?(Numeric) # 数値の場合のみ処理を行う

                  value = raw_value.to_f
                  if value >= 1.67
                    @kataken_cpk_OK += 1
                  else
                    @kataken_cpk_NG += 1
                  end
                end
              end

              @kataken_spec_OK = 0
              @kataken_spec_NG = 0
              (1..200).each do |row|
                next unless worksheet.cell(row, 2) == 'Spec' # B列はインデックス2

                (3..30).each do |col| # C列からAD列はインデックス3から30
                  value = worksheet.cell(row, col)
                  if value == 'OK'
                    @kataken_spec_OK += 1
                  elsif value == 'NG'
                    @kataken_spec_NG += 1
                  end
                end
              end

              @kataken_spec_result = @kataken_spec_NG.zero? ? '合格' : '不合格'
              @kataken_cpk_result = @kataken_cpk_NG.zero? ? '合格' : '不合格'
            else
              @kataken_spec_result = 'データシート無し'
              @kataken_cpk_result = 'データシート無し'
              next # 次のファイルに移動
            end
          end

          @kataken_check = '☑'
        else
          @kataken_check = '☐'
        end
      end

      if stage == '初期工程調査結果'
        @cpk_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @cpk_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*工程能力(Ppk)調査表*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得
            @cpk_person_in_charge = worksheet.cell(50, 71)
            @cpk_manager = worksheet.cell(50, 76)

            def cell_address_to_position(cell_address)
              col = cell_address.gsub(/\d/, '')
              row = cell_address.gsub(/\D/, '').to_i

              col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
              [row, col_index]
            end

            satisfied = '工程能力は満足している'
            not_satisfied = '工程能力は不足している'

            # チェックするセルの位置
            check_addresses = %w[E N W AF AO AX BG BP BY].map { |col| "#{col}44" }

            # 初期値
            satisfied_count = 0
            not_satisfied_count = 0

            # すべてのシートをループ
            workbook.sheets.each do |sheet_name|
              worksheet = workbook.sheet(sheet_name)

              check_addresses.each do |cell_address|
                row, col = cell_address_to_position(cell_address)
                cell_value = worksheet.cell(row, col)

                satisfied_count += 1 if cell_value == satisfied
                not_satisfied_count += 1 if cell_value == not_satisfied
              end
            end

            # 結果の設定
            @cpk_result = if not_satisfied_count.positive?
                            not_satisfied
                          elsif satisfied_count.positive?
                            satisfied
                          else
                            '結果なし' # この行は必要に応じて変更または削除してください
                          end
            @cpk_satisfied_count = satisfied_count
            @cpk_not_satisfied_count = not_satisfied_count

            @cpk_person_in_charge = worksheet.cell(50, 76) # 担当者名

            if worksheet.cell(3, 59) != nil
              @cpk_yotei = worksheet.cell(3, 59)
              @cpk_kanryou = worksheet.cell(3, 59)
            end
          end
          @cpk_check = '☑'
        else
          @cpk_check = '☐'
        end
      end

      if stage == '試作製造指示書_営業'
        @shisaku_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @shisaku_kanryou = pro.end_at.strftime('%y/%m/%d')
      end

      if stage == '金型製造指示書_営業'
        @kanagata_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @kanagata_kanryou = pro.end_at.strftime('%y/%m/%d')
      end

      if stage == '設計計画書_金型設計'
        @plan_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @plan_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*設計計画書*"
          # pattern = "/myapp/db/documents/NT2394-P43_PM81EB_設計計画書.xls"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得
            @plan_designer = worksheet.cell(4, 9)
            @plan_manager = worksheet.cell(5, 9)
            @plan_customer = worksheet.cell(6, 3)
            @plan_risk = worksheet.cell(41, 4).nil? ? '' : worksheet.cell(41, 4).to_s + worksheet.cell(42, 4).to_s
            @plan_opportunity = if worksheet.cell(43,
                                                  4).nil?
                                  ''
                                else
                                  worksheet.cell(43, 4).to_s + worksheet.cell(44, 4).to_s
                                end

            if worksheet.cell(10, 4) != nil
              @plan_yotei = worksheet.cell(11, 4)
              @plan_kanryou = worksheet.cell(11, 6)
            end
          end
        end
      end

      if stage == 'DR構想検討会議議事録_生産技術'
        @dr_setsubi_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @dr_setsubi_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*DR構想検討会議議事録*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)

          @dr_setsubi_count = files.size # 追加　ファイルの数カウントし、何行挿入するか決定する

          if @insert_rows_to_excel_template_dr_setsubi == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
            insert_rows_to_excel_template_dr_setsubi # セルに必要な行数だけ行を挿入するサブルーチン
          end

          # 各ファイルに対して処理を行う
          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得
            # @dr_setsubi_designer = worksheet.cell(2, 17)
            # @dr_setsubi_manager = worksheet.cell(2, 16)
            # @dr_setsubi_equipment_name = worksheet.cell(5, 11) #K5
            # @dr_setsubi_shiteki = (11..25).map { |row| worksheet.cell(row, 1)&.to_s}.compact.join("\n")

            instance_variable_set("@dr_setsubi_name_#{i + 1}", worksheet.cell(5, 11))

            instance_variable_set("@dr_setsubi_designer_#{i + 1}", worksheet.cell(2, 17))
            instance_variable_set("@dr_setsubi_manager_#{i + 1}", worksheet.cell(2, 16))
            instance_variable_set("@dr_setsubi_equipment_name_#{i + 1}", worksheet.cell(5, 11))
            instance_variable_set("@dr_setsubi_yotei_#{i + 1}", convert_excel_date(worksheet.cell(5, 15)))
            instance_variable_set("@dr_setsubi_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(5, 15)))
            # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
            # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
            # 以下のように変更します：
            instance_variable_set("@dr_setsubi_shiteki_#{i + 1}",
                                  (11..25).map { |row| worksheet.cell(row, 1)&.to_s }
                                  .compact
                                  .reject(&:empty?)
                                  .join("\n"))

            # if worksheet.cell(5, 15) != nil
            #  @dr_setsubi_yotei  =worksheet.cell(5,15)
            #  @dr_setsubi_kanryou=worksheet.cell(5,15)
            # end
          end
          @dr_setsubi_check = '☑'
        else
          @dr_setsubi_check = '☐'
        end
      end

      if stage == '進捗管理票_生産技術'
        @dr_seigi_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @dr_seigi_plan_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*進捗管理票*"
          # pattern = "/myapp/db/documents/NT2394-P43_PM81EB_設計計画書.xls"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)

          @progress_management_count = files.size # 追加　ファイルの数カウントし、何行挿入するか決定する

          if @insert_rows_to_excel_template_progress_management == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
            insert_rows_to_excel_template_progress_management # セルに必要な行数だけ行を挿入するサブルーチン
          end

          # 各ファイルに対して処理を行う
          # files.each do |file|
          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # すみません、混乱を招いてしまったようで。Roo gemはExcelの日付をシリアル日付として読み込む場合があります。
            # Excelでは、日付は1900年1月1日からの日数として保存されます。
            # したがって、数値をRubyのDateオブジェクトに変換するために、Excelの日付のオフセット（1900年1月1日から数えた日数）
            # を使用する必要があります。
            # 次の関数は、Excelのシリアル日付を日付文字列に変換します：

            # def convert_excel_date(serial_date)
            #  # Excelの日付は1900年1月1日から数えた日数として保存されている
            #  base_date = Date.new(1899,12,30)
            #  # シリアル日付を日付に変換
            #  date = base_date + serial_date.to_i
            #  # 1899年12月30日の場合、"-"を返す
            #  return "-" if date == base_date
            #  # 日付を文字列に変換
            #  date.strftime('%Y/%m/%d')
            # end

            instance_variable_set("@progress_management_seigi_equipment_name_#{i + 1}", worksheet.cell(3, 4)) # F列とおもったらD列だった。。

            # @progress_management_seigi_design_name = worksheet.cell(14, 8)           #H13 設計担当者名
            # @progress_management_seigi_design_yotei = convert_excel_date(worksheet.cell(12, 6)) #F12 設計予定日
            # @progress_management_seigi_design_kanryou = convert_excel_date(worksheet.cell(12, 7)) #G12 設計完了日

            instance_variable_set("@progress_management_seigi_design_name_#{i + 1}", worksheet.cell(14, 8))
            instance_variable_set("@progress_management_seigi_design_yotei_#{i + 1}",
                                  convert_excel_date(worksheet.cell(12, 6)))
            instance_variable_set("@progress_management_seigi_design_kanryou_#{i + 1}",
                                  convert_excel_date(worksheet.cell(12, 7)))

            # @progress_management_seigi_assembly_name = worksheet.cell(27, 8)         #H27 組立担当者名
            # @progress_management_seigi_assembly_yotei = convert_excel_date(worksheet.cell(26, 6)) #F26 組立予定日
            # @progress_management_seigi_assembly_kanryou = convert_excel_date(worksheet.cell(26, 7)) #G26 組立完了日

            instance_variable_set("@progress_management_seigi_assembly_name_#{i + 1}", worksheet.cell(27, 8))
            instance_variable_set("@progress_management_seigi_assembly_yotei_#{i + 1}",
                                  convert_excel_date(worksheet.cell(26, 6)))
            instance_variable_set("@progress_management_seigi_assembly_kanryou_#{i + 1}",
                                  convert_excel_date(worksheet.cell(26, 7)))

            # @progress_management_seigi_wiring_name = worksheet.cell(30, 8)           #H30 配線担当者名
            # @progress_management_seigi_wiring_yotei = convert_excel_date(worksheet.cell(29, 6)) #F29 配線予定日
            # @progress_management_seigi_wiring_kanryou = convert_excel_date(worksheet.cell(29, 7)) #G29 配線完了日

            instance_variable_set("@progress_management_seigi_wiring_name_#{i + 1}", worksheet.cell(30, 8))
            instance_variable_set("@progress_management_seigi_wiring_yotei_#{i + 1}",
                                  convert_excel_date(worksheet.cell(29, 6)))
            instance_variable_set("@progress_management_seigi_wiring_kanryou_#{i + 1}",
                                  convert_excel_date(worksheet.cell(29, 7)))

            # @progress_management_seigi_program_name = worksheet.cell(34, 8)          #H34 プログラム担当者名
            # @progress_management_seigi_program_yotei = convert_excel_date(worksheet.cell(33, 6)) #F33 プログラム予定日
            # @progress_management_seigi_program_kanryou = convert_excel_date(worksheet.cell(33, 7)) #G33 プログラム完了日

            instance_variable_set("@progress_management_seigi_program_name_#{i + 1}", worksheet.cell(34, 8))
            instance_variable_set("@progress_management_seigi_program_yotei_#{i + 1}",
                                  convert_excel_date(worksheet.cell(33, 6)))
            instance_variable_set("@progress_management_seigi_program_kanryou_#{i + 1}",
                                  convert_excel_date(worksheet.cell(33, 7)))

            if worksheet.cell(10, 4) != nil
              @dr_seigi_yotei = worksheet.cell(33, 6) # F33　プログラム予定日
              @dr_seigi_kanryou = worksheet.cell(33, 7) # G33 プログラム完了日
            end
          end
        end
      end

      if stage == '初期流動検査記録'
        @shoki_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @shoki_kanryou = pro.end_at.strftime('%y/%m/%d')
        @shoki_check = '☑'
        @shoki_person_in_charge = '石栗'
      end

      if stage == '材料仕様書'
        @material_specification_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @material_specification_kanryou = pro.end_at.strftime('%y/%m/%d')
        @material_specification_check = '☑'
      end

      if stage == 'プロセス指示書'
        @wi_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @wi_kanryou = pro.end_at.strftime('%y/%m/%d')
      end
    end

    # すぐに終了するためには、ループの外側でも終了する必要があります。
    # Rubyでは、catchとthrowを使用して、複数のネストされたループからの脱出を行うことができます。
    # 以下のようにコードを修正しました：
    # catchブロックを最外部に追加します。
    # @partnumberが見つかった場合、throw :foundでcatchブロックを終了させます。
    # この修正により、@partnumberが見つかった時点で、すべてのループを終了します。

    catch :found do
      @all_products.each do |all|
        stage = @dropdownlist[all.stage.to_i]
        next unless stage == '金型製作記録'

        Rails.logger.info '金型製作記録(添付資料確認前)'
        next unless all.documents.attached?

        pattern = '/myapp/db/documents/**/*.{xls,xlsx}'
        Rails.logger.info "Path= #{pattern}"
        # ディレクトリ内のExcelファイルを走査
        Dir.glob(pattern) do |file|
          # '金型製作記録'を含むファイルだけを対象に
          next unless file.include?('金型製作記録')

          Rails.logger.info '金型製作記録(添付資料確認後)'
          # ファイル形式に応じて適切なRooクラスを使用
          workbook = case File.extname(file)
                     when '.xlsx'
                       Roo::Excelx.new(file)
                     when '.xls'
                       Roo::Excel.new(file)
                     end
          workbook.sheets.each do |sheet|
            worksheet = workbook.sheet(sheet)
            # 最終行がnilの場合は、このシートの処理をスキップ
            next if worksheet.last_row.nil?

            # 各行を走査
            (1..worksheet.last_row).each do |i|
              row = worksheet.row(i)
              # E列がpartnumberと一致する場合、L列の値を@dieset_personに代入
              next unless row[4] == @partnumber

              @dieset_person = row[11]
              @kanagata_yotei        = row[9]
              @kanagata_kanryou      = row[10]
              @kanagata_katagouzou   = row[8]
              @kanagata_remark       = row[12]
              
              # @partnumber が見つかったので、ループを終了
              throw :found
            end
          end
        end
      end
    end


    #治具管理台帳の読み込み

    @all_products ||= []
    @dropdownlist ||= {}

    catch :found do
      @all_products.each do |all|
        begin
          stage = @dropdownlist[all.stage.to_i]
          next unless stage.present? && stage == '台帳'

          next unless all.documents&.attached?

          pattern = '/myapp/db/documents/**/*.{xls,xlsx}'
          Dir.glob(pattern) do |file|
            next unless file.include?('治具管理台帳')

            begin
              workbook = case File.extname(file)
                        when '.xlsx'
                          Roo::Excelx.new(file)
                        when '.xls'
                          Roo::Excel.new(file)
                        else
                          next
                        end

              worksheet = workbook.sheet(0)
              (6..100).each do |row_number|
                cell_value = worksheet.cell(row_number, 9)
                next unless cell_value.present?

                values = cell_value.include?(',') ? cell_value.split(',') : [cell_value]
                Rails.logger.info("Row #{row_number}: Processing values: #{values.inspect}")

                values.each do |value|
                  next unless value.strip == @partnumber

                  @jigu_kanribangou = worksheet.cell(row_number, 1)
                  @jigu_name = worksheet.cell(row_number, 2)
                  @jigu_produced_date = worksheet.cell(row_number, 5)
                  @jigu_seizou_dept = worksheet.cell(row_number, 6)
                  @jigu_start_useage_date = worksheet.cell(row_number, 7)                  
                  @jigu_tantou = worksheet.cell(row_number, 8)
                  @jigu_approved = worksheet.cell(row_number, 11)
                  throw :found
                end
              end
            rescue StandardError => e
              Rails.logger.error("Error processing file #{file}: #{e.message}")
            end
          end
        rescue StandardError => e
          Rails.logger.error("Error processing product #{all}: #{e.message}")
        end
      end
    end


  end

  def insert_rows_to_excel_template_msa
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_msa = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @grr_count >= 2
              @grr_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'GRR' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("品証（\#{?grr_person_in_charge_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?grr_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?grr_kanryou_#{i + 2}}")
      worksheet[row_number][14].change_contents("項番：\#{?grr_no_#{i + 2}} \n GRR値：\#{?grr_#{i + 2}}%、GRR結果：\#{?grr_result_#{i + 2}} \n ndc値：\#{?ndc_#{i + 2}}、ndc結果：\#{?ndc_result#{i + 2}}")

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @msa_crosstab_count >= 2
              @msa_crosstab_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'クロスタブ' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("品証（\#{?msa_crosstab_person_in_charge_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?msa_crosstab_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?msa_crosstab_kanryou_#{i + 2}}")
      worksheet[row_number][14].change_contents("\#{?inspector_name_a_#{i + 2}}：\#{?inspector_a_result_#{i + 2}}、\#{?inspector_name_b_#{i + 2}}：\#{?inspector_b_result_#{i + 2}}、\#{?inspector_name_c_#{i + 2}}：\#{?inspector_c_result_#{i + 2}}")

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template_dr_setsubi
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_dr_setsubi = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @dr_setsubi_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'デザインレビュー(設備)' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # @msa_crosstab_countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("生技（\#{?dr_setsubi_designer_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?dr_setsubi_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?dr_setsubi_kanryou_#{i + 2}}")
      # worksheet[row_number][14].change_contents("\#{?dr_setsubi_shiteki_#{i + 2}}")

      content = "設備名：\#{?dr_setsubi_name_#{i + 2}}\n\n\#{?dr_setsubi_shiteki_#{i + 2}}"
      worksheet[row_number][14].change_contents(content)

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template_progress_management
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_progress_management = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @progress_management_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == '設備設計' # D列を参照。
        insert_row_number = row + 4 # 挿入する行番号を取得(3行分下の行から挿入開始)
        break
      end
    end

    # @msa_crosstab_countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      # row_number = insert_row_number + i  # 正しい行番号を計算
      row_number = insert_row_number + (i * 4) # 正しい行番号を計算
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)

      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定

      worksheet[row_number][14].change_contents("設備名：\#{?progress_management_seigi_equipment_name_#{i + 2}}") # H13 設備名称

      # @progress_management_seigi_design_name = worksheet.cell(14, 8)           #H13 設計担当者名
      worksheet[row_number][7].change_contents("生技（\#{?progress_management_seigi_design_name_#{i + 2}}）") # H13 設計担当者名
      # @progress_management_seigi_design_yotei = convert_excel_date(worksheet.cell(12, 6)) #F12 設計予定日
      worksheet[row_number][10].change_contents("\#{?progress_management_seigi_design_yotei_#{i + 2}}")
      # @progress_management_seigi_design_kanryou = convert_excel_date(worksheet.cell(12, 7)) #G12 設計完了日
      worksheet[row_number][12].change_contents("\#{?progress_management_seigi_design_kanryou_#{i + 2}}")

      # @progress_management_seigi_assembly_name = worksheet.cell(27, 8)         #H27 組立担当者名
      worksheet[row_number + 1][7].change_contents("生技（\#{?progress_management_seigi_assembly_name_#{i + 2}}）") # H27 組立担当者名
      # @progress_management_seigi_assembly_yotei = convert_excel_date(worksheet.cell(26, 6)) #F26 組立予定日
      worksheet[row_number + 1][10].change_contents("\#{?progress_management_seigi_assembly_yotei_#{i + 2}}")
      # @progress_management_seigi_assembly_kanryou = convert_excel_date(worksheet.cell(26, 7)) #G26 組立完了日
      worksheet[row_number + 1][12].change_contents("\#{?progress_management_seigi_assembly_kanryou_#{i + 2}}")

      # @progress_management_seigi_wiring_name = worksheet.cell(30, 8)           #H30 配線担当者名
      worksheet[row_number + 2][7].change_contents("生技（\#{?progress_management_seigi_wiring_name_#{i + 2}}）") # H30 配線担当者名
      # @progress_management_seigi_wiring_yotei = convert_excel_date(worksheet.cell(29, 6)) #F29 配線予定日
      worksheet[row_number + 2][10].change_contents("\#{?progress_management_seigi_wiring_yotei_#{i + 2}}")
      # @progress_management_seigi_wiring_kanryou = convert_excel_date(worksheet.cell(29, 7)) #G29 配線完了日
      worksheet[row_number + 2][12].change_contents("\#{?progress_management_seigi_wiring_kanryou_#{i + 2}}")

      # @progress_management_seigi_program_name = worksheet.cell(34, 8)          #H34 プログラム担当者名
      worksheet[row_number + 3][7].change_contents("生技（\#{?progress_management_seigi_program_name_#{i + 2}}）") # H34 プログラム担当者名
      # @progress_management_seigi_program_yotei = convert_excel_date(worksheet.cell(33, 6)) #F33 プログラム予定日
      worksheet[row_number + 3][10].change_contents("\#{?progress_management_seigi_program_yotei_#{i + 2}}")
      # @progress_management_seigi_program_kanryou = convert_excel_date(worksheet.cell(33, 7)) #G33 プログラム完了日
      worksheet[row_number + 3][12].change_contents("\#{?progress_management_seigi_program_kanryou_#{i + 2}}")

      #    if worksheet.cell(10, 4) != nil
      #      @dr_seigi_yotei  =worksheet.cell(33, 6) #F33　プログラム予定日
      #      @dr_seigi_kanryou=worksheet.cell(33, 7) #G33 プログラム完了日
      #    end

      worksheet[row_number][3].change_contents('設備設計')
      worksheet[row_number + 1][3].change_contents('設備製作')
      worksheet[row_number + 1][5].change_contents('組立')
      worksheet[row_number + 2][5].change_contents('配線')
      worksheet[row_number + 3][5].change_contents('プログラム')

      worksheet.merge_cells(row_number, 3, row_number, 6)

      worksheet.merge_cells(row_number + 1, 3, row_number + 3, 4) # D列、E列を結合

      worksheet.merge_cells(row_number + 1, 5, row_number + 1, 6)
      worksheet.merge_cells(row_number + 2, 5, row_number + 2, 6)
      worksheet.merge_cells(row_number + 3, 5, row_number + 3, 6)

      worksheet.merge_cells(row_number, 14, row_number + 3, 23) # 設備名称のセルを結合

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)

      worksheet.merge_cells(row_number + 1, 7, row_number + 1, 9)
      worksheet.merge_cells(row_number + 1, 10, row_number + 1, 11)
      worksheet.merge_cells(row_number + 1, 12, row_number + 1, 13)

      worksheet.merge_cells(row_number + 2, 7, row_number + 2, 9)
      worksheet.merge_cells(row_number + 2, 10, row_number + 2, 11)
      worksheet.merge_cells(row_number + 2, 12, row_number + 2, 13)

      worksheet.merge_cells(row_number + 3, 7, row_number + 3, 9)
      worksheet.merge_cells(row_number + 3, 10, row_number + 3, 11)
      worksheet.merge_cells(row_number + 3, 12, row_number + 3, 13)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    # worksheet.merge_cells(insert_row_number-1, 3, insert_row_number+count-1, 6)

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  # すみません、混乱を招いてしまったようで。Roo gemはExcelの日付をシリアル日付として読み込む場合があります。
  # Excelでは、日付は1900年1月1日からの日数として保存されます。
  # したがって、数値をRubyのDateオブジェクトに変換するために、Excelの日付のオフセット（1900年1月1日から数えた日数）
  # を使用する必要があります。
  # 次の関数は、Excelのシリアル日付を日付文字列に変換します：

  def convert_excel_date(serial_date)
    # Excelの日付は1900年1月1日から数えた日数として保存されている
    base_date = Date.new(1899, 12, 30)
    # シリアル日付を日付に変換
    date = base_date + serial_date.to_i
    # 1899年12月30日の場合、"-"を返す
    return '-' if date == base_date

    # 日付を文字列に変換
    date.strftime('%Y/%m/%d')
  end

  #-------------------------------------------------------------------------------------------------
  def create_data_apqp_plan_report
    @datetime = Time.zone.now
    @partnumber = params[:partnumber]

    @apqp_plan_excel_template_initial = true # Excelテンプレートを初期値にする
    @apqp_plan_insert_rows_to_excel_template = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @apqp_plan_insert_rows_to_excel_template_dr_setsubi = true # 初回のファイルのみ挿入サブルーチンに飛ぶ
    @apqp_plan_insert_rows_to_excel_template_progress_management = true # 初回のファイルのみ挿入サブルーチンに飛ぶ

    @datetime = Time.zone.now
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
    @cp_check = '☐'
    @datou_check = '☐'
    @scr_check = '☐'
    @pfmea_check = '☐'
    @dr_check = '☐'
    @msa_check = '☐'
    @msa_crosstab_check = '☐'
    @msa_grr_check = '☐'
    @cpk_check = '☐'
    @shisaku_check = '☐'
    @kanagata_check = '☐'
    @dr_setsubi_check = '☐'
    @grr_check = '☐'
    @feasibility_check = '☐'
    @kataken_check = '☐'
    @psw_check = '☐'
    @special_check = '☐'
    @pf_check = '☐'
    @process_layout_check = '☐'
    @crosstab_check = '☐'
    @kataken_check = '☐'
    @inspection_fixtures_mold_check = '☐'
    @inspection_fixtures_stamping_check = '☐'

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= #{@partnumber}" # 追加
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= #{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= #{pro.stage}"
      Rails.logger.info "stage= #{stage}"

      if stage == '検査補助具'
        if pro.documents.attached?
          filename = pro.documents.first.filename.to_s
          if filename.include?("成形")
          @inspection_fixtures_mold_filename = filename
          @inspection_fixtures_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
          @inspection_fixtures_mold_kanryou = pro.end_at.strftime('%y/%m/%d')  
          @inspection_fixtures_mold_check = '☑'
          else
          @inspection_fixtures_stamping_filename = filename
          @inspection_fixtures_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
          @inspection_fixtures_stamping_kanryou = pro.end_at.strftime('%y/%m/%d')  
          @inspection_fixtures_stamping_check = '☑'
          end
        else
          @inspection_fixtures_mold_check = '☐'
          @inspection_fixtures_stamping_check = '☐'
        end
      end

      if stage == '量産コントロールプラン' || stage == '試作コントロールプラン' || stage == "先行生産（Pre-launch,量産試作）コントロールプラン"
        @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @cp_check = '☑'
          @cp_filename = pro.documents.first.filename.to_s
        else
          #@cp_check = '☐'
        end
      end

      if stage == '測定システム解析（MSA)' # GRR
        @grr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @grr_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @grr_check = '☑'
          @grr_filename = pro.documents.first.filename.to_s
        else
          @grr_check = '☐'
        end
      end

      if stage == '有資格試験所文書'
        @documented_information_of_qualified_laboratories_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @documented_information_of_qualified_laboratories_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @documented_information_of_qualified_laboratories_check = '☑'
          @documented_information_of_qualified_laboratories_filename = pro.documents.first.filename.to_s
        else
          @documented_information_of_qualified_laboratories_check = '☐'
        end
      end



      if stage == '妥当性確認記録_金型設計'
        @datou_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @datou_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @datou_check = '☑'
      
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*妥当性確認記録*"
          Rails.logger.info "Path= #{pattern}"
      
          files = Dir.glob(pattern)
          if files.empty?
            Rails.logger.info "該当するファイルが見つかりませんでした。"
          end
      
          files.each do |file|
            workbook = nil
            case File.extname(file)
            when '.xlsx'
              workbook = Roo::Excelx.new(file)
            when '.xls'
              workbook = Roo::Excel.new(file)
            else
              next # 次のファイルへ
            end
      
            begin
              # 最初のシートを取得
              worksheet = workbook.sheet(0)
      
              # セルの値を取得
              @datou_result = worksheet.cell(36, 24).presence || worksheet.cell(41, 13)
              @datou_person_in_charge = worksheet.cell(39, 22)
              @datou_kanryou = worksheet.cell(37, 6).presence || worksheet.cell(43, 4)
              @datou_filename = pro.documents.first.filename.to_s
              Rails.logger.info '妥当性確認'
              Rails.logger.info "@partnumber= #{@partnumber}"
              Rails.logger.info "@datou_result #{@datou_result}"
            rescue => e
              Rails.logger.error "ファイル処理中にエラーが発生しました: #{e.message}"
            end
          end
        else
          @datou_check = '☐'
          Rails.logger.info "添付ファイルがありません。"
        end
      end

      if stage == '製造実現可能性検討書'
        @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @feasibility_check = '☑'
          @feasibility_filename = pro.documents.first.filename.to_s
        else
          #@feasibility_check = '☐'
        end
      end






      #if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'
      #  @processflow_yotei = pro.deadline_at.strftime('%y/%m/%d')
      #  @processflow_kanryou = pro.end_at.strftime('%y/%m/%d')
      #  if pro.documents.attached?
      #    @processflow_check = '☑'
      #    @processflow_filename = pro.documents.first.filename.to_s
      #  else
      #    #@processflow_check = '☐'
      #  end
      #end

      


      if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'
        
        @processflow_check = if pro.documents.attached?
          '☑'
           
          begin
            # プレスファイルの確認
            press_file_found = false
            mold_file_found = false
            
            # 最初にプレスファイルを探す
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              if filename.include?('プロセスフロー') && filename.include?('プレス')
                press_file_found = true
                begin
                  temp_file = Tempfile.new(['temp', File.extname(filename)])
                  temp_file.binmode
                  temp_file.write(doc.download)
                  temp_file.rewind

                  workbook = case File.extname(filename).downcase
                            when '.xlsx' then Roo::Excelx.new(temp_file.path)
                            when '.xls'  then Roo::Excel.new(temp_file.path)
                            else
                              next
                            end

                  Rails.logger.info "=== ワークシート情報 ==="
                  Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                  
                  # 適切なシートを探す
                  target_sheet = nil
                  workbook.sheets.each do |sheet_name|
                    workbook.default_sheet = sheet_name
                    Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                    
                    # セル(2,21)とセル(2,22)の値を確認
                    cell_2_21 = workbook.cell(2, 21)
                    cell_2_22 = workbook.cell(2, 22)
                    
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                    
                    if cell_2_21.present? || cell_2_22.present?
                      target_sheet = sheet_name
                      Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                      break
                    end
                  end

                  unless target_sheet
                    Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                    next
                  end

                  workbook.default_sheet = target_sheet
                  Rails.logger.info "選択したシート: #{target_sheet}"
                  Rails.logger.info "最終行: #{workbook.last_row}"
                  Rails.logger.info "最終列: #{workbook.last_column}"

                  # セルの値を文字列として取得し、デバッグ情報を出力
                  @processflow_stamping_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_stamping_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_stamping_check = '☑'
                  @processflow_filename_stamping = pro.documents.first.filename.to_s

                  Rails.logger.info "=== セルの値確認 ==="
                  Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                  Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_stamping_person_in_charge.inspect}"
                  Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                  Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_stamping_dept.inspect}"

                  Rails.logger.info "プレス承認者: \#{?processflow_stamping_person_in_charge}"
                  Rails.logger.info "プレス部署: \#{?processflow_stamping_dept}"
                rescue StandardError => e
                  Rails.logger.error "プレスファイル処理エラー: #{e.message}"
                ensure
                  workbook&.close if defined?(workbook) && workbook
                  temp_file.close
                  temp_file.unlink
                end
                break
              end
            end

            # プレスファイルがない場合は成形ファイルを探す
            unless press_file_found
              pro.documents.each do |doc|
                filename = doc.filename.to_s
                if filename.include?('プロセスフロー') && filename.include?('成形')
                  mold_file_found = true
                  begin
                    temp_file = Tempfile.new(['temp', File.extname(filename)])
                    temp_file.binmode
                    temp_file.write(doc.download)
                    temp_file.rewind

                    workbook = case File.extname(filename).downcase
                              when '.xlsx' then Roo::Excelx.new(temp_file.path)
                              when '.xls'  then Roo::Excel.new(temp_file.path)
                              else
                                next
                              end

                    Rails.logger.info "=== ワークシート情報 ==="
                    Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                    
                    # 適切なシートを探す
                    target_sheet = nil
                    workbook.sheets.each do |sheet_name|
                      workbook.default_sheet = sheet_name
                      Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                      
                      # セル(2,21)とセル(2,22)の値を確認
                      cell_2_21 = workbook.cell(2, 21)
                      cell_2_22 = workbook.cell(2, 22)
                      
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                      
                      if cell_2_21.present? || cell_2_22.present?
                        target_sheet = sheet_name
                        Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                        break
                      end
                    end

                    unless target_sheet
                      Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                      next
                    end

                    workbook.default_sheet = target_sheet
                    Rails.logger.info "選択したシート: #{target_sheet}"
                    Rails.logger.info "最終行: #{workbook.last_row}"
                    Rails.logger.info "最終列: #{workbook.last_column}"

                    # セルの値を文字列として取得し、デバッグ情報を出力
                    @processflow_mold_person_in_charge = workbook.cell(2, 21).to_s.strip
                    @processflow_mold_dept = workbook.cell(4, 13).to_s.strip
                    @processflow_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
                    @processflow_mold_kanryou = pro.end_at.strftime('%y/%m/%d')
                    @processflow_mold_check = '☑'
                    @processflow_filename_mold = pro.documents.first.filename.to_s

                    Rails.logger.info "=== セルの値確認 ==="
                    Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                    Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_mold_person_in_charge.inspect}"
                    Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                    Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_mold_dept.inspect}"

                    Rails.logger.info "成形承認者: \#{?processflow_mold_person_in_charge}"
                  rescue StandardError => e
                    Rails.logger.error "成形ファイル処理エラー: #{e.message}"
                  ensure
                    workbook&.close if defined?(workbook) && workbook
                    temp_file.close
                    temp_file.unlink
                  end
                  break
                end
              end
            end

            # 営業、工程設計、検査のファイルは毎回確認
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              next unless filename.include?('プロセスフロー')

              begin
                temp_file = Tempfile.new(['temp', File.extname(filename)])
                temp_file.binmode
                temp_file.write(doc.download)
                temp_file.rewind

                workbook = case File.extname(filename).downcase
                          when '.xlsx' then Roo::Excelx.new(temp_file.path)
                          when '.xls'  then Roo::Excel.new(temp_file.path)
                          else
                            next
                          end

                Rails.logger.info "=== ワークシート情報 ==="
                Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                
                # 適切なシートを探す
                target_sheet = nil
                workbook.sheets.each do |sheet_name|
                  workbook.default_sheet = sheet_name
                  Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                  
                  # セル(2,21)とセル(2,22)の値を確認
                  cell_2_21 = workbook.cell(2, 21)
                  cell_2_22 = workbook.cell(2, 22)
                  
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                  
                  if cell_2_21.present? || cell_2_22.present?
                    target_sheet = sheet_name
                    Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                    break
                  end
                end

                unless target_sheet
                  Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                  next
                end

                workbook.default_sheet = target_sheet
                Rails.logger.info "選択したシート: #{target_sheet}"
                Rails.logger.info "最終行: #{workbook.last_row}"
                Rails.logger.info "最終列: #{workbook.last_column}"

                # セルの値を文字列として取得し、デバッグ情報を出力
                if filename.include?('営業')
                  @processflow_sales_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_sales_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_sales_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_sales_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_sales_check='☑'
                  @processflow_filename_sales = pro.documents.first.filename.to_s
                  Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
                elsif filename.include?('工程設計')
                  @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_design_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_design_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_design_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_design_check='☑'
                  @processflow_filename_design = pro.documents.first.filename.to_s
                  Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
                elsif filename.include?('検査')
                  @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_inspection_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_inspection_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_inspection_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_inspection_check='☑'
                  @processflow_filename_inspection = pro.documents.first.filename.to_s
                  Rails.logger.info "検査引渡し承認者: \#{?processflow_inspection_person_in_charge}"
                end
              rescue StandardError => e
                Rails.logger.error "その他ファイル処理エラー: #{e.message}"
              ensure
                workbook&.close if defined?(workbook) && workbook
                temp_file.close
                temp_file.unlink
              end
            end

          rescue StandardError => e
            Rails.logger.error "ファイル処理エラー: #{e.message}"
          end
        else
          '☐'
        end
      end

      














      if stage == '測定システム解析（MSA)' # クロスタブ
        @crosstab_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @crosstab_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @crosstab_check = '☑'
          @crosstab_filename = pro.documents.first.filename.to_s
        else
          #@crosstab_check = '☐'
        end
      end

      if stage == '部品提出保証書（PSW)'
        @psw_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @psw_kanryou = pro.end_at.strftime('%y/%m/%d')
        Rails.logger.info "@psw_yotei #{@psw_yotei}" # 追加
        if pro.documents.attached?
          @psw_check = '☑'
      
          # 変数の設定
          partnumber = pro.partnumber
          # 部品提出保証書の前にpartnumberがあるケース
          pattern1 = "/myapp/db/documents/*#{partnumber}部品提出保証書*"
          # 部品提出保証書の後にpartnumberがあるケース
          pattern2 = "/myapp/db/documents/*部品提出保証書*#{partnumber}*"

          # ログにパターンを出力
          Rails.logger.info "Pattern1= #{pattern1}"
          Rails.logger.info "Pattern2= #{pattern2}"
      
          # 両方のパターンにマッチするファイルを検索
          files = Dir.glob(pattern1) + Dir.glob(pattern2)
          files.each do |file|
            workbook = nil
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file)
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file)
            else
              break
            end
      
            # 最初のシートを取得
            worksheet = workbook.sheet(0)
      
            # X36のセルの値を取得
            (25..30).each do |row|
              if worksheet.cell(row, 2)&.to_s == '■'
                @psw_level = worksheet.cell(row, 3)&.to_s
                break # 一度見つかったらループを終了
              end
            end
          end # files.each do |file| の終了
        end # if pro.documents.attached? の終了
      end # if stage == '部品提出保証書（PSW)' の終了

      if stage == '寸法測定結果' # 型検
        @kataken_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @kataken_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @kataken_check = '☑'
          @kataken_filename = pro.documents.first.filename.to_s
        else
         #@kataken_check = '☐'
        end
      end

      if stage == 'プロセス故障モード影響解析（PFMEA）' ||   stage == 'プロセスFMEA'
        @pfmea_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @pfmea_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @pfmea_check = '☑'
          @pfmea_filename = pro.documents.first.filename.to_s
        else
          #@pfmea_check = '☐'
        end
      end

      if stage == '特性マトリクス'
        @special_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @special_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @special_check = '☑'
          @special_filename = pro.documents.first.filename.to_s
        else
          #special_check = '☐'
        end
      end

      if stage == '工程フロー図'
        @pf_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @pf_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @pf_check = '☑'
          @pf_filename = pro.documents.first.filename.to_s
        else
          @pf_check = '☐'
        end
      end


      if stage == 'フロアプランレイアウト'
        @floor_plan_layout_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @floor_plan_layout_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @floor_plan_layout_check = '☑'
          @floor_plan_layout_filename = pro.documents.first.filename.to_s
        else
          #@floor_plan_layout_check = '☐'
        end
      end

      #if stage == 'プロセスFMEA'
      #  @pfmea_yotei = pro.deadline_at.strftime('%y/%m/%d')
      #  @pfmea_kanryou = pro.end_at.strftime('%y/%m/%d')
      #  if pro.documents.attached?
      #    @pfmea_check = '☑'
      #    @pfmea_filename = pro.documents.first.filename.to_s
      #  else
      #    #@pfmea_check = '☐'
      #  end
      #end

      if stage == '部品提出保証書（PSW)'
        @psw_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @psw_kanryou = pro.end_at.strftime('%y/%m/%d')
        Rails.logger.info "@psw_yotei #{@psw_yotei}" # 追加
        if pro.documents.attached?
          @psw_check = '☑'

        # 変数の設定
        partnumber = pro.partnumber
        # 部品提出保証書の前にpartnumberがあるケース
        pattern1 = "/myapp/db/documents/*#{partnumber}*部品提出保証書*"
        # 部品提出保証書の後にpartnumberがあるケース
        pattern2 = "/myapp/db/documents/*部品提出保証書*#{partnumber}*"

        # ログにパターンを出力
        Rails.logger.info "Pattern1= #{pattern1}"
        Rails.logger.info "Pattern2= #{pattern2}"

        # 両方のパターンにマッチするファイルを検索
        files = Dir.glob(pattern1) + Dir.glob(pattern2)
          files.each do |file|
            workbook = nil
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file)
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file)
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # X36のセルの値を取得
            # RubyXLライブラリでExcelのセルを参照する際、行と列のインデックスは0から始まります。
            # したがって、1行1列目のセルは worksheet.cell(1, 1) としてアクセスされます。
            # したがって、セルX36を指定する場合:
            # 行番号: 36 - 1 = 35
            # 列番号: Xは24番目の列なので、24 - 1 = 23
            # 指定の範囲で各行をチェック
            (25..30).each do |row|
              if worksheet.cell(row, 2)&.to_s == '■'
                @psw_level = worksheet.cell(row, 3)&.to_s
                break # 一度見つかったらループを終了
              end
            end

            @psw_filename = pro.documents.first.filename.to_s
          end
        else
          #@psw_check = '☐'
        end
      end

      if stage == 'DR会議議事録_金型設計'
        @dr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @dr_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*D.R会議議事録*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break

            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得

            # @dr_kanagata_shiteki = worksheet.cell(12, 1).nil? ? "" : worksheet.cell(12, 1).to_s + worksheet.cell(13, 1).to_s
            # @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s}.compact.join("\n")
            # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
            # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
            # 以下のように変更します：
            @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_shochi = (12..28).map { |row| worksheet.cell(row, 6)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_try_kekka = (12..28).map { |row| worksheet.cell(row, 11)&.to_s }.compact.reject(&:empty?).join("\n")
          end

          @dr_check = '☑'
          @dr_check_filename = pro.documents.first.filename.to_s
        else
          #@dr_check = '☐'
        end
      end

      if stage == '初期工程調査結果'
        @cpk_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @cpk_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*工程能力(Ppk)調査表*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得
            @cpk_person_in_charge = worksheet.cell(50, 71)
            @cpk_manager = worksheet.cell(50, 76)

            def cell_address_to_position(cell_address)
              col = cell_address.gsub(/\d/, '')
              row = cell_address.gsub(/\D/, '').to_i

              col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
              [row, col_index]
            end

            satisfied = '工程能力は満足している'
            not_satisfied = '工程能力は不足している'

            # チェックするセルの位置
            check_addresses = %w[E N W AF AO AX BG BP BY].map { |col| "#{col}44" }

            # 初期値
            satisfied_count = 0
            not_satisfied_count = 0

            # すべてのシートをループ
            workbook.sheets.each do |sheet_name|
              worksheet = workbook.sheet(sheet_name)

              check_addresses.each do |cell_address|
                row, col = cell_address_to_position(cell_address)
                cell_value = worksheet.cell(row, col)

                satisfied_count += 1 if cell_value == satisfied
                not_satisfied_count += 1 if cell_value == not_satisfied
              end
            end

            # 結果の設定
            @cpk_result = if not_satisfied_count.positive?
                            not_satisfied
                          elsif satisfied_count.positive?
                            satisfied
                          else
                            '結果なし' # この行は必要に応じて変更または削除してください
                          end
            @cpk_satisfied_count = satisfied_count
            @cpk_not_satisfied_count = not_satisfied_count

            @cpk_person_in_charge = worksheet.cell(50, 76) # 担当者名

            if worksheet.cell(3, 59) != nil
              @cpk_yotei = worksheet.cell(3, 59)
              @cpk_kanryou = worksheet.cell(3, 59)
            end
          end
          @cpk_check = '☑'
          @cpk_check_filename = pro.documents.first.filename.to_s
        else
          #@cpk_check = '☐'
        end
      end

      if stage == '試作製造指示書_営業'
        @shisaku_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @shisaku_kanryou = pro.end_at.strftime('%y/%m/%d')
      end

      if stage == '金型製造指示書_営業'
        @kanagata_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @kanagata_kanryou = pro.end_at.strftime('%y/%m/%d')
      end

      def format_date_from_cells(year_cell, month_day_cell)
        year = if year_cell.is_a?(Date)
                 year_cell.strftime('%Y')
               else
                 year_cell.slice(0, 4)
               end
        "#{year}/#{month_day_cell}"
      end

      if stage == '設計計画書_金型設計'
        @plan_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @plan_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*設計計画書*"
          Rails.logger.info "Path= #{pattern}"
          files = Dir.glob(pattern)
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              next # 不明なファイル形式の場合は次のファイルへ
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            next unless worksheet.cell(10, 4)

            year_cell = worksheet.cell(3, 9)

            @plan_customer = worksheet.cell(6, 8)

            @plan_yotei = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
            @plan_kanryou = format_date_from_cells(year_cell,  worksheet.cell(11, 4).to_s)
            @actual_yotei = format_date_from_cells(year_cell,  worksheet.cell(11, 4).to_s)
            @actual_kanryou = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)

            @plan_design_start = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
            @plan_design_end = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
            @actual_design_start = format_date_from_cells(year_cell, worksheet.cell(10, 6).to_s)
            @actual_design_end = format_date_from_cells(year_cell, worksheet.cell(11, 6).to_s)

            @plan_datou_start = format_date_from_cells(year_cell, worksheet.cell(17, 4).to_s)
            @plan_datou_end = format_date_from_cells(year_cell, worksheet.cell(17, 4).to_s)
            @actual_datou_start = format_date_from_cells(year_cell, worksheet.cell(17, 6).to_s)
            @actual_datou_end = format_date_from_cells(year_cell, worksheet.cell(17, 6).to_s)
          end
        end
      end

      if stage == '顧客要求事項検討会議事録_営業'
        @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @scr_check = '☑'

          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*顧客要求検討会議事録*#{partnumber}*"
          Rails.logger.info "Path= #{pattern}"

          files = Dir.glob(pattern)
          files.each do |file|
            workbook = nil
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file)
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file)
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # X36のセルの値を取得
            # RubyXLライブラリでExcelのセルを参照する際、行と列のインデックスは0から始まります。
            # したがって、1行1列目のセルは worksheet.cell(1, 1) としてアクセスされます。
            # したがって、セルX36を指定する場合:
            # 行番号: 36 - 1 = 35
            # 列番号: Xは24番目の列なので、24 - 1 = 23
            @plan_scr_start = worksheet.cell(5, 6)
            @plan_scr_end = worksheet.cell(5, 6)
            @actual_scr_start = worksheet.cell(5, 6)
            @actual_scr_end = worksheet.cell(5, 6)
          end
        else
          #@scr_check = '☐'
        end
      end

      next unless stage == 'DR構想検討会議議事録_生産技術'

      @dr_setsubi_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @dr_setsubi_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*DR構想検討会議議事録*"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)

        @dr_setsubi_count = files.size # 追加　ファイルの数カウントし、何行挿入するか決定する

        if @apqp_plan_insert_rows_to_excel_template_dr_setsubi == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
          apqp_plan_insert_rows_to_excel_template_dr_setsubi # セルに必要な行数だけ行を挿入するサブルーチン
        end

        # 各ファイルに対して処理を行う
        files.each_with_index do |file, i| # with_indexでインデックスiを追加
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break
          end

          # 最初のシートを取得
          workbook.sheet(0)

          # i4のセルの値を取得

          # ファイル名の取得
          filename = File.basename(file)

          # インスタンス変数にファイル名を設定
          instance_variable_set("@dr_setsubi_filename_#{i + 1}", filename)

          # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
          # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
          # 以下のように変更します：
          # instance_variable_set("@dr_setsubi_shiteki_#{i + 1}",
          # (11..25).map { |row| worksheet.cell(row, 1)&.to_s }
          # .compact
          # .reject(&:empty?)
          # .join("\n"))

          # if worksheet.cell(5, 15) != nil
          #  @dr_setsubi_yotei  =worksheet.cell(5,15)
          #  @dr_setsubi_kanryou=worksheet.cell(5,15)
          # end
        end
        @dr_setsubi_check = '☑'
      else
        @dr_setsubi_check = '☐'
      end
    end
  end

  def apqp_plan_insert_rows_to_excel_template_dr_setsubi
    if @apqp_plan_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_plan_report.xlsx')
      @apqp_plan_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_plan_report_modified.xlsx')
    end
    @apqp_plan_insert_rows_to_excel_template_dr_setsubi = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @dr_setsubi_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (20..30).each do |row|
      next unless worksheet[row][5].value == 'デザインレビュー(設備設計)' # D列を参照。

      insert_row_number = row + 1 # 挿入する行番号を取得

      break
    end

    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加
    Rails.logger.info "count= #{count}" # 追加

    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)
      Rails.logger.info "row_number= #{row_number}" # 追加
    
      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定
      worksheet[row_number][12].change_contents("報告書名：\#{?dr_setsubi_filename_#{i + 2}}")
    
      # 横方向の結合のみループ内で実行
      worksheet.merge_cells(row_number, 12, row_number, 19)
    end
    
    # ループ終了後に縦方向の結合を実行
    if count > 0
      # 開始行は最初に挿入した行、終了行は最後に挿入した行
      start_row = insert_row_number
      end_row = insert_row_number + count - 1
      
      # 5列目から11列目の結合
      worksheet.merge_cells(start_row-1, 5, end_row, 11)
      # 4列目の結合
      worksheet.merge_cells(start_row-1, 4, end_row, 4)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    # worksheet.merge_cells(insert_row_number-1, 3, insert_row_number+count-1, 6)

    workbook.write('lib/excel_templates/apqp_plan_report_modified.xlsx')
  end

  #   end

  #  end

  def create_data_apqp_approved_report
    @datetime = Time.zone.now
    @partnumber = params[:partnumber]

    @apqp_approved_report_excel_template_initial = true # Excelテンプレートを初期値にする
    @apqp_approved_report_insert_rows_to_excel_template = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @apqp_approved_report_insert_rows_to_excel_template_msa = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @apqp_approved_report_insert_rows_to_excel_template_dr_setsubi = true # 初回のファイルのみ挿入サブルーチンに飛ぶ
    @apqp_approved_report_insert_rows_to_excel_template_progress_management = true # 初回のファイルのみ挿入サブルーチンに飛ぶ

    @datetime = Time.zone.now
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
    @cp_check = '☐'
    @datou_check = '☐'
    @scr_check = '☐'
    @pfmea_check = '☐'
    @dr_check = '☐'
    @msa_check = '☐'
    @msa_crosstab_check = '☐'
    @msa_grr_check = '☐'
    @cpk_check = '☐'
    @shisaku_check = '☐'
    @kanagata_check = '☐'
    @dr_setsubi_check = '☐'
    @grr_check = '☐'
    @feasibility_check = '☐'
    @kataken_check = '☐'
    @psw_check = '☐'
    @pf_sales_check = '☐'
    @pf_production_check = '☐'
    @pf_inspectoin_check = '☐'
    @pf_release_check = '☐'
    @pf_process_design_check = '☐'
    @pf_check = '☐'
    @process_layout_check = '☐'
    @processflow_inspection_ckeck = '☐'
    @processflow_mold_ckeck = '☐'
    @inspection_fixtures_mold_check = '☐'
    @inspection_fixtures_stamping_check = '☐'
    @processflow_design_check = '☐'
    @processflow_stamping_check = '☐'
    @processflow_inspection_check = '☐'
    @processflow_mold_check = '☐'
    @processflow_sales_check = '☐'
    @processflow_design_check = '☐'
    


#    catch :found do
#      @all_products.each do |all|
#        stage = @dropdownlist[all.stage.to_i]
#        Rails.logger.info "Stage: #{stage}, all.stage: #{all.stage.to_i},Documents attached: #{all.documents.attached?}"

#        Rails.logger.info "Current stage: #{stage}"
#        case stage
#        when '営業プロセスフロー'
#          Rails.logger.info 'Inside the condition for 営業プロセスフロー'
#          @pf_sales_check = all.documents.attached? ? '☑' : '☐'
#          Rails.logger.info "@pf_sales_check: #{@pf_sales_check}"
#        when '製造工程設計プロセスフロー'
#          @pf_process_design_check = all.documents.attached? ? '☑' : '☐'

#        when '製造プロセスフロー'
#          @pf_production_check = all.documents.attached? ? '☑' : '☐'

#        when '製品検査プロセスフロー'
#          @pf_inspectoin_check = all.documents.attached? ? '☑' : '☐'

#        when '引渡しプロセスフロー'
#          @pf_release_check = all.documents.attached? ? '☑' : '☐'

#        end

#        if @pf_sales_check && @pf_process_design_check && @pf_production_check && @pf_inspectoin_check && @pf_release_check
#          Rails.logger.info 'All checks completed.'
#          # throw :found
#        end
#      end
#    end

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= #{@partnumber}" # 追加
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= #{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= #{pro.stage}"




      if %w[プレス作業標準書].include?(stage)
        @stamping_standard_procedure_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @stamping_standard_procedure_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @stamping_standard_procedure_check = '☑'
          @stamping_standard_procedure_filename = pro.documents.first.filename.to_s
        else
          @stamping_standard_procedure_check = '☐'
        end
      end



      
      if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'
        
        @processflow_check = if pro.documents.attached?
          '☑'
           
          begin
            # プレスファイルの確認
            press_file_found = false
            mold_file_found = false
            
            # 最初にプレスファイルを探す
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              if filename.include?('プロセスフロー') && filename.include?('プレス')
                press_file_found = true
                begin
                  temp_file = Tempfile.new(['temp', File.extname(filename)])
                  temp_file.binmode
                  temp_file.write(doc.download)
                  temp_file.rewind

                  workbook = case File.extname(filename).downcase
                            when '.xlsx' then Roo::Excelx.new(temp_file.path)
                            when '.xls'  then Roo::Excel.new(temp_file.path)
                            else
                              next
                            end

                  Rails.logger.info "=== ワークシート情報 ==="
                  Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                  
                  # 適切なシートを探す
                  target_sheet = nil
                  workbook.sheets.each do |sheet_name|
                    workbook.default_sheet = sheet_name
                    Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                    
                    # セル(2,21)とセル(2,22)の値を確認
                    cell_2_21 = workbook.cell(2, 21)
                    cell_2_22 = workbook.cell(2, 22)
                    
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                    
                    if cell_2_21.present? || cell_2_22.present?
                      target_sheet = sheet_name
                      Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                      break
                    end
                  end

                  unless target_sheet
                    Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                    next
                  end

                  workbook.default_sheet = target_sheet
                  Rails.logger.info "選択したシート: #{target_sheet}"
                  Rails.logger.info "最終行: #{workbook.last_row}"
                  Rails.logger.info "最終列: #{workbook.last_column}"

                  # セルの値を文字列として取得し、デバッグ情報を出力
                  @processflow_stamping_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_stamping_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_stamping_check = '☑'

                  Rails.logger.info "=== セルの値確認 ==="
                  Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                  Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_stamping_person_in_charge.inspect}"
                  Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                  Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_stamping_dept.inspect}"

                  Rails.logger.info "プレス承認者: \#{?processflow_stamping_person_in_charge}"
                  Rails.logger.info "プレス部署: \#{?processflow_stamping_dept}"
                rescue StandardError => e
                  Rails.logger.error "プレスファイル処理エラー: #{e.message}"
                ensure
                  workbook&.close if defined?(workbook) && workbook
                  temp_file.close
                  temp_file.unlink
                end
                break
              end
            end

            # プレスファイルがない場合は成形ファイルを探す
            unless press_file_found
              pro.documents.each do |doc|
                filename = doc.filename.to_s
                if filename.include?('プロセスフロー') && filename.include?('成形')
                  mold_file_found = true
                  begin
                    temp_file = Tempfile.new(['temp', File.extname(filename)])
                    temp_file.binmode
                    temp_file.write(doc.download)
                    temp_file.rewind

                    workbook = case File.extname(filename).downcase
                              when '.xlsx' then Roo::Excelx.new(temp_file.path)
                              when '.xls'  then Roo::Excel.new(temp_file.path)
                              else
                                next
                              end

                    Rails.logger.info "=== ワークシート情報 ==="
                    Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                    
                    # 適切なシートを探す
                    target_sheet = nil
                    workbook.sheets.each do |sheet_name|
                      workbook.default_sheet = sheet_name
                      Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                      
                      # セル(2,21)とセル(2,22)の値を確認
                      cell_2_21 = workbook.cell(2, 21)
                      cell_2_22 = workbook.cell(2, 22)
                      
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                      Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                      
                      if cell_2_21.present? || cell_2_22.present?
                        target_sheet = sheet_name
                        Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                        break
                      end
                    end

                    unless target_sheet
                      Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                      next
                    end

                    workbook.default_sheet = target_sheet
                    Rails.logger.info "選択したシート: #{target_sheet}"
                    Rails.logger.info "最終行: #{workbook.last_row}"
                    Rails.logger.info "最終列: #{workbook.last_column}"

                    # セルの値を文字列として取得し、デバッグ情報を出力
                    @processflow_mold_person_in_charge = workbook.cell(2, 21).to_s.strip
                    @processflow_mold_dept = workbook.cell(4, 13).to_s.strip
                    @processflow_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
                    @processflow_mold_kanryou = pro.end_at.strftime('%y/%m/%d')
                    @processflow_mold_check = '☑'

                    Rails.logger.info "=== セルの値確認 ==="
                    Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                    Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_mold_person_in_charge.inspect}"
                    Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                    Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_mold_dept.inspect}"

                    Rails.logger.info "成形承認者: \#{?processflow_mold_person_in_charge}"
                  rescue StandardError => e
                    Rails.logger.error "成形ファイル処理エラー: #{e.message}"
                  ensure
                    workbook&.close if defined?(workbook) && workbook
                    temp_file.close
                    temp_file.unlink
                  end
                  break
                end
              end
            end

            # 営業、工程設計、検査のファイルは毎回確認
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              next unless filename.include?('プロセスフロー')

              begin
                temp_file = Tempfile.new(['temp', File.extname(filename)])
                temp_file.binmode
                temp_file.write(doc.download)
                temp_file.rewind

                workbook = case File.extname(filename).downcase
                          when '.xlsx' then Roo::Excelx.new(temp_file.path)
                          when '.xls'  then Roo::Excel.new(temp_file.path)
                          else
                            next
                          end

                Rails.logger.info "=== ワークシート情報 ==="
                Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
                
                # 適切なシートを探す
                target_sheet = nil
                workbook.sheets.each do |sheet_name|
                  workbook.default_sheet = sheet_name
                  Rails.logger.info "シート '#{sheet_name}' をチェック中..."
                  
                  # セル(2,21)とセル(2,22)の値を確認
                  cell_2_21 = workbook.cell(2, 21)
                  cell_2_22 = workbook.cell(2, 22)
                  
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"
                  
                  if cell_2_21.present? || cell_2_22.present?
                    target_sheet = sheet_name
                    Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                    break
                  end
                end

                unless target_sheet
                  Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                  next
                end

                workbook.default_sheet = target_sheet
                Rails.logger.info "選択したシート: #{target_sheet}"
                Rails.logger.info "最終行: #{workbook.last_row}"
                Rails.logger.info "最終列: #{workbook.last_column}"

                # セルの値を文字列として取得し、デバッグ情報を出力
                if filename.include?('営業')
                  @processflow_sales_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_sales_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_sales_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_sales_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_sales_check='☑'
                  Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
                elsif filename.include?('工程設計')
                  @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_design_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_design_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_design_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_design_check='☑'
                  Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
                elsif filename.include?('検査')
                  @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_inspection_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_inspection_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_inspection_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_inspection_check='☑'
                  Rails.logger.info "検査引渡し承認者: \#{?processflow_inspection_person_in_charge}"
                end
              rescue StandardError => e
                Rails.logger.error "その他ファイル処理エラー: #{e.message}"
              ensure
                workbook&.close if defined?(workbook) && workbook
                temp_file.close
                temp_file.unlink
              end
            end

          rescue StandardError => e
            Rails.logger.error "ファイル処理エラー: #{e.message}"
          end
        else
          '☐'
        end
      end






      if stage == '初期工程調査結果'
        @cpk_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @cpk_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成
          pattern = "/myapp/db/documents/*#{partnumber}*工程能力(Ppk)調査表*"
          Rails.logger.info "Path= #{pattern}"
          # パターンに一致するファイルを取得
          files = Dir.glob(pattern)
          # 各ファイルに対して処理を行う
          files.each do |file|
            # Excelファイルを開く
            if File.extname(file) == '.xlsx'
              workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
            elsif File.extname(file) == '.xls'
              workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
            else
              break
            end

            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # i4のセルの値を取得
            @cpk_person_in_charge = worksheet.cell(50, 71)
            @cpk_manager = worksheet.cell(50, 76)

            def cell_address_to_position(cell_address)
              col = cell_address.gsub(/\d/, '')
              row = cell_address.gsub(/\D/, '').to_i

              col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
              [row, col_index]
            end

            satisfied = '工程能力は満足している'
            not_satisfied = '工程能力は不足している'

            # チェックするセルの位置
            check_addresses = %w[E N W AF AO AX BG BP BY].map { |col| "#{col}44" }

            # 初期値
            satisfied_count = 0
            not_satisfied_count = 0

            # すべてのシートをループ
            workbook.sheets.each do |sheet_name|
              worksheet = workbook.sheet(sheet_name)

              check_addresses.each do |cell_address|
                row, col = cell_address_to_position(cell_address)
                cell_value = worksheet.cell(row, col)

                satisfied_count += 1 if cell_value == satisfied
                not_satisfied_count += 1 if cell_value == not_satisfied
              end
            end

            # 結果の設定
            @cpk_result = if not_satisfied_count.positive?
                            not_satisfied
                          elsif satisfied_count.positive?
                            satisfied
                          else
                            '結果なし' # この行は必要に応じて変更または削除してください
                          end
            @cpk_satisfied_count = satisfied_count
            @cpk_not_satisfied_count = not_satisfied_count

            @cpk_person_in_charge = worksheet.cell(50, 76) # 担当者名

            if worksheet.cell(3, 59) != nil
              @cpk_yotei = worksheet.cell(3, 59)
              @cpk_kanryou = worksheet.cell(3, 59)
            end
          end
          @cpk_check = '☑'
        else
          @cpk_check = '☐'
        end
      end

      if stage == '測定システム解析（MSA)' # GRR
        @grr_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @grr_kanryou = pro.end_at.strftime('%y/%m/%d')

        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*ゲージR&R*#{partnumber}*"
          Rails.logger.info "Path= #{pattern}"
          files = Dir.glob(pattern)
          @grr_count = files.size

          if @apqp_approved_report_insert_rows_to_excel_template_msa == true # 初回のファイルのみサブルーチン処理
            apqp_approved_report_insert_rows_to_excel_template_msa # ファイルの数だけ行を挿入するサブルーチン処理
          end

          # 各記号の初期化
          @grr = 0
          @ndc = 0

          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            if file.end_with?('.xlsx')
              workbook = Roo::Excelx.new(file)
            elsif file.end_with?('.xls')
              workbook = Roo::Excel.new(file)
            else
              raise 'Unsupported file format'
            end

            worksheet = workbook.sheet(0)

            @debagtest = ''
            # if worksheet.cell(4, 24) != nil

            instance_variable_set("@grr_kanryou_#{i + 1}", worksheet.cell(2, 8))
            instance_variable_set("@grr_yotei_#{i + 1}", worksheet.cell(2, 8))
            instance_variable_set("@grr_person_in_charge_#{i + 1}", worksheet.cell(36, 9))
            instance_variable_set("@grr_approved_#{i + 1}", worksheet.cell(36, 9))

            # end
            instance_variable_set("@grr_no_#{i + 1}", worksheet.cell(4, 2).to_s)

            instance_variable_set("@grr_#{i + 1}", worksheet.cell(23, 8).round(2))
            instance_variable_set("@ndc_#{i + 1}", worksheet.cell(31, 8).round(2))

            if worksheet.cell(23, 8) <= 10
              instance_variable_set("@grr_result_#{i + 1}", '合格')
            elsif worksheet.cell(23, 8) > 10 && worksheet.cell(23, 8) < 30
              instance_variable_set("@grr_result_#{i + 1}", '十分ではないが合格')
            else
              instance_variable_set("@grr_result_#{i + 1}", '不合格')
            end

            if worksheet.cell(31, 8) >= 5
              instance_variable_set("@ndc_result_#{i + 1}", '合格')
            else
              instance_variable_set("@ndc_result_#{i + 1}", '不合格')
            end
          end

          @grr_check = '☑'
        else
          @grr_check = '☐'

        end
        Rails.logger.info "@grr_person_in_charge_1= #{@grr_person_in_charge_1}" # 追加
        Rails.logger.info "@grr_result_1= #{@grr_result_1}"  # 追加
        Rails.logger.info "@ndc_result_1= #{@ndc_result_1}"  # 追加

        Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

      end

      if stage == '測定システム解析（MSA)' # クロスタブ
        @msa_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @msa_kanryou = pro.end_at.strftime('%y/%m/%d')

        if pro.documents.attached?
          # 変数の設定
          partnumber = pro.partnumber
          pattern = "/myapp/db/documents/*#{partnumber}*計数値MSA報告書*"
          Rails.logger.info "Path= #{pattern}"
          files = Dir.glob(pattern)
          @msa_crosstab_count = files.size

          if @apqp_approved_report_insert_rows_to_excel_template == true # 初回のファイルのみサブルーチン処理
            apqp_approved_report_insert_rows_to_excel_template # ファイルの数だけ行を挿入するサブルーチン処理
          end

          # 各記号のカウントを初期化
          @maru_count = 0
          @batsu_count = 0
          @sankaku_count = 0
          @oomaru_count = 0

          files.each_with_index do |file, i| # with_indexでインデックスiを追加
            workbook = Roo::Excelx.new(file)
            worksheet = workbook.sheet(0)

            @debagtest = ''
            # if worksheet.cell(4, 24) != nil

            instance_variable_set("@msa_crosstab_kanryou_#{i + 1}", worksheet.cell(4, 24))
            instance_variable_set("@msa_crosstab_recorder_#{i + 1}", worksheet.cell(6, 24))
            instance_variable_set("@msa_crosstab_person_in_charge_#{i + 1}", worksheet.cell(120, 29))
            instance_variable_set("@msa_crosstab_approved_#{i + 1}", worksheet.cell(120, 27))
            @debagtest = worksheet.cell(76, 29)
            Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加
            Rails.logger.info "i= #{i}" # 追加

            # end

            instance_variable_set("@inspector_name_a_#{i + 1}", worksheet.cell(8, 10))
            instance_variable_set("@inspector_name_b_#{i + 1}", worksheet.cell(8, 16))
            instance_variable_set("@inspector_name_c_#{i + 1}", worksheet.cell(8, 22))
            instance_variable_set("@inspector_a_result_#{i + 1}", worksheet.cell(131, 7))
            instance_variable_set("@inspector_b_result_#{i + 1}", worksheet.cell(131, 11))
            instance_variable_set("@inspector_c_result_#{i + 1}", worksheet.cell(131, 15))
          end

          @msa_crosstab_check = '☑'
        else
          @msa_crosstab_check = '☐'
          @msa_crosstab_count = 0
        end
        Rails.logger.info "@msa_crosstab_person_in_charge_0= #{@msa_crosstab_person_in_charge_0}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_1= #{@msa_crosstab_person_in_charge_1}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_2= #{@msa_crosstab_person_in_charge_2}"  # 追加
        Rails.logger.info "@msa_crosstab_person_in_charge_3= #{@msa_crosstab_person_in_charge_3}"  # 追加
        Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

      end

      if %w[量産コントロールプラン 試作コントロールプラン].include?(stage)
        @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
        if pro.documents.attached?
          @cp_check = '☑'
          @cp_filename = pro.documents.first.filename.to_s
        else
          @cp_check = '☐'
        end
      end

      next unless stage == '設計計画書_金型設計'

      @plan_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @plan_kanryou = pro.end_at.strftime('%y/%m/%d')
      next unless pro.documents.attached?

      # 変数の設定
      partnumber = pro.partnumber # ここには実際の値を設定してください
      # パスとファイル名のパターンを作成
      pattern = "/myapp/db/documents/*#{partnumber}*設計計画書*"
      # pattern = "/myapp/db/documents/NT2394-P43_PM81EB_設計計画書.xls"
      Rails.logger.info "Path= #{pattern}"
      # パターンに一致するファイルを取得
      files = Dir.glob(pattern)
      # 各ファイルに対して処理を行う
      files.each do |file|
        # Excelファイルを開く
        if File.extname(file) == '.xlsx'
          workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
        elsif File.extname(file) == '.xls'
          workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
        else
          break
        end

        # 最初のシートを取得
        worksheet = workbook.sheet(0)

        # i4のセルの値を取得
        @plan_designer = worksheet.cell(4, 9)
        @plan_manager = worksheet.cell(5, 9)
        @plan_customer = worksheet.cell(6, 3)
        @plan_risk = worksheet.cell(41, 4).nil? ? '' : worksheet.cell(41, 4).to_s + worksheet.cell(42, 4).to_s
        @plan_opportunity = if worksheet.cell(43,
                                              4).nil?
                              ''
                            else
                              worksheet.cell(43, 4).to_s + worksheet.cell(44, 4).to_s
                            end

        if worksheet.cell(10, 4) != nil
          @plan_yotei = worksheet.cell(11, 4)
          @plan_kanryou = worksheet.cell(11, 6)
        end
      end
    end
  end

  def apqp_approved_report_insert_rows_to_excel_template_msa
    if @apqp_approved_report_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report.xlsx')
      @apqp_approved_report_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report_modified.xlsx')
    end
    @apqp_approved_report_insert_rows_to_excel_template_msa = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @grr_count >= 2
              @grr_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (10..85).each do |row|
      if worksheet[row][1].value == 'GRR' # B列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      # worksheet[row_number][7].change_contents("品証（\#{?grr_person_in_charge_#{i + 2}}）")
      # worksheet[row_number][10].change_contents("\#{?grr_yotei_#{i + 2}}")
      # worksheet[row_number][12].change_contents("\#{?grr_kanryou_#{i + 2}}")
      worksheet[row_number][5].change_contents("項番：\#{?grr_no_#{i + 2}} \n GRR値：\#{?grr_#{i + 2}}%、GRR結果：\#{?grr_result_#{i + 2}} \n ndc値：\#{?ndc_#{i + 2}}、ndc結果：\#{?ndc_result#{i + 2}}")

      # H列、I列、J列を結合
      # worksheet.merge_cells(row_number, 7, row_number, 9)
      # worksheet.merge_cells(row_number, 10, row_number, 11)
      # worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 5, row_number, 20)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 1, insert_row_number + count - 1, 4)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/apqp_approved_report_modified.xlsx')
  end

  def apqp_approved_report_insert_rows_to_excel_template
    if @apqp_approved_report_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report.xlsx')
      @apqp_approved_report_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report_modified.xlsx')
    end
    @apqp_approved_report_insert_rows_to_excel_template = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @msa_crosstab_count >= 2
              @msa_crosstab_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (10..85).each do |row|
      if worksheet[row][1].value == 'クロスタブ' # B列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      # worksheet[row_number][7].change_contents("品証（\#{?msa_crosstab_person_in_charge_#{i + 2}}）")
      # worksheet[row_number][10].change_contents("\#{?msa_crosstab_yotei_#{i + 2}}")
      # worksheet[row_number][12].change_contents("\#{?msa_crosstab_kanryou_#{i + 2}}")
      worksheet[row_number][5].change_contents("\#{?inspector_name_a_#{i + 2}}：\#{?inspector_a_result_#{i + 2}}、\#{?inspector_name_b_#{i + 2}}：\#{?inspector_b_result_#{i + 2}}、\#{?inspector_name_c_#{i + 2}}：\#{?inspector_c_result_#{i + 2}}")

      # H列、I列、J列を結合
      # worksheet.merge_cells(row_number, 7, row_number, 9)
      # worksheet.merge_cells(row_number, 10, row_number, 11)
      # worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 5, row_number, 20)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 1, insert_row_number + count - 1, 4)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/apqp_approved_report_modified.xlsx')
  end

  # RailsでAxlsxを使ってxlsxを生成
  # https://qiita.com/necojackarc/items/0dbd672b2888c30c5a38

  # 【Rails】 strftimeの使い方と扱えるクラスについて
  # https://pikawaka.com/rails/strftime

  def generate_xlsx
    workbook = RubyXL::Workbook.new
    worksheet = workbook.add_worksheet('登録データ一覧')
  
    # スタイルの定義
    title_style = { 'fill_color' => 'C0C0C0', 'font_name' => 'Arial', 'font_size' => 12, 'b' => true }
    header_style = { 'fill_color' => 'E0E0E0', 'font_name' => 'Arial', 'font_size' => 11, 'b' => true }
  
    # タイトル行の追加
    title_cell = worksheet.add_cell(0, 0, '登録データ一覧')
    title_cell.change_fill(title_style['fill_color'])
    title_cell.change_font_name(title_style['font_name'])
    title_cell.change_font_size(title_style['font_size'])
    title_cell.change_font_bold(title_style['b'])
  
    # ヘッダー行の追加
    headers = %w[ID 図番 材料コード 文書名 詳細 カテゴリー フェーズ 項目 登録日 完了予定日 完了日 達成度 ステイタス]
    headers.each_with_index do |header, index|
      header_cell = worksheet.add_cell(1, index, header)
      header_cell.change_fill(header_style['fill_color'])
      header_cell.change_font_name(header_style['font_name'])
      header_cell.change_font_size(header_style['font_size'])
      header_cell.change_font_bold(header_style['b'])
    end
  
    # データ行の追加
    @products.each_with_index do |pro, row|
      data = [
        pro.id,
        pro.partnumber,
        pro.materialcode,
        pro.documentname,
        pro.description,
        @dropdownlist[pro.category.to_i],
        @dropdownlist[pro.phase.to_i],
        @dropdownlist[pro.stage.to_i],
        pro.start_time&.strftime('%y/%m/%d'),
        pro.deadline_at&.strftime('%y/%m/%d'),
        pro.end_at&.strftime('%y/%m/%d'),
        pro.goal_attainment_level,
        pro.status
      ]
      data.each_with_index do |value, col|
        worksheet.add_cell(row + 2, col, value)
      end
    end
  
    # ファイルの送信
    send_data(
      workbook.stream.string,
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      filename: "登録データ一覧(#{Time.zone.now.strftime('%Y_%m_%d_%H_%M_%S')}).xlsx"
    )
  end

 # def generate_xlsx
 #   workbook = Caxlsx::Workbook.new
 #   workbook.add_worksheet(name: '登録データ一覧') do |sheet|
 #     styles = workbook.styles
 #     title = styles.add_style(bg_color: 'c0c0c0', b: true)
 #     header = styles.add_style(bg_color: 'e0e0e0', b: true)
 # 
 #     sheet.add_row ['登録データ一覧'], style: title
 #     sheet.add_row %w[ID 図番 材料コード 文書名 詳細 カテゴリー フェーズ 項目 登録日 完了予定日 完了日 達成度 ステイタス], style: header
 #     sheet.add_row %w[id partnumber materialcode documentname description category phase stage start_time deadline_at end_at goal_attainment_level status],
 #                   style: header
 # 
 #     @products.each do |pro|
 #       sheet.add_row [pro.id, pro.partnumber, pro.materialcode, pro.documentname, pro.description,
 #                      @dropdownlist[pro.category.to_i], @dropdownlist[pro.phase.to_i], @dropdownlist[pro.stage.to_i], pro.start_time.strftime('%y/%m/%d'), pro.deadline_at.strftime('%y/%m/%d'), pro.end_at.strftime('%y/%m/%d'), pro.goal_attainment_level, pro.status]
 #     end
 #   end
 # 
 #   send_data(workbook.to_stream.read,
 #             type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
 #             filename: "登録データ一覧(#{Time.zone.now.strftime('%Y_%m_%d_%H_%M_%S')}).xlsx")
 # end

  def set_q
    @q = Product.ransack(params[:q] || {})
  end

  def set_product
    #@product = Product.find(params[:id])
    @product = Product.find(params[:id])
    rescue ActiveRecord::RecordNotFound
    flash[:alert] = "Product not found.(set_product)"
    redirect_to products_path
  end

  def product_params
    params.require(:product).permit(:documentname, :materialcode, :start_time, :deadline_at, :end_at, :status,
                                    :goal_attainment_level, :description, :category, :partnumber, :phase, :stage, documents: [])
  end

  def search_params
    params.require(:q).permit(Product.column_names.map { |col| "#{col}_eq" })
  end

  def phase
    # @phases=Phase.all
    @phases = Phase.where(ancestry: nil)
    @pha = Phase.all

    # ドロップダウンリストの表示が数字のため、単語で表示するためにdropdownlistを設定。※なぜか288行が勝手に追加されるためSKIPで回避
    dropdownlist = []
    dropdownlist.push('0')
    @pha.each do |p|
      dropdownlist.push(p.name) if p.name != 'SKIP'
    end
    @dropdownlist = dropdownlist

    phases_test = []
    @pha.each do |p|
      phases_test.push(Phase.find(p.id).children)
      # @phases_test=Phase.find(p.id).children
    end
    @phases_test = phases_test
  end

  def get_pdf_links(urls)
    @pdf_links = []
    @days_since_published = []
    @publish_dates = [] # 発行日を格納するための配列を追加

    urls.each do |url|
      html = URI.open(url, open_timeout: 5, read_timeout: 10) # タイムアウトを設定
      doc = Nokogiri::HTML(html)
      links = doc.css('a')
      links.each do |link|
        next unless link['href'].include?('pdf') && link['href'].include?('ja')

        @pdf_links << link['href']
        file_name = link['href'].split('/').last
        days, publish_date = days_since_published(file_name) # 経過日数と発行日を取得
        @days_since_published << days
        @publish_dates << publish_date # 発行日を配列に追加
      end
    rescue OpenURI::HTTPError => e
      Rails.logger.error "HTTPエラーが発生しました: #{e.message}"
    rescue StandardError => e
      Rails.logger.error "その他のエラーが発生しました: #{e.message}"
    end
  end

  def days_since_published(file_name)
    if file_name =~ /([A-Za-z]+)[_-](\d{4})_ja\.pdf$/
      month_name = ::Regexp.last_match(1) # "May"
      year = ::Regexp.last_match(2).to_i # "2022"

      # 月の名前を数字に変換
      month = Date::MONTHNAMES.index(month_name.capitalize)

      # 月の名前が有効であることを確認
      if month
        # 年と月から日付オブジェクトを作成（月の最初の日を使用）
        published_date = Date.new(year, month)

        # 現在の日付との差を計算
        days_since = (Time.zone.today - published_date).to_i
        [days_since, published_date] # 経過日数と発行日を返す
      else
        Rails.logger.info "Invalid month name: #{month_name}"
        [nil, nil]
      end
    else
      Rails.logger.info "Could not extract date from file name: #{file_name}"
      [nil, nil]
    end
  end
end


#---------------------------








def create_workbook(file)
  if File.extname(file) == '.xlsx'
    Roo::Excelx.new(file)
  else
    Roo::Excel.new(file)
  end
end

def handle_error(error, file)
  Rails.logger.error "ファイル処理中にエラーが発生しました: #{File.basename(file)}"
  Rails.logger.error "エラー: #{error.class.name} - #{error.message}"
  Rails.logger.error error.backtrace.join("\n")
end

def find_sheet_by_keyword(workbook, keyword)
  if keyword.is_a?(Array)
    workbook.sheets.find { |sheet_name| keyword.any? { |k| sheet_name.include?(k) } }
  else
    workbook.sheets.find { |sheet_name| sheet_name.include?(keyword) }
  end
end


def process_sheet1(source_worksheet, worksheet, row)
  audit_types = get_audit_info1(source_worksheet)
  content_nature, cause = get_additional_info(source_worksheet)
  data = get_row_data1(source_worksheet, audit_types, content_nature, cause)

  # 列幅を調整するための最大幅を保持する配列
  max_widths = Array.new(data.size, 0)

  # 最初の行を追加
  data.each_with_index do |value, col_index|
    cell = worksheet.add_cell(row, col_index, value)

    if [2, 9].include?(col_index)  # 日付列のインデックス
      cell.set_number_format('yyyy/mm/dd')
    elsif [7, 8].include?(col_index)  # 不適合の内容・性質と原因（発生及び流出）の列
      cell.change_text_wrap(true)
    end

    # 最大幅を更新
    max_widths[col_index] = [max_widths[col_index], value.to_s.length].max
  end

  # 次の行を追加する場合
  next_data = get_row_data1(source_worksheet, audit_types, content_nature, cause) # 2行目のデータを取得
  row += 1  # 次の行に移動

  next_data.each_with_index do |value, col_index|
    cell = worksheet.add_cell(row, col_index, value)

    if [2, 9].include?(col_index)  # 日付列のインデックス
      cell.set_number_format('yyyy/mm/dd')
    elsif [7, 8].include?(col_index)  # 不適合の内容・性質と原因（発生及び流出）の列
      cell.change_text_wrap(true)
    end

    # 最大幅を更新
    max_widths[col_index] = [max_widths[col_index], value.to_s.length].max
  end

  # H列とI列の幅を50に固定
  worksheet.change_column_width(7, 70)  # H列のインデックス
  worksheet.change_column_width(8, 80)  # I列のインデックス

  # 他の列の幅を15に設定
  (0...max_widths.size).each do |col_index|
    next if col_index == 7 || col_index == 8  # H列とI列はスキップ
    worksheet.change_column_width(col_index, 15)  # 15文字に設定
  end

  Rails.logger.info "シートに行を追加しました: #{data.inspect}"
  row + 1
end


def process_sheet2(source_worksheet, worksheet, row)
  Rails.logger.info "process_sheet2 メソッドが呼び出されました。現在の行: #{row}"
  begin
    data = get_row_data2(source_worksheet)
    Rails.logger.debug "get_row_data2 の結果: #{data.inspect}"

    # 列幅を調整するための最大幅を保持する配列
    max_widths = Array.new(data.size, 0)

    data.each_with_index do |value, col_index|
      cell = worksheet.add_cell(row, col_index, value)
      if [2, 6, 14, 24, 25, 30, 31, 33, 38, 39, 42].include?(col_index)  # 日付列のインデックス
        cell.set_number_format('yyyy/mm/dd')
      elsif [9, 12, 13, 17, 18, 19, 21, 22, 26, 27, 32, 36, 40, 44].include?(col_index)  # 複数行のテキストを含む列
        cell.change_text_wrap(true)
      end

      # 最大幅を更新
      max_widths[col_index] = [max_widths[col_index], value.to_s.length].max
    end

    # 指定された列の幅を設定
    worksheet.change_column_width(9, 80)  # J列のインデックス
    worksheet.change_column_width(12, 80) # M列のインデックス
    worksheet.change_column_width(13, 30)  # N列
    worksheet.change_column_width(17, 60)  # R列
    worksheet.change_column_width(18, 30)  # S列
    worksheet.change_column_width(19, 80)  # T列
    worksheet.change_column_width(21, 80)  # V列
    worksheet.change_column_width(22, 85)  # W列
    worksheet.change_column_width(26, 80)  # AA列
    worksheet.change_column_width(27, 85)  # AB列
    worksheet.change_column_width(36, 80)  # AK列
    worksheet.change_column_width(40, 80)  # AO列

    # 他の列の幅を20に設定
    (0...max_widths.size).each do |col_index|
      next if [9, 12, 13, 17, 18, 19, 21, 22, 26, 27, 36, 40].include?(col_index)  # 指定された列はスキップ
      worksheet.change_column_width(col_index, 25)  # 20文字に設定
    end

    Rails.logger.info "process_sheet2 メソッドが完了しました。次の行: #{row + 1}"
    row + 1
  rescue => e
    Rails.logger.error "process_sheet2 でエラーが発生しました: #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    row
  end
end









def get_audit_info1(source_worksheet)
  audit_types = []
  (20..23).each do |r|
    cell_value = source_worksheet.cell(r, 'A')
    if cell_value.present? && cell_value.to_s.strip.start_with?('□')
      audit_types << cell_value.to_s.strip[1..-1]
    end
  end
  audit_types
end

def get_additional_info(source_worksheet)
  content_nature = []
  cause = []
  current_section = nil

  (1..source_worksheet.last_row).each do |r|
    cell_value = source_worksheet.cell(r, 'A')
    if cell_value.present?
      cell_value = cell_value.to_s.strip
      if cell_value.include?("不適合の内容・性質")
        current_section = :content_nature
      elsif cell_value.include?("原因（発生及び流出）")
        current_section = :cause
      elsif cell_value.include?("不適合品の処置")
        current_section = nil
      elsif current_section == :content_nature && !content_nature.include?(cell_value)
        content_nature << cell_value
      elsif current_section == :cause && !cause.include?(cell_value)
        cause << cell_value
      end
    end
  end

  [content_nature.join("\n").strip, cause.join("\n").strip]
end

def get_row_data1(source_worksheet, audit_types, content_nature, cause)
  # A列から特定の値を探して対応するE列の値を取得する関数
  def find_value_in_column_e(worksheet, target_text)
    (1..worksheet.last_row).each do |row|
      cell_value = worksheet.cell(row, 'A')
      if cell_value.present? && cell_value.to_s.strip == target_text
        return worksheet.cell(row, 'E')
      end
    end
    nil
  end

    # AB列から品証受付番号を探し、見つけたら1つ下の行の値を返すメソッド
    def find_value_in_column_ab(worksheet, target_text)
      (1..worksheet.last_row).each do |row|
        cell_value = worksheet.cell(row, 'AB')
        if cell_value.present? && cell_value.to_s.strip == target_text
          return worksheet.cell(row + 1, 'AB')  # 1つ下の行の値を返す
        end
      end
      nil
    end

  # 品名/図番の行を特定する関数
  def find_product_row(worksheet)
    (1..worksheet.last_row).each do |row|
      cell_value = worksheet.cell(row, 'A')
      if cell_value.present? && cell_value.to_s.strip == "品名/図番"
        return row
      end
    end
    nil
  end

  # 品名/図番の行を特定
  product_row = find_product_row(source_worksheet)

  # 当該部門の値を取得
  department_value = find_value_in_column_e(source_worksheet, "当該部門") || find_value_in_column_e(source_worksheet, "＊当該部門")


  [
    find_value_in_column_e(source_worksheet, "発行部門"),   # 発行部門
    find_value_in_column_ab(source_worksheet, "品証受付番号"),  # 品証受付番号の1つ下の行の値
    parse_date1(find_value_in_column_e(source_worksheet, "発行日")),  # 発行日
    department_value,   # 当該部門
    find_value_in_column_e(source_worksheet, "品名/図番"),   # 品名/図番
    product_row ? source_worksheet.cell(product_row, 'P') : nil,   # ロット№
    product_row ? source_worksheet.cell(product_row, 'AA') : nil,  # 数量
    content_nature,  # 不適合の内容・性質
    cause,           # 原因（発生及び流出）
    parse_date1(source_worksheet.cell(25, 'A')),  # 処置日
    get_nonconforming_product_disposition(source_worksheet),  # 不適合品の処置
    source_worksheet.cell(24, 'M'),  # 処置者
    source_worksheet.cell(22, 'E'),  # 是正処置の必要性
    source_worksheet.cell(24, 'W'),  # 主管部門
    source_worksheet.cell(25, 'W'),  # 関連部門
  ]
end

def get_nonconforming_product_disposition(worksheet)
  disposition = []
  start_row = nil
  (1..worksheet.last_row).each do |row|
    if worksheet.cell(row, 'A').to_s.strip == '処置日'
      start_row = row
      break
    end
  end

  if start_row
    ('E'..'K').each do |col|
      header = worksheet.cell(start_row, col)
      value = worksheet.cell(start_row + 1, col)
      if value && !value.to_s.strip.empty?
        disposition << "#{header}: #{value}"
      end
    end
  end

  disposition.join(', ')
end

def get_row_data2(source_worksheet)
Rails.logger.info "get_row_data2 メソッドが呼び出されました"
  
  data = [
    source_worksheet.cell(2, 'K'),   # 管理No.
    source_worksheet.cell(4, 'C'),   # 件名
    parse_date1(source_worksheet.cell(5, 'H')),  # 発行日
    source_worksheet.cell(5, 'K'),   # 起票者
    source_worksheet.cell(6, 'C'),   # 品番又はプロセス
    source_worksheet.cell(6, 'K'),   # 発生場所
    parse_date1(source_worksheet.cell(9, 'C')),  # 発生日
    source_worksheet.cell(8, 'G'),   # 責任部門
    source_worksheet.cell(8, 'N'),   # 他部門要請
    get_section_content(source_worksheet, '不適合内容', '顧客在庫への影響'),  # 不適合内容
    source_worksheet.cell(10, 'N'),  # 発生履歴
    source_worksheet.cell(18, 'B'),  # 顧客への影響
    get_section_content(source_worksheet, '現品処置', '処置結果'),  # 現品処置
    get_section_content(source_worksheet, '処置結果', '在庫品の処置'),  # 処置結果
    parse_date1(source_worksheet.cell(28, 'H')),  # 実施日
    source_worksheet.cell(26, 'O'),  # 承認
    source_worksheet.cell(28, 'O'),  # 担当
    get_section_content(source_worksheet, '在庫品の処置', '処置結果'),  # 在庫品の処置
    get_section_content(source_worksheet, '処置結果', '事実の把握', min_row: 31),  # 処置結果（31行目以降）
    get_section_content(source_worksheet, '事実の把握', '原因と対策'),  # 事実の把握
    source_worksheet.cell(40, 'M'),  # 5M1Eの変更点・変化点
    get_section_content(source_worksheet, '原因と対策', '発生対策', column: 'D'),  # 発生原因
    get_section_content(source_worksheet, '発生対策', '流出原因'),  # 発生対策
    parse_date1(source_worksheet.cell(61, 'J')),  # 予定日
    parse_date1(source_worksheet.cell(62, 'J')),  # 実施日
    source_worksheet.cell(61, 'O'),  # 実施者
    get_section_content(source_worksheet, '流出原因', '流出対策', column: 'D'),  # 流出原因
    get_section_content(source_worksheet, '流出対策', '他の製品及びプロセスへの影響の有無'),  # 流出対策
    source_worksheet.cell(77, 'F'),  # 他の製品及びプロセスへの影響の有無
    parse_date1(source_worksheet.cell(76, 'J')),  # 予定日
    parse_date1(source_worksheet.cell(77, 'J')),  # 実施日
    source_worksheet.cell(77, 'O'),  # 実施者
    get_section_content(source_worksheet, '効果の確認', '歯止め'),  # 効果の確認
    parse_date1(source_worksheet.cell(83, 'J')),  # 確認日
    source_worksheet.cell(81, 'O'),  # 承認
    source_worksheet.cell(82, 'O'),  # 担当
    get_section_content(source_worksheet, '歯止め', '水平展開'),  # 歯止め
    parse_date1(source_worksheet.cell(88, 'F')),  # 予定日
    parse_date1(source_worksheet.cell(88, 'J')),  # 実施日
    source_worksheet.cell(87, 'O'),  # 実施者
    get_section_content(source_worksheet, '水平展開', '必要性'),  # 水平展開
    source_worksheet.cell(92, 'E'),  # 水平展開（予防）の必要性
    parse_date1(source_worksheet.cell(92, 'J')),  # 実施日
    source_worksheet.cell(92, 'O'),  # 実施者
    get_section_content(source_worksheet, '処置活動のレビュー', nil, max_rows: 10),  # 処置活動のレビュー
    parse_date1(source_worksheet.cell(96, 'I')),  # レビュー日
    source_worksheet.cell(95, 'O')   # 承認
  ]

  data.each_with_index do |value, index|
    Rails.logger.debug "データ[#{index}]: #{value}"
  end
  
  Rails.logger.debug "get_row_data2 の結果: #{data.inspect}"
  data
end

def get_section_content(source_worksheet, start_text, end_text, column: 'B', min_row: nil, max_rows: nil)
  content = []
  start_row = nil
  end_row = nil

  search_start = min_row || 1
  (search_start..source_worksheet.last_row).each do |r|
    cell_value = source_worksheet.cell(r, 'B')
    if cell_value.present?
      cell_value = cell_value.to_s.strip
      if cell_value.include?(start_text)
        start_row = r + 1  # タイトル行の次の行から開始
        break
      end
    end
  end

  if start_row
    (start_row..source_worksheet.last_row).each do |r|
      b_cell_value = source_worksheet.cell(r, 'B')
      if b_cell_value.present?
        b_cell_value = b_cell_value.to_s.strip
        if end_text && b_cell_value.include?(end_text)
          end_row = r - 1
          break
        end
      end
      
      cell_value = source_worksheet.cell(r, column)
      content << cell_value if cell_value.present?
      
      break if max_rows && (r - start_row >= max_rows)
    end
  end

  content.join("\n").strip
end

def parse_date1(cell_value)
  case cell_value
  when Date, Time
    cell_value
  when String
    begin
      Date.parse(cell_value)
    rescue Date::Error
      cell_value
    end
  when Numeric
    begin
      base_date = Date.new(1899, 12, 30)
      base_date + cell_value.to_i
    rescue Date::Error
      cell_value
    end
  else
    cell_value
  end
end
