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

  def content_eval(content)
    view_context.instance_eval(%("#{content}"), __FILE__, __LINE__).gsub(/\R/, "\n") # エクセルの改行は LF
  end

  def cell_render(cell)
    cell.change_contents(content_eval(cell.value))
    cell.change_text_wrap(true) if cell.value&.lines("\n")&.count&.> 1
  rescue StandardError
    cell.change_contents('')
    # cell.change_contents('error!')
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
