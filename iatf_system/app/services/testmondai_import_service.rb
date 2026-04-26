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
  HEADERLESS_COLUMNS = %w[kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu].freeze

  def self.call(file)
    new(file).call
  end

  def initialize(file)
    @file = file
    @result = CsvImportResult.new
  end

  def call
    return missing_file_result unless file.present?

    parsed = parse_rows
    return result.error!("Unsupported quiz CSV format: #{File.basename(file.path)}") && result if parsed.nil?

    normalized_headers = parsed[:headers]
    missing = REQUIRED_COLUMNS - normalized_headers.values.compact.uniq
    if missing.any?
      result.error!("Missing required columns: #{missing.join(', ')}")
      return result
    end

    parsed[:rows].each_with_index do |row, index|
      import_row(row, normalized_headers, parsed[:row_offset] + index)
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

  def parse_rows
    content = File.read(file.path, mode: 'rb')
    decoded = decode_content(content)
    raw_rows = CSV.parse(decoded, headers: false)
    return nil if raw_rows.empty?

    header_map = normalize_headers(raw_rows.first)
    if quiz_headers?(header_map)
      return {
        headers: header_map,
        rows: raw_rows.drop(1),
        row_offset: 2
      }
    end

    if headerless_quiz_rows?(raw_rows)
      return {
        headers: HEADERLESS_COLUMNS.index_with { |column| column },
        rows: raw_rows,
        row_offset: 1
      }
    end

    nil
  end

  def decode_content(content)
    utf8 = content.dup.force_encoding('UTF-8')
    decoded = if utf8.valid_encoding?
                utf8
              else
                content.encode('UTF-8', 'CP932', invalid: :replace, undef: :replace, replace: '')
              end
    decoded.sub("\xEF\xBB\xBF".b.force_encoding('UTF-8'), '')
  rescue Encoding::UndefinedConversionError, Encoding::InvalidByteSequenceError
    content.encode('UTF-8', invalid: :replace, undef: :replace, replace: '')
  end

  def quiz_headers?(header_map)
    (header_map.values.compact.uniq & REQUIRED_COLUMNS).size >= 2
  end

  def headerless_quiz_rows?(rows)
    samples = rows.first(5).map { |row| Array(row).map { |value| value.to_s.strip } }
    return false if samples.empty?
    return false unless samples.all? { |sample| sample.size == HEADERLESS_COLUMNS.size }
    return false unless samples.count { |sample| sample[0].match?(/\A\d+(\.\d+)+\z/) } >= [samples.size, 2].min

    answer_index = HEADERLESS_COLUMNS.index('seikai')
    samples.count { |sample| sample[answer_index].downcase.match?(/\A[a-c]\z/) } >= [samples.size, 2].min
  end

  def import_row(row, normalized_headers, row_number)
    attrs = {}
    if row.is_a?(Array)
      normalized_headers.each_with_index do |(_, normalized), index|
        next if normalized.blank?

        attrs[normalized] = row[index].to_s.strip
      end
    else
      normalized_headers.each do |header, normalized|
        next if normalized.blank?

        attrs[normalized] = row[header].to_s.strip
      end
    end

    if REQUIRED_COLUMNS.any? { |column| attrs[column].blank? }
      result.error!("Row #{row_number}: required quiz fields are blank")
      return
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
