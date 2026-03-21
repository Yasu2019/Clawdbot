# frozen_string_literal: true

# 登録データ一覧 Excel ファイルを生成するサービス。
# ProductsController#generate_xlsx から呼び出される。
class GenerateXlsxService
  def self.call(products:, dropdownlist:)
    new(products:, dropdownlist:).call
  end

  def initialize(products:, dropdownlist:)
    @products    = products
    @dropdownlist = dropdownlist
  end

  def call
    workbook  = RubyXL::Workbook.new
    worksheet = workbook.add_worksheet('登録データ一覧')

    # スタイルの定義
    title_style  = { 'fill_color' => 'C0C0C0', 'font_name' => 'Arial', 'font_size' => 12, 'b' => true }
    header_style = { 'fill_color' => 'E0E0E0', 'font_name' => 'Arial', 'font_size' => 11, 'b' => true }

    # タイトル行の追加
    title_cell = worksheet.add_cell(0, 0, '登録データ一覧')
    title_cell.change_fill(title_style['fill_color'])
    title_cell.change_font_name(title_style['font_name'])
    title_cell.change_font_size(title_style['font_size'])
    title_cell.change_font_bold(title_style['b'])

    # ヘッダー行の追加
    headers = %w[ID 図番 材料コード 文書名 詳細 カテゴリー フェーズ 項目 登録日 完了予定日 完了日 達成度 ステイタス]
    headers.each_with_index do |header, index|
      header_cell = worksheet.add_cell(1, index, header)
      header_cell.change_fill(header_style['fill_color'])
      header_cell.change_font_name(header_style['font_name'])
      header_cell.change_font_size(header_style['font_size'])
      header_cell.change_font_bold(header_style['b'])
    end

    # データ行の追加
    @products.each_with_index do |pro, row|
      data = [
        pro.id,
        pro.partnumber,
        pro.materialcode,
        pro.documentname,
        pro.description,
        @dropdownlist[pro.category.to_i],
        @dropdownlist[pro.phase.to_i],
        @dropdownlist[pro.stage.to_i],
        pro.start_time&.strftime('%y/%m/%d'),
        pro.deadline_at&.strftime('%y/%m/%d'),
        pro.end_at&.strftime('%y/%m/%d'),
        pro.goal_attainment_level,
        pro.status
      ]
      data.each_with_index do |value, col|
        worksheet.add_cell(row + 2, col, value)
      end
    end

    workbook.stream.string
  end
end
