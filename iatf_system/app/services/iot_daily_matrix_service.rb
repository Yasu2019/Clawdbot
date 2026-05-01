# frozen_string_literal: true

require 'csv'
require 'date'
require 'set'

class IotDailyMatrixService
  IOT_DIR = '/myapp/db/record/iot'

  METRIC_PATTERNS = {
    shot: /\AShot(?<machine>.+)\.csv\z/i,
    spm: /\ASPM(?<machine>.+)\.csv\z/i,
    chokotei: /\A(?:Stamping)?chokotei(?<machine>.+)\.csv\z/i
  }.freeze

  def self.call(year: nil, month: nil)
    new(year:, month:).call
  end

  def initialize(year:, month:)
    today = Time.zone.today
    @year = normalize_integer(year, today.year)
    @month = normalize_month(month, today.month)
  end

  def call
    matrix = empty_matrix
    machines = Set.new

    each_monthly_file do |date, metric, machine, path|
      machines << machine
      values = load_values(path)

      matrix[metric][machine][date] =
        metric == :spm ? spm_stats(values) : cumulative_delta(values)
    end

    {
      year: @year,
      month: @month,
      dates: month_dates,
      machines: machines.to_a.sort,
      matrix: matrix
    }
  end

  private

  def normalize_integer(value, fallback)
    integer = value.to_i
    integer.positive? ? integer : fallback
  end

  def normalize_month(value, fallback)
    integer = value.to_i
    (1..12).cover?(integer) ? integer : fallback
  end

  def empty_matrix
    {
      chokotei: Hash.new { |hash, key| hash[key] = {} },
      shot: Hash.new { |hash, key| hash[key] = {} },
      spm: Hash.new { |hash, key| hash[key] = {} }
    }
  end

  def month_dates
    first_day = Date.new(@year, @month, 1)
    last_day = first_day.end_of_month
    (first_day..last_day).to_a
  end

  def each_monthly_file
    pattern = File.join(IOT_DIR, "#{format('%<year>04d_%<month>02d', year: @year, month: @month)}_*.csv")
    Dir.glob(pattern).each do |path|
      basename = File.basename(path)
      next unless basename =~ /\A(?<date>\d{4}_\d{2}_\d{2})(?<source>.+)\z/

      date_part = Regexp.last_match[:date]
      source = Regexp.last_match[:source]
      metric, machine = detect_metric(source)
      next if metric.nil?

      yield Date.strptime(date_part, '%Y_%m_%d'), metric, machine, path
    end
  end

  def detect_metric(source)
    METRIC_PATTERNS.each do |metric, pattern|
      match = source.match(pattern)
      return [metric, match[:machine]] if match
    end
    [nil, nil]
  end

  def load_values(path)
    values = []
    CSV.foreach(path, headers: false) do |row|
      cells = row.map { |cell| cell.to_s.strip }
      next if cells.empty? || cells.all?(&:blank?)

      value = cells.length >= 2 ? cells[1] : cells[0]
      numeric = numeric_value(value)
      values << numeric unless numeric.nil?
    end
    values
  rescue CSV::MalformedCSVError
    []
  end

  def numeric_value(value)
    Float(value)
  rescue ArgumentError, TypeError
    nil
  end

  def cumulative_delta(values)
    return nil if values.empty?

    delta = values.max - values.min
    delta.negative? ? 0 : delta.round
  end

  def spm_stats(values)
    samples = values.select(&:positive?)
    return nil if samples.empty?

    average = samples.sum / samples.size
    sigma = standard_deviation(samples, average)

    {
      max: samples.max.round(1),
      average: average.round(1),
      min: samples.min.round(1),
      plus_3sigma: (average + (3 * sigma)).round(1),
      minus_3sigma: [average - (3 * sigma), 0].max.round(1)
    }
  end

  def standard_deviation(values, average)
    variance = values.sum { |value| (value - average)**2 } / values.size
    Math.sqrt(variance)
  end
end
