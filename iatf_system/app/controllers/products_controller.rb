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
    Rails.logger.debug { "params: #{params.inspect}" }
    create_data
    send_data(
      excel_render('lib/excel_templates/process_design_plan_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_製造工程設計計画／実績書.xlsx"
    )
  end

  def apqp_plan_report
    @products = Product.where(partnumber: params[:partnumber])
    @all_products = Product.all
    Rails.logger.debug { "params: #{params.inspect}" }
    create_data_apqp_plan_report
    send_data(
      excel_render('lib/excel_templates/apqp_plan_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_APQP計画書.xlsx"
    )
  end

  def apqp_approved_report
    @products = Product.where(partnumber: params[:partnumber])
    @all_products = Product.all
    Rails.logger.debug { "params: #{params.inspect}" }
    create_data_apqp_approved_report
    send_data(
      excel_render('lib/excel_templates/apqp_approved_report_modified.xlsx').stream.string,
      type: 'application/vnd.ms-excel',
      filename: "#{@datetime.strftime('%Y%m%d')}_#{@partnumber}_APQP総括・承認書.xlsx"
    )
  end


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

  end

  def import
    Product.import(params[:file])
    redirect_to products_url
  end


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
    @products = @qd.result(distinct: true)
  end

  def graph
    @products = Product.all
  end

  def calendar
    @products = Product.all
  end

  def training
    @products = Product.includes(:documents_attachments).all
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
    @products = Product.includes(:documents_attachments).where(partnumber: params[:partnumber])
  end

  def index3
    # こちらを選択していた@products=Product.select("DISTINCT ON (partnumber,food) *").page(params[:page]).per(4)
    @products = Product.select('DISTINCT ON (partnumber,stage) *')

    @mark_complate = '完'
    @mark_WIP = '仕掛'

  end

  def index4
    # IATF要求事項説明ページ
  end

  def index8
    @products = Product.where(partnumber: params[:partnumber])
  end

  def index9
    @products = Product.select('DISTINCT ON (partnumber,stage) *')
  end

  # RailsでExcel出力しないといけなくなった時の対処法
  # https://www.timedia.co.jp/tech/railsexcel/

  def download
    response.headers['Content-Type'] = 'application/excel'
    response.headers['Content-Disposition'] = 'attachment; filename="製品データ.xls"'
    @products = Product.all
    render 'data_download.xls.erb'
  end

  # RailsでExcel出力しないといけなくなった時の対処法
  # https://www.timedia.co.jp/tech/railsexcel/

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
    ProductCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist
    ).each { |key, value| instance_variable_set("@\#{key}", value) }
  end
  #-------------------------------------------------------------------------------------------------
  def create_data_apqp_plan_report
    ApqpPlanCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist,
      partnumber:   params[:partnumber]
    ).each { |key, value| instance_variable_set("@\#{key}", value) }
  end

  def create_data_apqp_approved_report
    ApqpApprovedCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist,
      partnumber:   params[:partnumber]
    ).each { |key, value| instance_variable_set("@\#{key}", value) }
  end
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


  def set_q
    @q = Product.ransack(params[:q] || {})
  end

  def set_product
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
    parse_date(find_value_in_column_e(source_worksheet, "発行日")),  # 発行日
    department_value,   # 当該部門
    find_value_in_column_e(source_worksheet, "品名/図番"),   # 品名/図番
    product_row ? source_worksheet.cell(product_row, 'P') : nil,   # ロット№
    product_row ? source_worksheet.cell(product_row, 'AA') : nil,  # 数量
    content_nature,  # 不適合の内容・性質
    cause,           # 原因（発生及び流出）
    parse_date(source_worksheet.cell(25, 'A')),  # 処置日
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
    parse_date(source_worksheet.cell(5, 'H')),  # 発行日
    source_worksheet.cell(5, 'K'),   # 起票者
    source_worksheet.cell(6, 'C'),   # 品番又はプロセス
    source_worksheet.cell(6, 'K'),   # 発生場所
    parse_date(source_worksheet.cell(9, 'C')),  # 発生日
    source_worksheet.cell(8, 'G'),   # 責任部門
    source_worksheet.cell(8, 'N'),   # 他部門要請
    get_section_content(source_worksheet, '不適合内容', '顧客在庫への影響'),  # 不適合内容
    source_worksheet.cell(10, 'N'),  # 発生履歴
    source_worksheet.cell(18, 'B'),  # 顧客への影響
    get_section_content(source_worksheet, '現品処置', '処置結果'),  # 現品処置
    get_section_content(source_worksheet, '処置結果', '在庫品の処置'),  # 処置結果
    parse_date(source_worksheet.cell(28, 'H')),  # 実施日
    source_worksheet.cell(26, 'O'),  # 承認
    source_worksheet.cell(28, 'O'),  # 担当
    get_section_content(source_worksheet, '在庫品の処置', '処置結果'),  # 在庫品の処置
    get_section_content(source_worksheet, '処置結果', '事実の把握', min_row: 31),  # 処置結果（31行目以降）
    get_section_content(source_worksheet, '事実の把握', '原因と対策'),  # 事実の把握
    source_worksheet.cell(40, 'M'),  # 5M1Eの変更点・変化点
    get_section_content(source_worksheet, '原因と対策', '発生対策', column: 'D'),  # 発生原因
    get_section_content(source_worksheet, '発生対策', '流出原因'),  # 発生対策
    parse_date(source_worksheet.cell(61, 'J')),  # 予定日
    parse_date(source_worksheet.cell(62, 'J')),  # 実施日
    source_worksheet.cell(61, 'O'),  # 実施者
    get_section_content(source_worksheet, '流出原因', '流出対策', column: 'D'),  # 流出原因
    get_section_content(source_worksheet, '流出対策', '他の製品及びプロセスへの影響の有無'),  # 流出対策
    source_worksheet.cell(77, 'F'),  # 他の製品及びプロセスへの影響の有無
    parse_date(source_worksheet.cell(76, 'J')),  # 予定日
    parse_date(source_worksheet.cell(77, 'J')),  # 実施日
    source_worksheet.cell(77, 'O'),  # 実施者
    get_section_content(source_worksheet, '効果の確認', '歯止め'),  # 効果の確認
    parse_date(source_worksheet.cell(83, 'J')),  # 確認日
    source_worksheet.cell(81, 'O'),  # 承認
    source_worksheet.cell(82, 'O'),  # 担当
    get_section_content(source_worksheet, '歯止め', '水平展開'),  # 歯止め
    parse_date(source_worksheet.cell(88, 'F')),  # 予定日
    parse_date(source_worksheet.cell(88, 'J')),  # 実施日
    source_worksheet.cell(87, 'O'),  # 実施者
    get_section_content(source_worksheet, '水平展開', '必要性'),  # 水平展開
    source_worksheet.cell(92, 'E'),  # 水平展開（予防）の必要性
    parse_date(source_worksheet.cell(92, 'J')),  # 実施日
    source_worksheet.cell(92, 'O'),  # 実施者
    get_section_content(source_worksheet, '処置活動のレビュー', nil, max_rows: 10),  # 処置活動のレビュー
    parse_date(source_worksheet.cell(96, 'I')),  # レビュー日
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
