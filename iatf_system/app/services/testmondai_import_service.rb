# frozen_string_literal: true

require 'csv'

class TestmondaiImportService
  HEADER_ALIASES = {
    'id' => 'id',
    'kajyou' => 'kajyou',
    'kajyo' => 'kajyou',
    'mondai_no' => 'mondai_no',
    'mondaino' => 'mondai_no',
    'mondai no' => 'mondai_no',
    'rev' => 'rev',
    'mondai' => 'mondai',
    'question' => 'mondai',
    'mondai_a' => 'mondai_a',
    'choice_a' => 'mondai_a',
    'mondai_b' => 'mondai_b',
    'choice_b' => 'mondai_b',
    'mondai_c' => 'mondai_c',
    'choice_c' => 'mondai_c',
    'seikai' => 'seikai',
    'answer' => 'seikai',
    'kaisetsu' => 'kaisetsu',
    'explanation' => 'kaisetsu'
  }.freeze

  REQUIRED_COLUMNS = %w[kajyou mondai_no mondai mondai_a mondai_b mondai_c seikai].freeze

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

    unless %w[a b c].include?(attrs['seikai'])
      result.error!("Row #{row_number}: seikai must be one of a/b/c")
      return
    end

    record = find_target_record(attrs)
    was_persisted = record.persisted?
    record.assign_attributes(attrs.slice(*Testmondai.updatable_attributes))
    record.save!
    was_persisted ? result.updated! : result.imported!
  rescue StandardError => e
    result.error!("Row #{row_number}: #{e.message}")
  end

  def find_target_record(attrs)
    if attrs['id'].present?
      Testmondai.find_by(id: attrs['id']) ||
        Testmondai.find_or_initialize_by(kajyou: attrs['kajyou'], mondai_no: attrs['mondai_no'], rev: attrs['rev'])
    else
      Testmondai.find_or_initialize_by(kajyou: attrs['kajyou'], mondai_no: attrs['mondai_no'], rev: attrs['rev'])
    end
  end
end
