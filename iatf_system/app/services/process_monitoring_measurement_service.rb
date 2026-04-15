# frozen_string_literal: true

require 'json'

class ProcessMonitoringMeasurementService
  DATA_PATH = Rails.root.join('db', 'process_monitoring_measurement.json')
  MONTH_COLUMNS = (1..12).to_h { |month| [month, month + 9] }.freeze
  PROCESS_NAMES = [
    '営業プロセス',
    '改善プロセス',
    '内部監査プロセス',
    '計測器管理プロセス',
    '方針管理プロセス',
    '設備管理プロセス',
    '購買・生産管理プロセス',
    '製品検査引渡しプロセス',
    '製造プロセス',
    '製造工程設計プロセス'
  ].freeze

  def self.call
    new.call
  end

  def call
    return fallback_payload unless DATA_PATH.exist?

    payload = JSON.parse(DATA_PATH.read, symbolize_names: true)
    year_2024 = normalize_2024(payload[:year_2024] || {})
    year_2024[:metrics] = build_metric_cards(year_2024[:rows])
    year_payloads = { year_2024: year_2024 }
    available_years = [2024]

    payload.keys.grep(/\Ayear_(20\d{2})\z/).sort.each do |key|
      year = key.to_s.delete_prefix('year_').to_i
      next if year <= 2024

      available_years << year
      if payload[key].is_a?(Hash) && payload[key][:rows].present?
        year_payloads[key] = normalize_2024(payload[key])
        year_payloads[key][:metrics] = build_metric_cards(year_payloads[key][:rows])
      else
        year_payloads[key] = build_year_template(year_2024, Array(payload[key]), year)
      end
    end

    {
      generated_at: payload[:generated_at].to_s,
      source_dir: payload[:source_dir].to_s,
      available_years: available_years.uniq.sort,
      **year_payloads
    }
  rescue StandardError => e
    {
      generated_at: '',
      source_dir: '',
      available_years: [2024, 2025, 2026],
      year_2024: { rows: [], column_widths: [], source_file: '', sheet_name: '', metrics: [], error: e.message },
      year_2025: { rows: [], column_widths: [], source_file: '', sheet_name: '', source_files: [], metrics: [], error: e.message },
      year_2026: { rows: [], column_widths: [], source_file: '', sheet_name: '', source_files: [], metrics: [], error: e.message }
    }
  end

  private

  def fallback_payload
    {
      generated_at: '',
      source_dir: '',
      available_years: [2024, 2025, 2026],
      year_2024: { rows: [], column_widths: [], source_file: '', sheet_name: '', metrics: [] },
      year_2025: { rows: [], column_widths: [], source_file: '', sheet_name: '', source_files: [], metrics: [] },
      year_2026: { rows: [], column_widths: [], source_file: '', sheet_name: '', source_files: [], metrics: [] }
    }
  end

  def normalize_2024(payload)
    {
      source_file: payload[:source_file].to_s,
      sheet_name: payload[:sheet_name].to_s,
      column_widths: Array(payload[:column_widths]).map { |width| width.to_f.nonzero? || 13.0 },
      rows: Array(payload[:rows]).map do |row|
        {
          row: row[:row].to_i,
          cells: Array(row[:cells]).map do |cell|
            {
              col: cell[:col].to_i,
              value: cell[:value].to_s,
              rowspan: cell[:rowspan].to_i.nonzero? || 1,
              colspan: cell[:colspan].to_i.nonzero? || 1
            }
          end
        }
      end
    }
  end

  def build_year_template(year_2024, items, year)
    template = Marshal.load(Marshal.dump(year_2024))
    rows = template[:rows]
    blocks = build_metric_blocks(rows)

    clear_monthly_values!(rows)
    rename_process_labels!(rows)

    normalized_items = normalize_year_items(items)
    normalized_items.each do |item|
      month_col = MONTH_COLUMNS[item[:month].to_i]
      next unless month_col

      item[:entries].each do |entry|
        block = find_metric_block(blocks, entry)
        next unless block

        set_cell_value(rows, block[:metric_row], 5, entry[:target])
        set_cell_value(rows, block[:metric_row], month_col, entry[:target])

        month_value, cumulative_value = split_actual_values(entry[:actual])
        set_cell_value(rows, block[:actual_row], month_col, month_value)
        set_cell_value(rows, block[:cumulative_row], month_col, cumulative_value || month_value)
      end
    end

    template.merge(
      source_file: '',
      sheet_name: "プロセスの監視・測定記録 (#{year}年)",
      source_files: normalized_items.map do |item|
        {
          month: item[:month],
          source_file: item[:source_file],
          created_date: item[:created_date]
        }
      end,
      metrics: build_metric_cards(rows)
    )
  end

  def normalize_year_items(items)
    items.map do |item|
      {
        source_file: item[:source_file].to_s,
        month: item[:month].to_i,
        created_date: item[:created_date].to_s,
        entries: normalize_year_entries(Array(item[:entries]))
      }
    end.sort_by { |item| item[:month] }
  end

  # PDF テキスト抽出誤りで実績値・目標値が metric 先頭に混入する場合を除去する
  def strip_metric_contamination(text)
    value = text.to_s.strip
    return value if value.empty?

    # パターン1: 5文字以上先行してから累計/累積が出現 → 全体を先頭から累計直後まで除去
    # （累計から始まる正規メトリクス名を破壊しないよう5文字ガード）
    if value.match?(/\A[\s\S]{5,80}?累[計積]/m)
      cleaned = value.sub(/\A[\s\S]{0,80}?累[計積][\d０-９.%％件\s]{0,20}?(?=[\u4e00-\u9fff]{2})/m, '').strip
      value = cleaned if cleaned.length > 5
    end

    # 累計除去後に残る数字・件などのゴミを除去
    value = value.sub(/\A[\d０-９]+件?\s*/, '') if value.match?(/\A[\d０-９]/)
    value = value.sub(/\A件\s*/, '')

    # パターン2: 先頭に数字の目標値（「4件/年」「2件以下/年」等）が混入
    value = value.sub(/\A[\d０-９]+[.．\d]*[%％]?(?:以上|以下|件[\/／]?年|件以下[\/／]?年)\s*/, '')

    # パターン3: 当月から始まる残余（累計なし）
    value = value.sub(/\A当月\S{0,20}\s*/, '') if value.start_with?('当月')

    value.strip
  end

  def normalize_year_entries(entries)
    current_process = nil

    entries.filter_map do |entry|
      process = clean_inline_text(entry[:process].to_s)
      metric = strip_metric_contamination(clean_inline_text(entry[:metric].to_s))
      target = clean_inline_text(entry[:target].to_s)
      actual = clean_inline_text(entry[:actual].to_s)

      next if [metric, target, actual].all?(&:blank?)

      process_candidate = usable_process_name?(process) ? detect_process_name(process) : nil
      metric_candidate = detect_process_name(metric)
      detected_process = metric_candidate || process_candidate
      current_process = detected_process if detected_process.present?

      normalized_process =
        if usable_process_name?(process)
          process
        else
          current_process.presence || '共通'
        end

      normalized_process = current_process if normalized_process == '理プロセス' && current_process.present?
      metric = strip_leading_process(metric, detected_process || current_process)

      {
        process: normalized_process.to_s,
        metric: metric,
        target: target,
        actual: actual
      }
    end
  end

  def build_metric_blocks(rows)
    current_process = ''

    rows.filter_map do |row|
      cell_map = row[:cells].each_with_object({}) { |cell, memo| memo[cell[:col]] = cell[:value].to_s }
      current_process = clean_inline_text(cell_map[2]) if cell_map[2].present?
      next unless cell_map[4].present?

      {
        metric_row: row[:row],
        process: current_process,
        metric: clean_inline_text(cell_map[4]),
        metric_key: canonical_metric_name(cell_map[4]),
        actual_row: row[:row] + 1,
        cumulative_row: row[:row] + 2
      }
    end
  end

  def clear_monthly_values!(rows)
    rows.each do |row|
      next unless row[:row].to_i >= 9

      row[:cells].each do |cell|
        next unless MONTH_COLUMNS.value?(cell[:col].to_i)

        cell[:value] = ''
      end
    end
  end

  def rename_process_labels!(rows)
    rows.each do |row|
      row[:cells].each do |cell|
        next unless cell[:col].to_i == 2

        value = clean_inline_text(cell[:value])
        cell[:value] =
          case value
          when '購買プロセス'
            '購買・生産管理プロセス'
          when '製品検査・ 引渡しプロセス', '製品検査・　　引渡しプロセス'
            '製品検査引渡しプロセス'
          else
            cell[:value]
          end
      end
    end
  end

  def find_metric_block(blocks, entry)
    metric_key = canonical_metric_name(entry[:metric])
    process_key = canonical_process_name(entry[:process])

    exact = blocks.find { |block| block[:metric_key] == metric_key && canonical_process_name(block[:process]) == process_key }
    return exact if exact

    metric_only = blocks.find { |block| block[:metric_key] == metric_key }
    return metric_only if metric_only

    alias_key = metric_alias(metric_key)
    aliased = blocks.find { |block| block[:metric_key] == alias_key }
    return aliased if aliased

    # Prefix match: handles Docling-truncated metric names (e.g. last few chars cut off)
    return nil if metric_key.length < 10

    prefix_match = blocks.find { |block| block[:metric_key].start_with?(metric_key) }
    return prefix_match if prefix_match

    # Strip leading process-name contamination (e.g. "計測器管理 校正計画達成度" → "校正計画達成度")
    # Try progressively stripping leading chars until we find a block match or key is too short
    stripped = metric_key
    while stripped.length >= 10
      idx = stripped.index(/[\u4e00-\u9fff]/, 1)
      break unless idx
      stripped = stripped[idx..]
      found = blocks.find { |block| block[:metric_key] == stripped }
      found ||= blocks.find { |block| block[:metric_key] == metric_alias(stripped) }
      found ||= (stripped.length >= 10 ? blocks.find { |block| block[:metric_key].start_with?(stripped) } : nil)
      return found if found
    end

    nil
  end

  def canonical_process_name(text)
    clean_inline_text(text).gsub(/[()（）\s・]/, '')
  end

  def canonical_metric_name(text)
    value = clean_inline_text(text)
    # 会社名プレフィックス除去
    value = value.sub(/\Aミツイ精密株式会社/, '')
    value = value.gsub(/[()（）]/, '')
    value = value.gsub(%r{[/／]}, '')
    value = value.gsub(/[：:・]/, '')
    value = value.gsub(/\s+/, '')
    value = value.delete('　')
    value
  end

  def metric_alias(metric_key)
    aliases = {
      canonical_metric_name('品質又は納期問題に関する顧客からの特別通知回数目標達成度') => canonical_metric_name('品質又は納期問題に関する顧客からの特別通知回数目標達成度'),
      canonical_metric_name('見積もり案件に対する受注目標達成率') => canonical_metric_name('試作見積件数に対する受注目標達成率'),
      canonical_metric_name('効率指標：1人1時間あたり生産達成率') => canonical_metric_name('生産数／１人１Ｈ 目標達成度'),
      canonical_metric_name('顧客納期遵守率目標達成度') => canonical_metric_name('納期順守率目標達成度 （順守件数/納入件数)'),
      canonical_metric_name('受入検査不適合件数目標達成度') => canonical_metric_name('受入検査不適合率目標達成度'),
      canonical_metric_name('製品検査引渡しプロセスプレス検査工程内不良率目標達成度') => canonical_metric_name('検査工程内不適合率目標達成度不適合数生産数'),
      canonical_metric_name('プレス検査工程内不良率目標達成度') => canonical_metric_name('検査工程内不適合率目標達成度不適合数生産数'),
      canonical_metric_name('成形工程検査内不適合率') => canonical_metric_name('成形工程検査不適合率不適合数生産数'),
      canonical_metric_name('出荷検査不適合率目標達成度') => canonical_metric_name('出荷検査不適合件数目標達成度'),
      canonical_metric_name('顧客納期遵守率目標達成度遵守件数納入件数') => canonical_metric_name('納期順守率目標達成度順守件数納入件数'),
      canonical_metric_name('供給者納期遵守率目標達成度遵守件数納入件数') => canonical_metric_name('納期遵守率目標達成度遵守件数納入件数'),
      canonical_metric_name('納期遵守率目標達成度') => canonical_metric_name('納期遵守率目標達成度遵守件数納入件数'),
      canonical_metric_name('計測器管理プロセス校正計画達成度') => canonical_metric_name('校正計画達成度実施数計画数'),
      canonical_metric_name('計測器管理校正計画達成度') => canonical_metric_name('校正計画達成度実施数計画数'),
      canonical_metric_name('校正計画達成度') => canonical_metric_name('校正計画達成度実施数計画数'),
      canonical_metric_name('方針管理プロセス品質方針達成度') => canonical_metric_name('品質目標達成率達成件数目標件数'),
      canonical_metric_name('品質方針達成度') => canonical_metric_name('品質目標達成率達成件数目標件数'),
      canonical_metric_name('内部監査プロセス改善の機会件数目標達成度') => canonical_metric_name('改善の機会件数目標達成度'),
      canonical_metric_name('是正処置完了日程目標達成度') => canonical_metric_name('是正処置完了日程目標達成度順守数処置数'),
      canonical_metric_name('プロセス是正処置完了日程目標達成度') => canonical_metric_name('是正処置完了日程目標達成度順守数処置数'),
      canonical_metric_name('是正処置再発率目標達成度') => canonical_metric_name('是正処置再発件数目標達成度'),
      canonical_metric_name('納入不良率目標達成度') => canonical_metric_name('納入不良率目標達成度不合格数納入数'),
      canonical_metric_name('プレス工程内不良合率') => canonical_metric_name('プレス工程内不適合率目標達成度不適合数生産数'),
      canonical_metric_name('特別輸送費の発生金額目標達成度') => canonical_metric_name('特別輸送費の発生金額目標達成度特別輸送発生件数通常輸送件数'),
      canonical_metric_name('工程能力指数目標1.67以上達成度') => canonical_metric_name('工程能力指数目標1.67以上達成度達成件数対象件数量産について評価'),
      canonical_metric_name('プレス効率指標1人1時間あたり生産達成率') => canonical_metric_name('生産数１人１Ｈ目標達成度'),
      canonical_metric_name('成形効率指標生産達成率') => canonical_metric_name('生産達成率稼働率目標達成度'),
      canonical_metric_name('設備故障回数') => canonical_metric_name('故障回数'),
      canonical_metric_name('成形工程内不適合率') => canonical_metric_name('工程内不適合率目標達成度不適合数生産数'),
      canonical_metric_name('成形有効性指標工程能力指数1.67以上') => canonical_metric_name('工程能力指数目標1.67以上達成度達成件数対象件数量産について評価'),
      canonical_metric_name('プレス有効性指数工程能力指数1.67以上') => canonical_metric_name('工程能力指数目標1.67以上達成度達成件数対象件数量産について評価'),
      canonical_metric_name('プレス有効性指標工程能力指数1.67以上') => canonical_metric_name('工程能力指数目標1.67以上達成度達成件数対象件数量産について評価')
    }

    aliases[metric_key] || metric_key
  end

  def split_actual_values(text)
    value = clean_inline_text(text)
    monthly = nil
    cumulative = nil

    if value.include?('??') && value.include?('??')
      monthly = value.split('??', 2).last.to_s.split('??', 2).first.to_s.strip
      cumulative = value.split('??', 2).last.to_s.strip
    elsif value.include?('???') && value.include?('??')
      monthly = value.split('???', 2).last.to_s.split('??', 2).first.to_s.strip
      cumulative = value.split('??', 2).last.to_s.strip
    end

    monthly = value if monthly.blank? && cumulative.blank?
    [monthly, cumulative]
  end

  def set_cell_value(rows, row_no, col_no, value)
    row = rows.find { |item| item[:row].to_i == row_no.to_i }
    return unless row

    cell = row[:cells].find { |item| item[:col].to_i == col_no.to_i }
    return unless cell

    cell[:value] = value.to_s
  end

  def clean_inline_text(text)
    text.to_s.gsub(/\r\n?/, "\n").gsub(/[[:space:]]+/, ' ').strip
  end

  def detect_process_name(text)
    PROCESS_NAMES.find { |name| text.to_s.include?(name) }
  end

  def usable_process_name?(text)
    value = text.to_s.strip
    return false if value.blank?
    return false if value.start_with?('・')
    return false if value.length > 24
    return false if value.include?('当月') || value.include?('累計')

    true
  end

  def strip_leading_process(metric, process_name)
    return metric if process_name.blank?

    metric.to_s.sub(/\A.*?#{Regexp.escape(process_name)}/, '').strip
  end

  def clean_section_text(text, stop_markers:)
    value = text.to_s.gsub(/\r\n?/, "\n")
    stop_index = stop_markers.filter_map { |marker| value.index(marker) }.min
    value = value[0...stop_index] if stop_index.present?

    lines = value.lines.map(&:strip)
    lines.shift while lines.any? && !meaningful_section_line?(lines.first)
    lines.reject!(&:blank?)
    lines.join("\n").strip
  end

  def meaningful_section_line?(line)
    value = line.to_s.strip
    return false if value.blank?
    return true if value.start_with?("\u30fb")

    value.length > 3
  end

  def build_metric_cards(rows)
    current_process = ''

    rows.filter_map do |row|
      cell_map = row[:cells].each_with_object({}) { |cell, memo| memo[cell[:col]] = cell[:value].to_s }
      current_process = clean_inline_text(cell_map[2]) if cell_map[2].present?
      next unless cell_map[4].present?

      actual_row = rows.find { |item| item[:row].to_i == row[:row].to_i + 1 }
      cumulative_row = rows.find { |item| item[:row].to_i == row[:row].to_i + 2 }
      actual_map = actual_row ? actual_row[:cells].each_with_object({}) { |cell, memo| memo[cell[:col]] = cell[:value].to_s } : {}
      cumulative_map = cumulative_row ? cumulative_row[:cells].each_with_object({}) { |cell, memo| memo[cell[:col]] = cell[:value].to_s } : {}

      {
        process: current_process,
        metric: clean_inline_text(cell_map[4]),
        target: clean_inline_text(cell_map[5]),
        months: MONTH_COLUMNS.map do |month, col|
          {
            month: month,
            target: clean_inline_text(cell_map[col]),
            actual: clean_inline_text(actual_map[col]),
            cumulative: clean_inline_text(cumulative_map[col])
          }
        end
      }
    end
  end
end
