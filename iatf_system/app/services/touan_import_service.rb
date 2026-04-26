# frozen_string_literal: true

require 'csv'

class TouanImportService
  HEADER_ALIASES = {
    'id' => 'id',
    'kajyou' => 'kajyou',
    'mondai_no' => 'mondai_no',
    'mondaino' => 'mondai_no',
    'rev' => 'rev',
    'mondai' => 'mondai',
    'mondai_a' => 'mondai_a',
    'mondai_b' => 'mondai_b',
    'mondai_c' => 'mondai_c',
    'seikai' => 'seikai',
    'kaisetsu' => 'kaisetsu',
    'kaito' => 'kaito',
    'user_id' => 'user_id',
    'total_answers' => 'total_answers',
    'correct_answers' => 'correct_answers',
    'seikairitsu' => 'seikairitsu'
  }.freeze

  REQUIRED_COLUMNS = %w[kajyou mondai_no kaito user_id].freeze

  def self.call(file)
    new(file).call
  end

  def initialize(file)
    @file = file
    @result = CsvImportResult.new
  end

  def call
    return missing_file_result unless file.present?

    csv = CSV.read(file.path, headers: true, encoding: 'bom|utf-8')
    normalized_headers = normalize_headers(csv.headers)
    missing = REQUIRED_COLUMNS - normalized_headers.values.compact.uniq
    if missing.any?
      result.error!("Missing required columns: #{missing.join(', ')}")
      return result
    end

    csv.each_with_index do |row, index|
      import_row(row, normalized_headers, index + 2)
    end

    result
  rescue CSV::MalformedCSVError => e
    result.error!("Malformed CSV: #{e.message}")
    result
  end

  private

  attr_reader :file, :result

  def missing_file_result
    result.error!('No CSV file was provided')
    result
  end

  def normalize_headers(headers)
    headers.each_with_object({}) do |header, map|
      key = header.to_s.encode('UTF-8', invalid: :replace, undef: :replace, replace: '').strip.downcase
      map[header] = HEADER_ALIASES[key]
    end
  end

  def import_row(row, normalized_headers, row_number)
    attrs = normalized_headers.each_with_object({}) do |(header, normalized), memo|
      next if normalized.blank?

      memo[normalized] = row[header].to_s.strip
    end

    record = attrs['id'].present? ? (Touan.find_by(id: attrs['id']) || Touan.new) : Touan.new
    was_persisted = record.persisted?
    record.assign_attributes(attrs.slice(*Touan.updatable_attributes))
    record.save!
    was_persisted ? result.updated! : result.imported!
  rescue StandardError => e
    result.error!("Row #{row_number}: #{e.message}")
  end
end
