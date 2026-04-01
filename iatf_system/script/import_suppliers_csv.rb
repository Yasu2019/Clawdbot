# frozen_string_literal: true

require "json"
require Rails.root.join("app/services/supplier_csv_import_service")

csv_relative_path = ARGV[0] || "db/record/suppliers.csv"
csv_path = Rails.root.join(csv_relative_path)

unless File.exist?(csv_path)
  warn "CSV not found: #{csv_path}"
  exit 1
end

result = SupplierCsvImportService.call(csv_path: csv_path)
puts JSON.generate(result.merge(csv_path: csv_relative_path))
