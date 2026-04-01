# frozen_string_literal: true

require "csv"

class SupplierCsvImportService
  KEY_FIELDS = %i[no supplier_name manufacturer_name].freeze
  UPDATABLE_FIELDS = %i[
    no
    supplier_name
    manufacturer_name
    iso_existence
    target
    qms
    second_party_audit
    supplier_development
    automotive_related
    departments
    transaction_details
    address1
    address2
    postal_code
    tel
    fax
    filename
    document_name
    issue_date
    feedback_date
  ].freeze

  class << self
    def call(csv_path:)
      rows = CSV.read(csv_path, headers: true, encoding: "bom|utf-8")

      existing = Supplier.all.index_by { |supplier| key_for_record(supplier) }
      matched_ids = []
      created = 0
      updated = 0
      migrated_with_docs = 0
      removed = 0
      preserved_with_docs = []

      Supplier.transaction do
        rows.each do |row|
          attrs = row.to_h.slice(*UPDATABLE_FIELDS.map(&:to_s)).transform_values { |value| value.to_s.strip }
          key = key_for_hash(attrs)
          supplier = existing[key]

          if supplier
            supplier.update!(attrs)
            matched_ids << supplier.id
            updated += 1
          else
            supplier = Supplier.create!(attrs)
            existing[key] = supplier
            matched_ids << supplier.id
            created += 1
          end
        end

        Supplier.where.not(id: matched_ids.uniq).find_each do |supplier|
          if supplier.documents.attached?
            candidate_scope = Supplier.where(id: matched_ids.uniq, no: supplier.no)
            if candidate_scope.count == 1
              target = candidate_scope.first
              ActiveStorage::Attachment.where(record_type: "Supplier", record_id: supplier.id)
                                       .update_all(record_id: target.id)
              supplier.destroy!
              migrated_with_docs += 1
              next
            end

            preserved_with_docs << {
              id: supplier.id,
              no: supplier.no,
              supplier_name: supplier.supplier_name,
              manufacturer_name: supplier.manufacturer_name,
              docs: supplier.documents.count
            }
            next
          end

          supplier.destroy!
          removed += 1
        end
      end

      {
        imported_rows: rows.size,
        updated: updated,
        created: created,
        migrated_with_docs: migrated_with_docs,
        removed_without_docs: removed,
        preserved_with_docs: preserved_with_docs
      }
    end

    private

    def key_for_record(record)
      KEY_FIELDS.map { |field| record.public_send(field).to_s.strip }
    end

    def key_for_hash(hash)
      KEY_FIELDS.map { |field| hash[field.to_s].to_s.strip }
    end
  end
end
