# frozen_string_literal: true

# APQP フェーズ別データを Excel に出力するサービス。
# ProductsController#export_phases_to_excel から呼び出される。
class ExportPhasesToExcelService
  SHEETS_DATA = {
    'フェーズ1' => ['顧客インプット', '顧客の声', '設計目標', '製品保証計画書', '製品・製造工程の前提条件',
                    '製品・製造工程のベンチマークデータ', '製品の信頼性調査', '経営者の支援',
                    '特殊製品特性・特殊プロセス特性の暫定リスト', '暫定材料明細表', '暫定プロセスマップフロー図',
                    '信頼性目標・品質目標', '事業計画・マーケティング戦略'],
    'フェーズ2' => ['試作コントロールプラン', '設計検証', '設計故障モード影響解析（DFMEA）',
                    '製造性・組立性を考慮した設計', '特殊製品特性・特殊プロセス特性', '材料仕様書', '技術仕様書',
                    '実現可能性検討報告書および経営者の支援', '図面（数学的データを含む）', '図面・仕様書の変更',
                    'デザインレビュー', 'ゲージ・試験装置の要求事項'],
    'フェーズ3' => ['製品・プロセスの品質システムのレビュー', '経営者の支援(Phase3)', '特性マトリクス',
                    '測定システム解析計画書', '梱包規格・仕様書', '工程能力予備調査計画書',
                    '先行生産（Pre-launch,量産試作）コントロールプラン', 'プロセス故障モード影響解析（PFMEA）',
                    'プロセス指示書', 'プロセスフロー図(Phase3)', 'フロアプランレイアウト'],
    'フェーズ4' => ['量産コントロールプラン', '量産の妥当性確認試験', '生産部品承認(PPAP)', '測定システム解析',
                    '梱包評価', '工程能力予備調査', '実質的生産', '品質計画承認署名'],
    'フェーズ5' => ['顧客満足の向上', '引渡しおよびサービスの改善', '学んだ教訓・ベストプラクティスの効果的な利用',
                    '変動の減少'],
    'PPAP'      => ['顧客技術承認', '顧客固有要求事項適合記録', '部品提出保証書（PSW)', '設計FMEA', '製品設計文書',
                    '製品サンプル', '測定システム解析（MSA)', '検査補助具', '材料・性能試験結果', '有資格試験所文書',
                    '技術変更文書（顧客承認）', '寸法測定結果', '外観承認報告書（AAR)', '初期工程調査結果',
                    'マスターサンプル', 'プロセスフロー図', 'プロセスFMEA', 'バルク材料チェックリスト',
                    'コントロールプラン'],
    '8.3製品の設計・開発' => ['顧客要求事項検討会議事録_営業', '金型製造指示書_営業', '金型製作依頼票_金型設計',
                              '進捗管理票_生産技術', '試作製造指示書_営業', '設計計画書_金型設計',
                              '設計検証チェックリスト_金型設計', '設計変更会議議事録_金型設計',
                              '製造実現可能性検討書', '妥当性確認記録_金型設計', '初期流動検査記録',
                              'レイアウト/歩留まり_営業', 'DR構想検討会議議事録_生産技術', 'DR会議議事録_金型設計']
  }.freeze

  def self.call(products:, dropdownlist:)
    new(products:, dropdownlist:).call
  end

  def initialize(products:, dropdownlist:)
    @products    = products
    @dropdownlist = dropdownlist
  end

  def call
    workbook = RubyXL::Workbook.new

    SHEETS_DATA.each do |sheet_name, stage_headers|
      worksheet = workbook.add_worksheet(sheet_name)

      # ヘッダー行の追加
      all_headers = ['図番'] + stage_headers
      all_headers.each_with_index do |header, index|
        worksheet.add_cell(0, index, header)
      end

      # データ行の追加
      grouped_products = @products.group_by(&:partnumber)
      row = 1
      grouped_products.each do |partnumber, products|
        worksheet.add_cell(row, 0, partnumber)

        products.each do |product|
          next unless @dropdownlist[product.phase.to_i] == sheet_name

          Rails.logger.debug "Processing product: #{product.partnumber}, Phase: #{product.phase}"

          stage_headers.each_with_index do |header, col|
            if @dropdownlist[product.stage.to_i] == header
              status = case product.status
                       when '完了' then '完'
                       when '仕掛中' then '仕'
                       else '―'
                       end
              worksheet.add_cell(row, col + 1, status)
              Rails.logger.debug "Header: #{header}, Status: #{status}"
            end
          end
        end
        row += 1
      end
    end

    workbook.stream.string
  end
end
