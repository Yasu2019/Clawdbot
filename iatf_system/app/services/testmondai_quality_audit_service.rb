# frozen_string_literal: true

require 'csv'
require 'pathname'

class TestmondaiQualityAuditService
  REQUIRED_COLUMNS = %w[kajyou mondai_no mondai mondai_a mondai_b mondai_c seikai].freeze
  HEADERLESS_COLUMNS = %w[kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu].freeze
  MOJIBAKE_MARKERS = %w[邵ｺ 郢ｧ 闕ｳ 陷ｿ 鬩・陞ｳ 髯ｦ 髫ｪ・ｭ 髫補扱・ｱ].freeze
  QUIZ_PATH_HINTS = %w[test mondai kajyou].freeze

  def self.call(paths)
    new(paths).call
  end

  def initialize(paths)
    @paths = Array(paths).map { |path| Pathname(path) }.uniq
  end

  def call
    skipped_files = []
    reports = @paths.filter_map do |path|
      next unless path.file?
      next unless path.extname.downcase == '.csv'

      report = audit_file(path)
      if report[:skipped]
        skipped_files << report
        next
      end

      report
    end

    {
      scanned_files: reports.size,
      skipped_files: skipped_files.size,
      total_rows: reports.sum { |report| report[:row_count] },
      total_issues: reports.sum { |report| report[:issue_count] },
      files: reports.sort_by { |report| [-report[:issue_count], report[:path]] },
      skipped: skipped_files.sort_by { |report| report[:path] }
    }
  end

  private

  def audit_file(path)
    parsed = parse_csv(path)

    if parsed[:skipped_reason]
      return {
        path: path.to_s,
        skipped: true,
        reason: parsed[:skipped_reason]
      }
    end

    missing_columns = REQUIRED_COLUMNS - parsed[:headers]
    issues = []

    parsed[:rows].each_with_index do |row, index|
      issues.concat(row_issues(path:, row:, row_number: index + 2))
    end

    unless missing_columns.empty?
      issues << {
        type: 'missing_columns',
        row_number: 1,
        message: "Missing required columns: #{missing_columns.join(', ')}"
      }
    end

    {
      path: path.to_s,
      skipped: false,
      row_count: parsed[:rows].size,
      issue_count: issues.size,
      issues:
    }
  rescue StandardError => e
    {
      path: path.to_s,
      skipped: false,
      row_count: 0,
      issue_count: 1,
      issues: [{ type: 'parse_error', row_number: 1, message: e.message }]
    }
  end

  def parse_csv(path)
    content = File.read(path, mode: 'rb')
    decoded = decode_content(content)
    raw_rows = CSV.parse(decoded, headers: false)
    return skipped_result('empty_csv') if raw_rows.empty?

    if headered_quiz_csv?(raw_rows)
      headers = normalized_headers(raw_rows.first)
      return {
        headers:,
        rows: raw_rows.drop(1).map { |row| build_row_hash(headers, row) },
        skipped_reason: nil
      }
    end

    if headerless_quiz_csv?(path, raw_rows)
      return {
        headers: HEADERLESS_COLUMNS,
        rows: raw_rows.map { |row| build_row_hash(HEADERLESS_COLUMNS, row) },
        skipped_reason: nil
      }
    end

    skipped_result('not_quiz_csv')
  end

  def decode_content(content)
    utf8 = content.dup.force_encoding('UTF-8')
    return utf8 if utf8.valid_encoding?

    content.encode('UTF-8', 'CP932', invalid: :replace, undef: :replace, replace: '')
  rescue Encoding::UndefinedConversionError, Encoding::InvalidByteSequenceError
    content.encode('UTF-8', invalid: :replace, undef: :replace, replace: '')
  end

  def row_issues(path:, row:, row_number:)
    issues = []

    mondai = normalized_text(row['mondai'])
    kaisetsu = normalized_text(row['kaisetsu'])
    answers = %w[mondai_a mondai_b mondai_c].map { |key| normalized_text(row[key]) }
    seikai = normalized_text(row['seikai']).downcase

    issues << issue(row_number, 'blank_question', 'Question text is blank') if mondai.empty?
    issues << issue(row_number, 'short_question', 'Question text is too short') if mondai.length.positive? && mondai.length < 15
    issues << issue(row_number, 'blank_explanation', 'Explanation is blank') if kaisetsu.empty?
    issues << issue(row_number, 'short_explanation', 'Explanation is too short') if kaisetsu.length.positive? && kaisetsu.length < 20
    issues << issue(row_number, 'invalid_seikai', "Invalid seikai: #{seikai.inspect}") unless %w[a b c].include?(seikai)

    duplicate_answers = answers.reject(&:empty?).group_by(&:itself).select { |_value, grouped| grouped.size > 1 }.keys
    unless duplicate_answers.empty?
      issues << issue(row_number, 'duplicate_choices', "Duplicate choices: #{duplicate_answers.join(' / ')}")
    end

    [mondai, kaisetsu, *answers].each do |field|
      next if field.empty?
      next unless looks_mojibake?(field)

      issues << issue(row_number, 'mojibake_suspected', 'Text appears mojibake or wrongly encoded')
      break
    end

    issues << issue(row_number, 'missing_rev', 'Revision is placeholder "-"') if normalized_text(row['rev']) == '-'

    issues.map do |entry|
      entry.merge(
        path: path.to_s,
        kajyou: normalized_text(row['kajyou']),
        mondai_no: normalized_text(row['mondai_no'])
      )
    end
  end

  def headered_quiz_csv?(rows)
    headers = normalized_headers(rows.first)
    (headers & REQUIRED_COLUMNS).size >= 4
  end

  def headerless_quiz_csv?(path, rows)
    return false unless path_quiz_like?(path)

    samples = rows.first(5).map { |row| normalized_values(row) }
    return false if samples.empty?
    return false unless samples.all? { |sample| sample.size == HEADERLESS_COLUMNS.size }
    return false unless samples.count { |sample| sample[0].match?(/\A\d+(\.\d+)+\z/) } >= [samples.size, 2].min
    return false unless samples.count { |sample| sample[1].match?(/\A[\w.-]+\z/) } >= [samples.size, 2].min

    answer_index = HEADERLESS_COLUMNS.index('seikai')
    samples.count { |sample| sample[answer_index].downcase.match?(/\A[a-c]\z/) } >= [samples.size, 2].min
  end

  def path_quiz_like?(path)
    lowered = path.to_s.downcase
    QUIZ_PATH_HINTS.any? { |hint| lowered.include?(hint) }
  end

  def normalized_headers(row)
    normalized_values(row).map { |header| header.delete_prefix("\uFEFF").downcase }
  end

  def normalized_values(row)
    values = row.respond_to?(:fields) ? row.fields : Array(row)
    values.map { |value| normalized_text(value) }
  end

  def build_row_hash(headers, row)
    headers.zip(normalized_values(row)).to_h
  end

  def skipped_result(reason)
    {
      headers: [],
      rows: [],
      skipped_reason: reason
    }
  end

  def normalized_text(value)
    value.to_s.strip.gsub(/\s+/, ' ')
  end

  def looks_mojibake?(text)
    marker_hits = MOJIBAKE_MARKERS.count { |marker| text.include?(marker) }
    replacement_ratio = text.count('・ｽ').to_f / [text.length, 1].max

    marker_hits >= 2 || replacement_ratio > 0.02
  end

  def issue(row_number, type, message)
    {
      row_number:,
      type:,
      message:
    }
  end
end
