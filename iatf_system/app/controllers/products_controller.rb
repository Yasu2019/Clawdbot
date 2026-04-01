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

  include ExcelTemplateHelper

  def in_process_nonconforming_product_control_form
    send_data(
      InProcessNonconformingExcelService.call,
      filename: '品質管理票.xlsx',
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  end

  def audit_followup_status
    @audit_followup = AuditFollowupStatusService.call
    @available_audit_years = collect_audit_years(@audit_followup)
    @selected_audit_year = params[:year].presence&.to_i
    filter_audit_followup!(@selected_audit_year) if @selected_audit_year.present?
  end

  def document_reconciliation
    @document_reconciliation = DocumentReconciliationService.call
  end

  def process_monitoring_measurement
    @process_monitoring_measurement = ProcessMonitoringMeasurementService.call
    @available_monitoring_years = @process_monitoring_measurement[:available_years] || [2024, 2025]
    @selected_monitoring_year = params[:year].presence&.to_i || 2024
  end

  def update_history
    @update_history = UpdateHistoryService.call
  end

  def audit_followup_status_excel
    payload = AuditFollowupStatusService.call
    selected_year = params[:year].presence&.to_i

    send_data(
      AuditFollowupExportService.call(payload: payload, selected_year: selected_year),
      filename: selected_year.present? ? "audit_followup_status_#{selected_year}.xlsx" : "audit_followup_status_all_years.xlsx",
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
  end

  def upload_jqa_audit_reports
    files = Array(params[:jqa_reports]).compact
    if files.empty?
      redirect_to audit_followup_status_product_path(year: params[:year]), alert: "JQA審査報告書を選択してください。"
      return
    end

    result = JqaAuditReportIngestService.call(files: files)
    redirect_to(
      audit_followup_status_product_path(year: params[:year]),
      notice: "JQA審査報告書 #{result[:imported_count]} 件を登録しました。category=2 の文書として attachedfile.csv と Product Documents に反映しています。"
    )
  rescue StandardError => e
    redirect_to(
      audit_followup_status_product_path(year: params[:year]),
      alert: "JQA審査報告書の取り込みに失敗しました: #{e.message}"
    )
  end


  def audit_improvement_opportunity
    send_data(
      AuditImprovementOpportunityService.call,
      filename: 'audit_improvement_opportunity_list.xlsx',
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  end
  
  
  
  
  
  
  
  
  
  def audit_correction_report
    send_data(
      AuditCorrectionReportService.call,
      filename: 'audit_correction_report.xlsx',
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  end











  def export_phases_to_excel
    Rails.logger.debug "Starting export_phases_to_excel method"
    phase  # @dropdownlistを設定するためにphaseメソッドを呼び出す
    @products = Product.all

    xlsx_data = ExportPhasesToExcelService.call(products: @products, dropdownlist: @dropdownlist)
    send_data(
      style_exported_workbook(xlsx_data),
      filename: 'phases_data.xlsx',
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
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
    IotDataService.call.each do |key, value|
      instance_variable_set("@#{key}", value) unless value.nil?
    end
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

  def create_data
    ProductCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist
    ).each { |key, value| instance_variable_set("@#{key}", value) }
  end

  def create_data_apqp_plan_report
    ApqpPlanCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist,
      partnumber:   params[:partnumber]
    ).each { |key, value| instance_variable_set("@#{key}", value) }
  end

  def create_data_apqp_approved_report
    ApqpApprovedCreateDataService.call(
      products:     @products,
      all_products: @all_products,
      dropdownlist: @dropdownlist,
      partnumber:   params[:partnumber]
    ).each { |key, value| instance_variable_set("@#{key}", value) }
  end
  def generate_xlsx
    send_data(
      GenerateXlsxService.call(products: @products, dropdownlist: @dropdownlist),
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
    if file_name =~ /([A-Za-z]+)[_-](\d{4})[_-]ja\.pdf$/
      month_name = ::Regexp.last_match(1) # "May"
      year = ::Regexp.last_match(2).to_i # "2022"

      # 月の名前を数字に変換（フルネーム "November" と略称 "Nov" の両方に対応）
      month = Date::MONTHNAMES.index(month_name.capitalize) ||
              Date::ABBR_MONTHNAMES.index(month_name.capitalize)

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

  def style_exported_workbook(binary_data)
    workbook = RubyXL::Parser.parse_buffer(binary_data)

    workbook.worksheets.each do |worksheet|
      max_col = 0
      max_row = 0
      worksheet.sheet_data.rows.each_with_index do |row, row_idx|
        next unless row

        row.cells.each_with_index do |cell, col_idx|
          next unless cell

          max_col = [max_col, col_idx].max
        end
        max_row = [max_row, row_idx].max
      end

      (0..max_row).each do |row_idx|
        (0..max_col).each do |col_idx|
          row = worksheet[row_idx]
          cell = (row && row[col_idx]) || worksheet.add_cell(row_idx, col_idx, '')
          cell.change_text_wrap(true)
          cell.change_vertical_alignment('top')
          %w[top bottom left right].each do |direction|
            cell.change_border(direction, 'thin')
          end
        end
      end

      (0..max_col).each do |col|
        worksheet.change_column_width(col, 18)
      end
    end

    workbook.stream.string
  end

  def collect_audit_years(payload)
    years = []
    [:audit_corrections, :audit_opportunities, :nonconformities].each do |section_key|
      Array(payload.dig(section_key, :entries)).each do |entry|
        year = [entry[:due_date], entry[:completed_on]].find { |value| value.respond_to?(:year) }&.year
        years << year if year.present?
      end
    end
    Array(payload[:jqa_yearly_matrix]).each do |row|
      years << row[:year].to_i if row[:year].present?
    end
    years.compact.uniq.sort.reverse
  end

  def filter_audit_followup!(selected_year)
    [:audit_corrections, :audit_opportunities, :nonconformities].each do |section_key|
      section = @audit_followup[section_key] || {}
      entries = Array(section[:entries]).select do |entry|
        [entry[:due_date], entry[:completed_on]].find { |value| value.respond_to?(:year) }&.year == selected_year
      end
      counts = Hash.new(0)
      entries.each { |entry| counts[entry[:status]] += 1 }
      @audit_followup[section_key] = section.merge(entries: entries, total: entries.length, counts: counts)
    end

    @audit_followup[:jqa_yearly_matrix] = Array(@audit_followup[:jqa_yearly_matrix]).select do |row|
      row[:year].to_i == selected_year
    end
  end
end
