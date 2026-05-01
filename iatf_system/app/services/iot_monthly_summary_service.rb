# frozen_string_literal: true

require 'csv'
require 'date'
require 'set'

class IotMonthlySummaryService
  IOT_DIR = '/myapp/db/record/iot'
  DEFAULT_WORK_HOURS_PER_DAY = 8.0
  RUNNING_THRESHOLD = 0.0

  METRIC_PATTERNS = {
    shot: /\AShot(?<machine>.+)\.csv\z/i,
    spm: /\ASPM(?<machine>.+)\.csv\z/i,
    chokotei: /\A(?:Stamping)?chokotei(?<machine>.+)\.csv\z/i,
    jyotai: /\A(?:Stamping)?JYOTAI(?<machine>.+)\.csv\z/i
  }.freeze

  def self.call(month: nil, work_hours_per_day: DEFAULT_WORK_HOURS_PER_DAY)
    new(month:, work_hours_per_day:).call
  end

  def initialize(month:, work_hours_per_day:)
    @month = parse_month(month)
    @work_hours_per_day = normalize_work_hours(work_hours_per_day)
  end

  def call
    machine_data = Hash.new { |hash, key| hash[key] = empty_machine_data }

    each_monthly_file do |date, metric, machine, path|
      machine_data[machine][:days] << date
      machine_data[machine][metric].concat(load_points(path))
    end

    rows = machine_data.map do |machine, data|
      build_row(machine, data)
    end.sort_by { |row| row[:machine] }

    {
      month: @month,
      work_hours_per_day: @work_hours_per_day,
      rows: rows,
      totals: build_totals(rows)
    }
  end

  private

  def parse_month(value)
    return Time.zone.today.beginning_of_month if value.blank?

    Date.strptime("#{value}-01", '%Y-%m-%d')
  rescue ArgumentError
    Time.zone.today.beginning_of_month
  end

  def normalize_work_hours(value)
    hours = Float(value.presence || DEFAULT_WORK_HOURS_PER_DAY)
    hours.positive? ? hours : DEFAULT_WORK_HOURS_PER_DAY
  rescue ArgumentError, TypeError
    DEFAULT_WORK_HOURS_PER_DAY
  end

  def empty_machine_data
    {
      days: Set.new,
      shot: [],
      spm: [],
      chokotei: [],
      jyotai: []
    }
  end

  def each_monthly_file
    pattern = File.join(IOT_DIR, "#{@month.strftime('%Y_%m')}_*.csv")
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

  def load_points(path)
    points = []
    CSV.foreach(path, headers: false).with_index do |row, index|
      cells = row.map { |cell| cell.to_s.strip }
      next if cells.empty? || cells.all?(&:blank?)

      if cells.length >= 2
        points << { time: parse_time(cells[0]), value: numeric_value(cells[1]), index: index }
      else
        points << { time: nil, value: numeric_value(cells[0]), index: index }
      end
    end
    points
  rescue CSV::MalformedCSVError
    []
  end

  def parse_time(value)
    Time.zone.parse(value)
  rescue ArgumentError, TypeError
    nil
  end

  def numeric_value(value)
    Float(value)
  rescue ArgumentError, TypeError
    nil
  end

  def build_row(machine, data)
    active_days = data[:days].size
    available_hours = active_days * @work_hours_per_day
    operating_hours = calculate_operating_hours(data[:jyotai])

    {
      machine: machine,
      active_days: active_days,
      available_hours: available_hours,
      operating_hours: operating_hours,
      operating_rate: rate(operating_hours, available_hours),
      shot_count: cumulative_delta(data[:shot]),
      average_spm: average(data[:spm].filter_map { |point| point[:value] }.select(&:positive?)),
      chokotei_count: cumulative_delta(data[:chokotei]),
      latest_at: latest_time(data)
    }
  end

  def calculate_operating_hours(points)
    values = points.select { |point| point[:value].to_f > RUNNING_THRESHOLD }
    return 0.0 if values.empty?

    interval_seconds = median_interval_seconds(points)
    return 0.0 if interval_seconds.zero?

    (values.size * interval_seconds / 3600.0).round(2)
  end

  def median_interval_seconds(points)
    timestamps = points.filter_map { |point| point[:time] }.sort
    intervals = timestamps.each_cons(2).filter_map do |previous_time, current_time|
      diff = current_time - previous_time
      diff.positive? && diff <= 1.hour ? diff : nil
    end
    return 30.0 if intervals.empty? && timestamps.present?
    return 0.0 if intervals.empty?

    sorted = intervals.sort
    sorted[sorted.length / 2]
  end

  def cumulative_delta(points)
    values = points.filter_map { |point| point[:value] }
    return 0 if values.empty?

    delta = values.max - values.min
    delta.negative? ? 0 : delta.round
  end

  def average(values)
    return 0.0 if values.empty?

    (values.sum / values.size).round(1)
  end

  def rate(numerator, denominator)
    return 0.0 if denominator.to_f <= 0.0

    ((numerator / denominator) * 100).round(1)
  end

  def latest_time(data)
    data.values_at(:shot, :spm, :chokotei, :jyotai).flatten.filter_map { |point| point[:time] }.max
  end

  def build_totals(rows)
    {
      machine_count: rows.size,
      operating_hours: rows.sum { |row| row[:operating_hours] }.round(2),
      available_hours: rows.sum { |row| row[:available_hours] }.round(2),
      shot_count: rows.sum { |row| row[:shot_count] },
      chokotei_count: rows.sum { |row| row[:chokotei_count] }
    }
  end
end
