# frozen_string_literal: true

# データベースのクリーンアップ
puts "Cleaning up database..."

# ActiveStorageのアタッチメントを削除
ActiveStorage::Attachment.destroy_all
ActiveStorage::Blob.destroy_all

# 各モデルのデータを削除
Product.destroy_all
Phase.destroy_all
User.destroy_all
Measurementequipment.destroy_all
Supplier.destroy_all
Mitsui.destroy_all

puts "Database cleaned successfully!"

require 'csv'
require 'active_storage'

# ロガーの設定
Rails.logger = Logger.new(STDOUT)

# 製品データの処理
CSV.foreach(Rails.root.join('db/record/attachedfile.csv'), headers: true) do |row|
  product = Product.new
  product.category = row['category']
  product.partnumber = row['partnumber']
  product.materialcode = row['materialcode']
  product.phase = row['phase']
  product.stage = row['stage']
  product.description = row['description']
  product.status = row['status']
  product.documenttype = row['documenttype']
  product.documentname = row['documentname']
  product.documentrev = row['documentrev']
  product.documentcategory = row['documentcategory']
  product.documentnumber = row['documentnumber'].present? ? row['documentnumber'].strip : nil
  product.start_time = row['start_time']
  product.deadline_at = row['deadline_at']
  product.end_at = row['end_at']
  product.goal_attainment_level = row['goal_attainment_level']
  product.tasseido = row['tasseido']
  product.object = row['object']

  # ファイル添付処理
  if row['filename'].present?
    file_path = Rails.root.join("db/documents/#{row['filename']}")
    if File.file?(file_path)
      product.documents.attach(
        io: File.open(file_path),
        filename: row['filename']
      )
    else
      Rails.logger.debug { "Attached File not found: #{file_path}" }
    end
  else
    Rails.logger.debug 'Attached Filename is empty on csv data'
  end

  unless product.save
    Rails.logger.error "製品の保存に失敗しました。ドキュメント番号: #{product.documentnumber}。" \
                       "エラー: #{product.errors.full_messages.join(', ')}"
  end
end

# Phase データの更新
CSV.foreach('db/category.csv') do |row|
  phase = Phase.find_or_initialize_by(id: row[0])
  phase.update(name: row[1], ancestry: row[2])
end

# User データの更新
CSV.foreach('db/record/login.csv') do |row|
  user = User.find_or_initialize_by(id: row[0])
  user.update(email: row[1], password: row[2], name: row[3], role: row[4], owner: row[5], auditor: row[6])
end

# Measurementequipment データの作成
CSV.foreach('db/record/measurement_equipment.csv') do |row|
  measurementequipment = Measurementequipment.new
  measurementequipment.attributes = {
    categories: row[0],
    scope_of_internal_testing_laboratories: row[1],
    product_measurement_item: row[2],
    measuring_range: row[3],
    measuring_instrument_test_equipment: row[4],
    manufacturer: row[5],
    equipment_model_name: row[6],
    control_no: row[7],
    measurement_accuracy: row[8],
    reference_document_no: row[9],
    calibration_in_house_external: row[10],
    laboratory_environmental_conditions: row[11],
    external_calibration_laboratory: row[12],
    remarks: row[13]
  }
  measurementequipment.save
end

# Supplier データの作成と更新
CSV.foreach(Rails.root.join('db/record/suppliers.csv'), headers: true) do |row|
  supplier = Supplier.new
  supplier.attributes = {
    no: row[0],
    supplier_name: row[1],
    manufacturer_name: row[2],
    iso_existence: row[3],
    target: row[4],
    qms: row[5],
    second_party_audit: row[6],
    supplier_development: row[7],
    automotive_related: row[8],
    departments: row[9],
    transaction_details: row[10],
    address1: row[11],
    address2: row[12],
    postal_code: row[13],
    tel: row[14],
    fax: row[15],
    filename: row[16],
    document_name: row[17],
    issue_date: row[18],
    feedback_date: row[19]
  }
  supplier.save

  if row['filename'].present? && row['document_name'].present?
    filenames = row['filename'].split(',').map(&:strip)
    document_names = row['document_name'].split(',').map(&:strip)

    filenames.zip(document_names).each do |filename, document_name|
      file_path = Rails.root.join("db/documents/#{filename}")
      if File.file?(file_path)
        blob = ActiveStorage::Blob.create_and_upload!(io: File.open(file_path), filename: filename)
        supplier.documents.attach(blob)
        supplier.document_name = document_name
      else
        Rails.logger.info "ファイルが見つかりません: #{file_path}"
      end
    end
  else
    Rails.logger.info 'Supplier_File_name is empty' if row['filename'].blank?
    Rails.logger.info 'Supplier_Document_name is empty' if row['document_name'].blank?
  end

  supplier.save
end

# Iatf データの作成
CSV.foreach('db/record/iatf_request_list.csv') do |row|
  Iatf.create(
    no: row[0],
    name: row[1],
    sales: row[2],
    process_design: row[3],
    production: row[4],
    inspection: row[5],
    release: row[6],
    procurement: row[7],
    equipment: row[8],
    measurement: row[9],
    policy: row[10],
    satisfaction: row[11],
    audit: row[12],
    corrective_action: row[13]
  )
end

# CSR データの作成
CSV.foreach('db/record/mek_csr_list.csv') do |row|
  Csr.create(csr_number: row[0], csr_content: row[1])
end

# Mitsui データの作成
CSV.foreach('db/record/mitsui_kajyou_list.csv') do |row|
  Mitsui.create(mitsui_number: row[0], mitsui_content: row[1])
end

# Iatflist データの作成
CSV.foreach('db/record/iatf_kajyou_list.csv') do |row|
  Iatflist.create(iatf_number: row[0], iatf_content: row[1])
end

# テスト問題データの作成
Dir.glob('db/record/bing/kajyou*.csv') do |file|
  CSV.foreach(file) do |row|
    Testmondai.create(
      kajyou: row[0],
      mondai_no: row[1],
      rev: row[2],
      mondai: row[3],
      mondai_a: row[4],
      mondai_b: row[5],
      mondai_c: row[6],
      seikai: row[7],
      kaisetsu: row[8]
    )
  end
end