# app/controllers/suppliers_controller.rb
# frozen_string_literal: true

require "csv"
require "fileutils"
require "json"
require "roo"

class SuppliersController < ApplicationController
  before_action :set_supplier, only: %i[show edit update destroy verify_password]
  before_action :load_supplier_workbook, only: %i[workbooks]
  before_action :load_upload_status, only: %i[uploads]

  SUPPLIER_SOURCE_DIR = Rails.root.join("db/record/supplier_sources")
  SUPPLIER_SOURCE_FILES = {
    list: {
      param: :supplier_list_file,
      stored_name: "供給者リスト.xlsx",
      label: "供給者リスト",
      output: :list
    },
    management_plan: {
      param: :management_plan_file,
      stored_name: "2025●供給者管理計画／実績表(KGM017).xlsx",
      label: "管理計画／実績",
      output: :management_plan
    },
    evaluation: {
      param: :evaluation_file,
      stored_name: "●供給者評価表・供給者再評価記録台帳2025.xls",
      label: "評価表／再評価台帳",
      output: :evaluation
    }
  }.freeze

  # GET /suppliers
  def index
    @suppliers = Supplier.includes(documents_attachments: :blob).all
  end

  def workbooks
    @dataset = params[:dataset] == "evaluation" ? "evaluation" : "management_plan"
    @summary = @workbook.fetch("summary", {})
    @sheets = @workbook.fetch("sheets")
    if @dataset == "evaluation"
      @primary_sheets = @sheets.first(5)
      @detail_sheets = @sheets.drop(5)
    else
      @primary_sheets = @sheets
      @detail_sheets = []
    end
    @active_sheet_name = params[:sheet].presence || @sheets.first.fetch("name")
    @active_sheet = @sheets.find { |sheet| sheet.fetch("name") == @active_sheet_name } || @sheets.first
    @active_sheet_name = @active_sheet.fetch("name")
    @active_rows = @active_sheet.fetch("rows")
  end

  def download_excel
    source_path = supplier_source_file_path(params[:dataset])

    unless File.exist?(source_path)
      redirect_back fallback_location: index_suppliers_path, alert: "Excel file not found."
      return
    end

    send_file source_path, filename: File.basename(source_path), disposition: "attachment"
  end

  def uploads; end

  def upload_sources
    uploaded = store_uploaded_supplier_files
    if uploaded.empty?
      redirect_to uploads_suppliers_path, alert: "3つのうち少なくとも1ファイルを選択してください。"
      return
    end

    results = {}
    csv_path = Rails.root.join("db/record/suppliers.csv")

    if uploaded[:list]
      export_supplier_list_csv(source_path: supplier_source_file_path(nil), csv_path: csv_path)
      results[:list] = SupplierCsvImportService.call(csv_path: csv_path)
    end

    if uploaded[:management_plan]
      SupplierWorkbookExportService.export!(
        dataset: :management_plan,
        source_path: supplier_source_file_path("management_plan"),
        output_dir: Rails.root.join("db/record")
      )
      results[:management_plan] = "refreshed"
    end

    if uploaded[:evaluation]
      SupplierWorkbookExportService.export!(
        dataset: :evaluation,
        source_path: supplier_source_file_path("evaluation"),
        output_dir: Rails.root.join("db/record")
      )
      results[:evaluation] = "refreshed"
    end

    results[:seed_sync] = SupplierSeedSyncService.call

    status_payload = {
      uploaded: uploaded.transform_values { |item| item.is_a?(Hash) ? item.slice(:filename, :size) : item },
      results: results,
      updated_at: Time.zone.now.iso8601
    }
    upload_status_path.write(JSON.pretty_generate(status_payload))

    messages = []
    if results[:list]
      messages << "供給者リストを更新しました（#{results[:list][:imported_rows]}行）"
    end
    messages << "管理計画／実績を再生成しました" if results[:management_plan]
    messages << "評価表／再評価台帳を再生成しました" if results[:evaluation]
    messages << "seed 資産も更新しました" if results[:seed_sync]

    redirect_to uploads_suppliers_path, notice: messages.join(" / ")
  rescue StandardError => e
    redirect_to uploads_suppliers_path, alert: "更新に失敗しました: #{e.message}"
  end

  # GET /suppliers/1
  def show; end

  # GET /suppliers/new
  def new
    @supplier = Supplier.new
  end

  # GET /suppliers/1/edit
  def edit; end

  # POST /suppliers
  def create
    @supplier = Supplier.new(supplier_params)

    if @supplier.save
      redirect_to @supplier, notice: 'Supplier was successfully created.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  # PATCH/PUT /suppliers/1
  def update
    if @supplier.update(supplier_params)
      redirect_to @supplier, notice: 'Supplier was successfully updated.'
    else
      render :edit, status: :unprocessable_entity
    end
  end

  # DELETE /suppliers/1
  def destroy
    @supplier.destroy
    redirect_to suppliers_url, notice: 'Supplier was successfully destroyed.'
  end

  # GET /suppliers/1/verify_password/:blob_id
  def verify_password
    # ここにパスワード確認のロジックを追加します
    # 例: @supplier.verify_password(params[:blob_id])
  end

  private

  # Use callbacks to share common setup or constraints between actions.
  def set_supplier
    @supplier = Supplier.find(params[:id])
  end

  # Only allow a list of trusted parameters through.
  def supplier_params
    params.require(:supplier).permit(:supplier_name, :manufacturer_name, :iso_existence, :target, :qms, :development,
                                     :second_party_audit, :supplier_development, :automotive_related, :departments, :department, :transaction_details, :address1, :address2, :postal_code, :tel, :fax, :filename, :document_name, :issue_date, :feedback_date, :no, documents: [])
  end

  def load_supplier_workbook
    filename = params[:dataset] == "evaluation" ? "supplier_evaluation_2025.json" : "supplier_management_plan_2025.json"
    path = Rails.root.join("db/record/#{filename}")
    @workbook = JSON.parse(File.read(path, encoding: "utf-8"))
  end

  def supplier_source_file_path(dataset)
    key =
      case dataset
      when "management_plan" then :management_plan
      when "evaluation" then :evaluation
      else :list
      end
    SUPPLIER_SOURCE_DIR.join(SUPPLIER_SOURCE_FILES.fetch(key).fetch(:stored_name))
  end

  def store_uploaded_supplier_files
    SUPPLIER_SOURCE_DIR.mkpath
    uploaded = {}

    SUPPLIER_SOURCE_FILES.each do |key, config|
      file = params[config.fetch(:param)]
      next unless file.respond_to?(:original_filename)

      target_path = SUPPLIER_SOURCE_DIR.join(config.fetch(:stored_name))
      backup_existing_source_file(target_path)
      File.binwrite(target_path, file.read)
      uploaded[key] = {
        filename: file.original_filename,
        size: file.size,
        stored_path: target_path.to_s
      }
    end

    uploaded
  end

  def export_supplier_list_csv(source_path:, csv_path:)
    workbook = Roo::Spreadsheet.open(source_path.to_s)
    sheet = workbook.sheet("Sheet1")
    headers = SupplierCsvImportService::UPDATABLE_FIELDS.map(&:to_s)
    existing_attachment_map = existing_supplier_attachment_map(csv_path)

    CSV.open(csv_path, "w:bom|utf-8", write_headers: true, headers: headers) do |csv|
      (7..sheet.last_row).each do |row_index|
        row = sheet.row(row_index)
        no = normalize_excel_cell(row[1])
        supplier_name = normalize_excel_cell(row[2])
        manufacturer_name = normalize_excel_cell(row[3])
        next if [no, supplier_name, manufacturer_name].all?(&:blank?)

        attachment_attrs = existing_attachment_map[[no.to_s.strip, supplier_name.to_s.strip, manufacturer_name.to_s.strip]] || {}

        csv << {
          "no" => no,
          "supplier_name" => supplier_name,
          "manufacturer_name" => manufacturer_name,
          "iso_existence" => normalize_excel_cell(row[8]),
          "target" => normalize_excel_cell(row[11]),
          "qms" => normalize_excel_cell(row[12]),
          "second_party_audit" => normalize_excel_cell(row[13]),
          "supplier_development" => normalize_excel_cell(row[14]),
          "automotive_related" => normalize_excel_cell(row[17]),
          "departments" => normalize_excel_cell(row[18]),
          "transaction_details" => normalize_excel_cell(row[19]),
          "address1" => normalize_excel_cell(row[23]),
          "address2" => normalize_excel_cell(row[24]),
          "postal_code" => normalize_excel_cell(row[25]),
          "tel" => normalize_excel_cell(row[26]),
          "fax" => normalize_excel_cell(row[27]),
          "filename" => attachment_attrs["filename"].to_s,
          "document_name" => attachment_attrs["document_name"].to_s,
          "issue_date" => attachment_attrs["issue_date"].to_s,
          "feedback_date" => attachment_attrs["feedback_date"].to_s
        }.values_at(*headers)
      end
    end
  end

  def existing_supplier_attachment_map(csv_path)
    return {} unless File.exist?(csv_path)

    CSV.read(csv_path, headers: true, encoding: "bom|utf-8").each_with_object({}) do |row, memo|
      key = [row["no"].to_s.strip, row["supplier_name"].to_s.strip, row["manufacturer_name"].to_s.strip]
      memo[key] = {
        "filename" => row["filename"],
        "document_name" => row["document_name"],
        "issue_date" => row["issue_date"],
        "feedback_date" => row["feedback_date"]
      }
    end
  rescue StandardError
    {}
  end

  def normalize_excel_cell(value)
    return "" if value.nil?
    return value.strftime("%Y-%m-%d") if value.respond_to?(:strftime)
    return value.to_i.to_s if value.is_a?(Float) && value.to_i == value

    value.to_s.strip
  end

  def upload_status_path
    Rails.root.join("db/record/supplier_sources/upload_status.json")
  end

  def backup_existing_source_file(path)
    return unless File.exist?(path)

    backup_dir = SUPPLIER_SOURCE_DIR.join("backups")
    backup_dir.mkpath
    timestamp = Time.zone.now.strftime("%Y%m%d_%H%M%S")
    FileUtils.cp(path, backup_dir.join("#{timestamp}_#{path.basename}"))
  end

  def load_upload_status
    @upload_status =
      if File.exist?(upload_status_path)
        JSON.parse(File.read(upload_status_path, encoding: "utf-8"))
      else
        {}
      end
  end
end
