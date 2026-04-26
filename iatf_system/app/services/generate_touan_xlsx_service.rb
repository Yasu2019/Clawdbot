# frozen_string_literal: true

# 登録答案一覧 Excel ファイルを生成するサービス。
# TouansController#xlsx から呼び出される。
class GenerateTouanXlsxService
  def self.call(touans:)
    new(touans:).call
  end

  def initialize(touans:)
    @touans = touans
  end

  def call
    package = Axlsx::Package.new(encoding: 'UTF-8')
    package.workbook.add_worksheet(name: '登録答案一覧') do |sheet|
      styles = package.workbook.styles
      title  = styles.add_style(bg_color: 'c0c0c0', b: true)
      header = styles.add_style(bg_color: 'e0e0e0', b: true)

      sheet.add_row ['登録答案一覧'], style: title
      sheet.add_row %w[id 箇条 問題番号 参考URL 問題 選択肢a 選択肢b 選択肢c 正解 解説 ユーザーの回答 ユーザーID 回答数 正解数 正解率 作成日 更新日], style: header
      sheet.add_row %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu kaito user_id total_answers correct_answers seikairitsu created_at updated_at],
                    style: header

      @touans.each do |t|
        sheet.add_row [t.id, t.kajyou, t.mondai_no, t.rev, t.mondai, t.mondai_a, t.mondai_b, t.mondai_c, t.seikai, t.kaisetsu,
                       t.kaito, t.user_id, t.total_answers, t.correct_answers, t.seikairitsu, t.created_at, t.updated_at]
      end
    end

    package.to_stream.read
  end
end
