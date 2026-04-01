# frozen_string_literal: true

class AttachedfileSeedImportService
  class << self
    def call(rows:)
      new(rows:).call
    end
  end

  def initialize(rows:)
    @rows = Array(rows).compact
  end

  def call
    imported = []
    skipped = []

    @rows.each do |row|
      filename = row.fetch("filename")
      if already_imported?(filename)
        skipped << filename
        next
      end

      imported << import_row(row)
    end

    {
      imported_count: imported.length,
      skipped_count: skipped.length,
      imported: imported,
      skipped: skipped
    }
  end

  private

  def already_imported?(filename)
    Product
      .joins(documents_attachments: :blob)
      .where(active_storage_blobs: { filename: filename })
      .exists?
  end

  def import_row(row)
    product = Product.new(
      category: row["category"],
      partnumber: row["partnumber"],
      materialcode: row["materialcode"],
      phase: row["phase"],
      stage: row["stage"],
      description: row["description"],
      status: row["status"],
      documenttype: row["documenttype"],
      documentname: row["documentname"],
      documentrev: row["documentrev"],
      documentcategory: row["documentcategory"],
      documentnumber: row["documentnumber"],
      start_time: row["start_time"],
      deadline_at: row["deadline_at"],
      end_at: row["end_at"],
      goal_attainment_level: row["goal_attainment_level"],
      tasseido: row["tasseido"],
      object: row["object"]
    )

    file_path = Rails.root.join("db/documents", row.fetch("filename"))
    raise "Document file not found: #{file_path}" unless File.file?(file_path)

    product.documents.attach(io: File.open(file_path, "rb"), filename: row.fetch("filename"))
    product.save!

    {
      product_id: product.id,
      filename: row.fetch("filename"),
      documentname: row["documentname"]
    }
  end
end
