# frozen_string_literal: true

# APQP フェーズ別データを Excel に出力するサービス
# ProductsController#export_phases_to_excel から呼び出される
class ExportPhasesToExcelService
  SHEETS_DATA = {
    "フェーズ1" => ["製品インプット", "製品の図", "設計要求", "製品仕様計画書", "製品の製造工程の仮要求事項",
                  "製品の製造工程のベンチマークデータ", "製品の特殊特性検討", "顧客図面・要求事項",
                  "特殊特性・特殊工程特性の識別リスト", "設計構想会議・検討書", "設計案のプロセスマップフロー図",
                  "特殊特性管理の製品特性", "社内設計図・マーケティング調査"],
    "フェーズ2" => ["試作品コントロールプラン", "設計FMEA", "設計FMEA見直し", "製造実現性・工程能力検討書",
                  "特殊特性・特殊工程特性", "図面レビュー", "設計レビュー", "製造工程特殊特性管理検討書",
                  "工程表・工程設計レビュー", "工程表・図面見直し", "デザインレビュー", "ゲージ・試験装置の妥当性確認"],
    "フェーズ3" => ["製品・プロセスの製造システムのレビュー", "顧客図面・要求事項(Phase3)", "特殊特性マトリクス",
                  "製造システム検討会議議事録", "工程能力・試験レビュー", "製造工程の妥当性確認計画書",
                  "試作工程(re-launch,量産立上げ)コントロールプラン", "プロセスFMEA見直し", "プロセス仕様書",
                  "プロセスフロー図(Phase3)", "フロアプランレイアウト"],
    "フェーズ4" => ["量産コントロールプラン", "量産の測定システム分析報告書", "生産部品承認(PPAP)", "製造システム検討",
                  "工程能力評価", "製造工程の妥当性確認", "初期流動管理", "工程能力確認書類"],
    "フェーズ5" => ["量産開始後の改善", "問題発生時のサービスの改善", "学んだ教訓のベストプラクティスへの反映",
                  "継続的な改善"],
    "PPAP" => ["量産承認資料", "量産開始時の工程能力と寸法評価", "部品提出保証書(PSW)", "設計FMEA", "製品仕様書",
              "製品サンプル", "製造システム評価(MSA)", "試験成績表", "図面・機能性評価結果", "初期工程能力評価",
              "製造工程管理の評価結果・工程監査報告書", "外観承認報告書", "検査成績書", "承認済サンプル",
              "マスターサンプル", "プロセスフロー図", "プロセスFMEA", "バルク材料チェックリスト", "コントロールプラン"],
    "8.3設計開発" => ["顧客要求事項検討会議事録_営業", "金型製造指示書_営業", "金型製作依頼票_金型設計",
                   "進捗管理票_生産技術", "試作製造指示書_営業", "設計計画書_金型設計", "設計検証チェックリスト_金型設計",
                   "設計変更会議議事録_金型設計", "妥当性確認記録_金型設計", "初期流動検査記録", "レイアウト/歩留まり_営業",
                   "DR構想検討会議議事録_生産技術", "DR会議議事録_金型設計"]
  }.freeze

  def self.call(products:, dropdownlist:)
    new(products:, dropdownlist:).call
  end

  def initialize(products:, dropdownlist:)
    @products = products
    @dropdownlist = dropdownlist
  end

  def call
    workbook = RubyXL::Workbook.new

    SHEETS_DATA.each do |sheet_name, stage_headers|
      worksheet = workbook.add_worksheet(sheet_name)
      all_headers = ["品番", "型No候補"] + stage_headers

      all_headers.each_with_index do |header, index|
        worksheet.add_cell(0, index, header)
      end

      row = 1
      @products.group_by(&:partnumber).each do |partnumber, products|
        worksheet.add_cell(row, 0, partnumber)
        worksheet.add_cell(row, 1, type_candidates_for(products))

        products.each do |product|
          next unless @dropdownlist[product.phase.to_i] == sheet_name

          stage_headers.each_with_index do |header, col|
            next unless @dropdownlist[product.stage.to_i] == header

            status = case product.status.to_s
                     when "完了" then "完"
                     when /仕掛/ then "仕"
                     else "－"
                     end
            worksheet.add_cell(row, col + 2, status)
          end
        end

        row += 1
      end
    end

    workbook.stream.string
  end

  private

  def type_candidates_for(products)
    ApplicationController.helpers.product_type_candidates(products).join(" / ")
  end
end
