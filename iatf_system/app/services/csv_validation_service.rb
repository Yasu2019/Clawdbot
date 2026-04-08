# frozen_string_literal: true

require 'csv'

class CsvValidationService
  attr_reader :errors

  def initialize(expected_headers: [], date_columns: [], numeric_columns: [])
    @expected_headers = expected_headers
    @date_columns = date_columns
    @numeric_columns = numeric_columns
    @errors = []
  end

  def validate_row(row, row_index)
    row_errors = []

    # 1. Column count check
    if @expected_headers.any? && row.length != @expected_headers.length
      row_errors << "Column count mismatch: expected #{@expected_headers.length}, got #{row.length}"
    end

    # 2. Date format check (YYYY-MM-DD HH:MM:SS or blank)
    @date_columns.each do |col|
      val = row[col].to_s.strip
      next if val.blank?

      unless val.match?(/\A\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\z/)
        row_errors << "Invalid date format in column '#{col}': '#{val}'"
      end
    end

    # 3. Numeric check
    @numeric_columns.each do |col|
      val = row[col].to_s.strip
      next if val.blank?

      begin
        Float(val)
      rescue ArgumentError
        row_errors << "Invalid numeric value in column '#{col}': '#{val}'"
      end
    end

    if row_errors.any?
      full_message = "Line #{row_index}: #{row_errors.join('; ')}"
      @errors << full_message
      false
    else
      true
    end
  end

  def self.attachedfile_validator
    new(
      expected_headers: %w[filename category partnumber materialcode phase stage description status documenttype documentname documentrev documentcategory documentnumber start_time deadline_at end_at goal_attainment_level tasseido object],
      date_columns: %w[start_time deadline_at end_at],
      numeric_columns: %w[goal_attainment_level tasseido]
    )
  end
end
