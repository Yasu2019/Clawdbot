# frozen_string_literal: true

require "rubyXL"
require "rubyXL/convenience_methods"
require "rubyXL/convenience_methods/cell"
require "rubyXL/convenience_methods/worksheet"

# ProductsController#generate_xlsx から呼び出される一覧 Excel 出力サービス
class GenerateXlsxService
  COLUMN_WIDTH = 18
  SHEET_NAME = "登録データ一覧"
  TITLE = "登録データ一覧"
  HEADERS = %w[
    ID
    品番
    材料コード
    文書名
    詳細
    カテゴリー
    フェーズ
    段階
    登録日
    期限日
    完了日
    進捗度
    ステータス
  ].freeze

  def self.call(products:, dropdownlist:)
    new(products:, dropdownlist:).call
  end

  def initialize(products:, dropdownlist:)
    @products = products
    @dropdownlist = dropdownlist
  end

  def call
    workbook = RubyXL::Workbook.new
    worksheet = workbook[0]
    worksheet.sheet_name = SHEET_NAME

    title_style = { fill_color: "C0C0C0", font_name: "Arial", font_size: 12, bold: true }
    header_style = { fill_color: "E0E0E0", font_name: "Arial", font_size: 11, bold: true }

    title_cell = worksheet.add_cell(0, 0, TITLE)
    title_cell.change_fill(title_style[:fill_color])
    title_cell.change_font_name(title_style[:font_name])
    title_cell.change_font_size(title_style[:font_size])
    title_cell.change_font_bold(title_style[:bold])
    apply_cell_format(title_cell)

    HEADERS.each_with_index do |header, index|
      header_cell = worksheet.add_cell(1, index, header)
      header_cell.change_fill(header_style[:fill_color])
      header_cell.change_font_name(header_style[:font_name])
      header_cell.change_font_size(header_style[:font_size])
      header_cell.change_font_bold(header_style[:bold])
      apply_cell_format(header_cell)
    end

    @products.each_with_index do |product, row|
      row_data_for(product).each_with_index do |value, col|
        cell = worksheet.add_cell(row + 2, col, value)
        apply_cell_format(cell)
      end
    end

    HEADERS.each_index do |col|
      worksheet.change_column_width(col, COLUMN_WIDTH)
    end

    workbook.stream.string
  end

  private

  def row_data_for(product)
    [
      product.id,
      product.partnumber,
      product.materialcode,
      product.documentname,
      product.description,
      @dropdownlist[product.category.to_i],
      @dropdownlist[product.phase.to_i],
      @dropdownlist[product.stage.to_i],
      format_date(product.start_time),
      format_date(product.deadline_at),
      format_date(product.end_at),
      product.goal_attainment_level,
      product.status
    ]
  end

  def format_date(value)
    value&.strftime("%y/%m/%d")
  end

  def apply_cell_format(cell)
    cell.change_text_wrap(true)
    cell.change_vertical_alignment("top")
    %w[top bottom left right].each do |direction|
      cell.change_border(direction, "thin")
    end
  end
end
