# frozen_string_literal: true

module ExcelTemplateHelper
  def excel_render(template_file)
    RubyXL::Parser.parse(template_file).tap do |workbook|
      workbook.worksheets.each do |worksheet|
        @worksheet = worksheet
        # @worksheet.each do |row|
        @worksheet.each_with_index do |row, row_num| # row_numを追加
          row&.cells&.each do |cell|
            next if cell.nil?

            cell_render(cell)
          end
          row_height_auto(row_num)
        end
      end
    end
  end

  private

  def cell_render(cell)
    # 結合セルのマスターセル（左上）以外への操作をスキップし、ファイルの破損を防ぐ
    return if merged_and_not_master?(cell)

    cell.change_contents(content_eval(cell.value))
    cell.change_text_wrap(true) if cell.value&.lines("\n")&.count&.> 1
  rescue StandardError
    cell.change_contents('')
  end

  def merged_and_not_master?(cell)
    @worksheet.merged_cells&.any? do |merged_range|
      # 結合範囲を取得 (A1:B2 形式など)
      ref = merged_range.is_a?(String) ? merged_range : merged_range.ref.to_s
      
      # 範囲をパースして、現在のセルが含まれているか確認
      # RubyXL::Reference を使用して範囲判定
      range = RubyXL::Reference.new(ref)
      
      if range.row_range.include?(cell.row) && range.col_range.include?(cell.column)
        # 範囲内だが、左上（開始点）でない場合は true (スキップ対象)
        return cell.row != range.row_range.first || cell.column != range.col_range.first
      end
      false
    end
  end

  # @のままだと出力したときに、＠のセルにメールのハイパーリンクがついてしまう。
  def content_eval(content)
    adjusted_content = content.gsub('?', '@') # '?' を '@' に置換
    view_context.instance_eval(%("#{adjusted_content}"), __FILE__, __LINE__).gsub(/\R/, "\n") # エクセルの改行は LF
  end

  def row_height_auto(row_num)
    max_lines = @worksheet[row_num]&.cells&.map { |cell| cell&.value&.lines("\n")&.count || 0 }&.max
    origin_height = [@worksheet.get_row_height(row_num), 30].max # 最小値が RubyXL::Row::DEFAULT_HEIGHT (= 13) では合わなかったので手動調整
    @worksheet.change_row_height(row_num, origin_height * max_lines) if max_lines&.positive?
  end
end
