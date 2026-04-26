# frozen_string_literal: true

class CsvImportResult
  attr_reader :imported_count, :updated_count, :error_count, :errors

  def initialize
    @imported_count = 0
    @updated_count = 0
    @error_count = 0
    @errors = []
  end

  def imported!
    @imported_count += 1
  end

  def updated!
    @updated_count += 1
  end

  def error!(message)
    @error_count += 1
    @errors << message
  end

  def success?
    error_count.zero?
  end

  def summary
    "imported=#{imported_count}, updated=#{updated_count}, errors=#{error_count}"
  end
end
