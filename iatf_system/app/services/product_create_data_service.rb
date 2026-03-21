# frozen_string_literal: true

# Excelテンプレートに必要なデータを製品ドキュメントから収集するサービス。
# ProductsController#process_design_plan_report から呼び出され、
# 収集した値をコントローラのインスタンス変数に割り当てるためのハッシュを返す。
class ProductCreateDataService
  def self.call(products:, all_products:, dropdownlist:)
    new(products:, all_products:, dropdownlist:).call
  end

  def initialize(products:, all_products:, dropdownlist:)
    @products     = products
    @all_products = all_products
    @dropdownlist = dropdownlist
  end

  def call
    @insert_rows_to_excel_template = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @insert_rows_to_excel_template_msa = true # MSA GRRを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @insert_rows_to_excel_template_dr_setsubi = true # 初回のファイルのみ挿入サブルーチンに飛ぶ
    @insert_rows_to_excel_template_progress_management = true # 初回のファイルのみ挿入サブルーチンに飛ぶ

    @datetime = Time.zone.now
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
    initialize_checkboxes

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= #{@partnumber}" # 追加
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= #{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= #{pro.stage}"

      collect_process_flow(pro, stage)

      collect_floor_plan_layout(pro, stage)

      collect_control_plan(pro, stage)

      collect_characteristics_matrix(pro, stage)

      collect_validation_record(pro, stage)

      collect_customer_requirements(pro, stage)

      collect_packaging_specs(pro, stage)

      collect_parts_inspection(pro, stage)

      collect_tech_specs(pro, stage)

      collect_drawings(pro, stage)

      collect_press_instructions(pro, stage)

      collect_process_inspection_record(pro, stage)

      collect_visual_inspection_guideline(pro, stage)

      collect_inspection_procedures(pro, stage)

      collect_manufacturing_feasibility(pro, stage)

      collect_process_fmea(pro, stage)

      collect_dr_meeting_minutes(pro, stage)

      collect_msa_grr(pro, stage)

      collect_msa_crosstab(pro, stage)

      collect_dimensional_measurement(pro, stage)

      collect_initial_process_survey(pro, stage)

      collect_prototype_instructions(pro, stage)

      collect_mold_instructions(pro, stage)

      collect_design_plan(pro, stage)

      collect_dr_concept_minutes(pro, stage)

      collect_progress_management(pro, stage)

      collect_initial_flow_record(pro, stage)

      collect_material_specs(pro, stage)

      collect_process_instructions(pro, stage)
    end

    collect_kanagata_record
    collect_jig_ledger

    result_variables
  end

  private

  def initialize_checkboxes
    @cp_check = '☐'
    @datou_check = '☐'
    @scr_check = '☐'
    @pfmea_check = '☐'
    @dr_check = '☐'
    @msa_check = '☐'
    @msa_crosstab_check = '☐'
    @msa_grr_check = '☐'
    @cpk_check = '☐'
    @shisaku_check = '☐'
    @kanagata_check = '☐'
    @dr_setsubi_check = '☐'
    @grr_check = '☐'
    @feasibility_check = '☐'
    @kataken_check = '☐'
    @visual_inspection_tejyunsho_check = '☐'
    @visual_inspection_youryousho_check = '☐'
    @stamping_instruction_check = '☐'
    @process_inspection_record_check = '☐'
    @drawing_check = '☐'
    @specifications_check = '☐'
    @parts_inspection_report_check = '☐'
    @material_specification_check = '☐'
    @shoki_check = '☐'
    @controlplan_check = '☐'
    @processflow_inspection_check = '☐'
    @processflow_mold_check = '☐'
  end

  # 入力パラメータを除くインスタンス変数をハッシュで返す
  def result_variables
    skip = %i[@products @all_products @dropdownlist]
    instance_variables.each_with_object({}) do |ivar, hash|
      next if skip.include?(ivar)
      hash[ivar.to_s.delete('@')] = instance_variable_get(ivar)
    end
  end

  def collect_process_flow(pro, stage)
    if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'

      @processflow_check = if pro.documents.attached?
        '☑'

        begin
          # プレスファイルの確認
          press_file_found = false
          mold_file_found = false

          # 最初にプレスファイルを探す
          pro.documents.each do |doc|
            filename = doc.filename.to_s
            if filename.include?('プロセスフロー') && filename.include?('プレス')
              press_file_found = true
              begin
                temp_file = Tempfile.new(['temp', File.extname(filename)])
                temp_file.binmode
                temp_file.write(doc.download)
                temp_file.rewind

                workbook = case File.extname(filename).downcase
                          when '.xlsx' then Roo::Excelx.new(temp_file.path)
                          when '.xls'  then Roo::Excel.new(temp_file.path)
                          else
                            next
                          end

                Rails.logger.info "=== ワークシート情報 ==="
                Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"

                # 適切なシートを探す
                target_sheet = nil
                workbook.sheets.each do |sheet_name|
                  workbook.default_sheet = sheet_name
                  Rails.logger.info "シート '#{sheet_name}' をチェック中..."

                  # セル(2,21)とセル(2,22)の値を確認
                  cell_2_21 = workbook.cell(2, 21)
                  cell_2_22 = workbook.cell(2, 22)

                  Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                  Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"

                  if cell_2_21.present? || cell_2_22.present?
                    target_sheet = sheet_name
                    Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                    break
                  end
                end

                unless target_sheet
                  Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                  next
                end

                workbook.default_sheet = target_sheet
                Rails.logger.info "選択したシート: #{target_sheet}"
                Rails.logger.info "最終行: #{workbook.last_row}"
                Rails.logger.info "最終列: #{workbook.last_column}"

                # セルの値を文字列として取得し、デバッグ情報を出力
                @processflow_stamping_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_stamping_dept = workbook.cell(4, 13).to_s.strip
                @processflow_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_stamping_check = '☑'

                Rails.logger.info "=== セルの値確認 ==="
                Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_stamping_person_in_charge.inspect}"
                Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_stamping_dept.inspect}"

                Rails.logger.info "プレス承認者: \#{?processflow_stamping_person_in_charge}"
                Rails.logger.info "プレス部署: \#{?processflow_stamping_dept}"
              rescue StandardError => e
                Rails.logger.error "プレスファイル処理エラー: #{e.message}"
              ensure
                workbook&.close if defined?(workbook) && workbook
                temp_file.close
                temp_file.unlink
              end
              break
            end
          end

          # プレスファイルがない場合は成形ファイルを探す
          unless press_file_found
            pro.documents.each do |doc|
              filename = doc.filename.to_s
              if filename.include?('プロセスフロー') && filename.include?('成形')
                mold_file_found = true
                begin
                  temp_file = Tempfile.new(['temp', File.extname(filename)])
                  temp_file.binmode
                  temp_file.write(doc.download)
                  temp_file.rewind

                  workbook = case File.extname(filename).downcase
                            when '.xlsx' then Roo::Excelx.new(temp_file.path)
                            when '.xls'  then Roo::Excel.new(temp_file.path)
                            else
                              next
                            end

                  Rails.logger.info "=== ワークシート情報 ==="
                  Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"

                  # 適切なシートを探す
                  target_sheet = nil
                  workbook.sheets.each do |sheet_name|
                    workbook.default_sheet = sheet_name
                    Rails.logger.info "シート '#{sheet_name}' をチェック中..."

                    # セル(2,21)とセル(2,22)の値を確認
                    cell_2_21 = workbook.cell(2, 21)
                    cell_2_22 = workbook.cell(2, 22)

                    Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                    Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"

                    if cell_2_21.present? || cell_2_22.present?
                      target_sheet = sheet_name
                      Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                      break
                    end
                  end

                  unless target_sheet
                    Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                    next
                  end

                  workbook.default_sheet = target_sheet
                  Rails.logger.info "選択したシート: #{target_sheet}"
                  Rails.logger.info "最終行: #{workbook.last_row}"
                  Rails.logger.info "最終列: #{workbook.last_column}"

                  # セルの値を文字列として取得し、デバッグ情報を出力
                  @processflow_mold_person_in_charge = workbook.cell(2, 21).to_s.strip
                  @processflow_mold_dept = workbook.cell(4, 13).to_s.strip
                  @processflow_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
                  @processflow_mold_kanryou = pro.end_at.strftime('%y/%m/%d')
                  @processflow_mold_check = '☑'

                  Rails.logger.info "=== セルの値確認 ==="
                  Rails.logger.info "セル(2,21)の生の値: #{workbook.cell(2, 21).inspect}"
                  Rails.logger.info "セル(2,21)の変換後の値: \#{?processflow_mold_person_in_charge.inspect}"
                  Rails.logger.info "セル(4,13)の生の値: #{workbook.cell(4, 13).inspect}"
                  Rails.logger.info "セル(4,13)の変換後の値: \#{?processflow_mold_dept.inspect}"

                  Rails.logger.info "成形承認者: \#{?processflow_mold_person_in_charge}"
                rescue StandardError => e
                  Rails.logger.error "成形ファイル処理エラー: #{e.message}"
                ensure
                  workbook&.close if defined?(workbook) && workbook
                  temp_file.close
                  temp_file.unlink
                end
                break
              end
            end
          end

          # 営業、工程設計、検査のファイルは毎回確認
          pro.documents.each do |doc|
            filename = doc.filename.to_s
            next unless filename.include?('プロセスフロー')

            begin
              temp_file = Tempfile.new(['temp', File.extname(filename)])
              temp_file.binmode
              temp_file.write(doc.download)
              temp_file.rewind

              workbook = case File.extname(filename).downcase
                        when '.xlsx' then Roo::Excelx.new(temp_file.path)
                        when '.xls'  then Roo::Excel.new(temp_file.path)
                        else
                          next
                        end

              Rails.logger.info "=== ワークシート情報 ==="
              Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"

              # 適切なシートを探す
              target_sheet = nil
              workbook.sheets.each do |sheet_name|
                workbook.default_sheet = sheet_name
                Rails.logger.info "シート '#{sheet_name}' をチェック中..."

                # セル(2,21)とセル(2,22)の値を確認
                cell_2_21 = workbook.cell(2, 21)
                cell_2_22 = workbook.cell(2, 22)

                Rails.logger.info "シート '#{sheet_name}' - セル(2,21): #{cell_2_21.inspect}"
                Rails.logger.info "シート '#{sheet_name}' - セル(2,22): #{cell_2_22.inspect}"

                if cell_2_21.present? || cell_2_22.present?
                  target_sheet = sheet_name
                  Rails.logger.info "適切なシートが見つかりました: #{sheet_name}"
                  break
                end
              end

              unless target_sheet
                Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
                next
              end

              workbook.default_sheet = target_sheet
              Rails.logger.info "選択したシート: #{target_sheet}"
              Rails.logger.info "最終行: #{workbook.last_row}"
              Rails.logger.info "最終列: #{workbook.last_column}"

              # セルの値を文字列として取得し、デバッグ情報を出力
              if filename.include?('営業')
                @processflow_sales_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_sales_dept = workbook.cell(4, 13).to_s.strip
                @processflow_sales_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_sales_kanryou = pro.end_at.strftime('%y/%m/%d')
                @processflow_sales_check='☑'
                Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
              elsif filename.include?('工程設計')
                @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_design_dept = workbook.cell(4, 13).to_s.strip
                @processflow_design_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_design_kanryou = pro.end_at.strftime('%y/%m/%d')
                @processflow_design_check='☑'
                Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
              elsif filename.include?('検査')
                @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_inspection_dept = workbook.cell(4, 13).to_s.strip
                @processflow_inspection_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_inspection_kanryou = pro.end_at.strftime('%y/%m/%d')
                @processflow_inspection_check='☑'
                Rails.logger.info "検査引渡し承認者: \#{?processflow_inspection_person_in_charge}"
              end
            rescue StandardError => e
              Rails.logger.error "その他ファイル処理エラー: #{e.message}"
            ensure
              workbook&.close if defined?(workbook) && workbook
              temp_file.close
              temp_file.unlink
            end
          end

        rescue StandardError => e
          Rails.logger.error "ファイル処理エラー: #{e.message}"
        end
      else
        '☐'
      end
    end
  end

  def collect_floor_plan_layout(pro, stage)
    if stage == 'フロアプランレイアウト'
      @floor_plan_layout_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @floor_plan_layout_kanryou = pro.end_at.strftime('%y/%m/%d')
      @floor_plan_layout_person_in_charge = "鈴木"
      @floor_plan_layout_check = if pro.documents.attached?

        '☑'
      else
        '☐'
      end
    end
  end

  def collect_control_plan(pro, stage)
    if %w[量産コントロールプラン 試作コントロールプラン].include?(stage)
      @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
      @cp_check = if pro.documents.attached?
                    '☑'
                  else
                    '☐'
                  end
    end
  end

  def collect_characteristics_matrix(pro, stage)
    if stage == '特性マトリクス'
      @special_characteristics_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @special_characteristics_kanryou = pro.end_at.strftime('%y/%m/%d')
      @special_characteristics_person_in_charge = "鈴木"
      @special_characteristics_check = if pro.documents.attached?

        '☑'
      else
        '☐'
      end
    end
  end

  def collect_validation_record(pro, stage)
    if stage == '妥当性確認記録_金型設計'
      @datou_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @datou_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @datou_check = '☑'

        # 変数の設定
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*#{partnumber}*妥当性確認記録*"
        Rails.logger.info "Path= #{pattern}"

        files = Dir.glob(pattern)
        files.each do |file|
          workbook = nil
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file)
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file)
          else
            break
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # X36のセルの値を取得
          # RubyXLライブラリでExcelのセルを参照する際、行と列のインデックスは0から始まります。
          # したがって、1行1列目のセルは worksheet.cell(1, 1) としてアクセスされます。
          # したがって、セルX36を指定する場合:
          # 行番号: 36 - 1 = 35
          # 列番号: Xは24番目の列なので、24 - 1 = 23
          @datou_result = worksheet.cell(36, 24).presence || worksheet.cell(41, 13)
          @datou_person_in_charge = worksheet.cell(39, 22)
          @datou_kanryou = worksheet.cell(37, 6).presence || worksheet.cell(43, 4)
          Rails.logger.info '妥当性確認' # 追加
          Rails.logger.info "@partnumber= #{@partnumber}" # 追加
          Rails.logger.info "@datou_result #{@datou_result}" # 追加
        end

      else
        @datou_check = '☐'
      end
    end
  end

  def collect_customer_requirements(pro, stage)
    if stage == '顧客要求事項検討会議事録_営業'
      @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
      @scr_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_packaging_specs(pro, stage)
    if stage == '梱包規格・仕様書'
      @packing_instruction_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @packing_instruction_kanryou = pro.end_at.strftime('%y/%m/%d')
      @packing_instruction_check = if pro.documents.attached?
        '☑'
      else
        '☐'
      end
    end
  end

  def collect_parts_inspection(pro, stage)
    if stage == '部品検査成績書'
      @parts_inspection_report_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @parts_inspection_report_kanryou = pro.end_at.strftime('%y/%m/%d')
      @parts_inspection_report_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_tech_specs(pro, stage)
    if stage == '技術仕様書'
      @specifications_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @specifications_kanryou = pro.end_at.strftime('%y/%m/%d')
      @specifications_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_drawings(pro, stage)
    if stage == '図面（数学的データを含む）' || stage == '図面・仕様書の変更'
      @drawing_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @drawing_kanryou = pro.end_at.strftime('%y/%m/%d')
      @drawing_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_press_instructions(pro, stage)
    if stage == 'プレス作業手順書'
      @stamping_instruction_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @stamping_instruction_kanryou = pro.end_at.strftime('%y/%m/%d')
      @stamping_instruction_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_process_inspection_record(pro, stage)
    if stage == '工程検査記録票'
      @process_inspection_record_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @process_inspection_record_kanryou = pro.end_at.strftime('%y/%m/%d')
      @process_inspection_record_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_visual_inspection_guideline(pro, stage)
    if stage == '外観検査要領書'
      @visual_inspection_youryousho_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @visual_inspection_youryousho_kanryou = pro.end_at.strftime('%y/%m/%d')
      @visual_inspection_youryousho_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_inspection_procedures(pro, stage)
    if stage == '検査手順書'
      @visual_inspection_tejyunsho_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @visual_inspection_tejyunsho_kanryou = pro.end_at.strftime('%y/%m/%d')
      @visual_inspection_tejyunsho_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_manufacturing_feasibility(pro, stage)
    if stage == '製造実現可能性検討書'
      @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
      @feasibility_check = if pro.documents.attached?
                             '☑'
                           else
                             '☐'
                           end
    end
  end

  def collect_process_fmea(pro, stage)
    if stage == 'プロセスFMEA' || stage == 'プロセス故障モード影響解析（PFMEA）'
      @pfmea_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @pfmea_kanryou = pro.end_at.strftime('%y/%m/%d')

      if pro.documents.attached?
        begin
          # 変数の設定
          partnumber = pro.partnumber # ここには実際の値を設定してください
          # パスとファイル名のパターンを作成（プロジェクトルートからの相対パス）
          pattern = Rails.root.join('db', 'documents', "*#{partnumber}*PFMEA*").to_s
          Rails.logger.info "PFMEA検索パス: #{pattern}"

          files = Dir.glob(pattern)
          files.each do |file|
            begin
              workbook = case File.extname(file).downcase
                        when '.xlsx'
                          Roo::Excelx.new(file)
                        when '.xls'
                          Roo::Excel.new(file)
                        else
                          next
                        end

              worksheet = workbook.sheet(0)
              @pfmea_check = '☑'
              #@pfmea_person_in_charge = worksheet.cell(6, 13)
              cell_value = worksheet.cell(6, 13)
              Rails.logger.info "PFMEA担当者セル(M6)の値: #{cell_value.inspect}"
              @pfmea_person_in_charge = cell_value

              Rails.logger.info "PFMEA処理中"
              Rails.logger.info "品番: #{partnumber}"
              Rails.logger.info "担当者: \#{?pfmea_person_in_charge}"

            rescue StandardError => e
              Rails.logger.error "PFMEAファイル(#{file})の処理中にエラーが発生: #{e.message}"
              Rails.logger.error e.backtrace.join("\n")
            end
          end
        rescue StandardError => e
          Rails.logger.error "PFMEA処理全体でエラーが発生: #{e.message}"
          Rails.logger.error e.backtrace.join("\n")
        end
      end

      # ファイルが添付されていない、またはエラーが発生した場合のデフォルト値
      @pfmea_check ||= '☐'
    end
  end

  def collect_dr_meeting_minutes(pro, stage)
    if stage == 'DR会議議事録_金型設計'
      @dr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @dr_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*D.R会議議事録*"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)
        # 各ファイルに対して処理を行う
        files.each do |file|
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break

          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # i4のセルの値を取得

          # @dr_kanagata_shiteki = worksheet.cell(12, 1).nil? ? "" : worksheet.cell(12, 1).to_s + worksheet.cell(13, 1).to_s
          # @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s}.compact.join("\n")
          # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
          # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
          # 以下のように変更します：

          @dr_kanagata_shiteki = (12..28).map { |row| worksheet.cell(row, 1)&.to_s }.compact.reject(&:empty?).join("\n")
          @dr_kanagata_shochi = (12..28).map { |row| worksheet.cell(row, 6)&.to_s }.compact.reject(&:empty?).join("\n")
          @dr_kanagata_try_kekka = (12..28).map { |row| worksheet.cell(row, 11)&.to_s }.compact.reject(&:empty?).join("\n")
        end

        @dr_check = '☑'
      else
        @dr_check = '☐'
      end
    end
  end

  def collect_msa_grr(pro, stage)
    if stage == '測定システム解析（MSA)' # GRR
      @grr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @grr_kanryou = pro.end_at.strftime('%y/%m/%d')

      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*ゲージR&R*#{partnumber}*"
        Rails.logger.info "Path= #{pattern}"
        files = Dir.glob(pattern)
        @grr_count = files.size

        if @insert_rows_to_excel_template_msa == true # 初回のファイルのみサブルーチン処理
          insert_rows_to_excel_template_msa # ファイルの数だけ行を挿入するサブルーチン処理
        end

        # 各記号の初期化
        @grr = 0
        @ndc = 0

        files.each_with_index do |file, i| # with_indexでインデックスiを追加
          if file.end_with?('.xlsx')
            workbook = Roo::Excelx.new(file)
          elsif file.end_with?('.xls')
            workbook = Roo::Excel.new(file)
          else
            raise 'Unsupported file format'
          end

          worksheet = workbook.sheet(0)

          @debagtest = ''
          # if worksheet.cell(4, 24) != nil

          instance_variable_set("@grr_kanryou_#{i + 1}", worksheet.cell(2, 8))
          instance_variable_set("@grr_yotei_#{i + 1}", worksheet.cell(2, 8))
          instance_variable_set("@grr_person_in_charge_#{i + 1}", worksheet.cell(36, 9))
          instance_variable_set("@grr_approved_#{i + 1}", worksheet.cell(36, 9))

          # end
          instance_variable_set("@grr_no_#{i + 1}", worksheet.cell(4, 2).to_s)

          instance_variable_set("@grr_#{i + 1}", worksheet.cell(23, 8).round(2))
          instance_variable_set("@ndc_#{i + 1}", worksheet.cell(31, 8).round(2))

          if worksheet.cell(23, 8) <= 10
            instance_variable_set("@grr_result_#{i + 1}", '合格')
          elsif worksheet.cell(23, 8) > 10 && worksheet.cell(23, 8) < 30
            instance_variable_set("@grr_result_#{i + 1}", '十分ではないが合格')
          else
            instance_variable_set("@grr_result_#{i + 1}", '不合格')
          end

          if worksheet.cell(31, 8) >= 5
            instance_variable_set("@ndc_result_#{i + 1}", '合格')
          else
            instance_variable_set("@ndc_result_#{i + 1}", '不合格')
          end
        end

        @grr_check = '☑'
      else
        @grr_check = '☐'

      end
      Rails.logger.info "@grr_person_in_charge_1= #{@grr_person_in_charge_1}" # 追加
      Rails.logger.info "@grr_result_1= #{@grr_result_1}"  # 追加
      Rails.logger.info "@ndc_result_1= #{@ndc_result_1}"  # 追加

      Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

    end
  end

  def collect_msa_crosstab(pro, stage)
    if stage == '測定システム解析（MSA)' # クロスタブ
      @msa_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @msa_kanryou = pro.end_at.strftime('%y/%m/%d')

      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*#{partnumber}*計数値MSA報告書*"
        Rails.logger.info "Path= #{pattern}"
        files = Dir.glob(pattern)
        @msa_crosstab_count = files.size

        if @insert_rows_to_excel_template == true # 初回のファイルのみサブルーチン処理
          insert_rows_to_excel_template # ファイルの数だけ行を挿入するサブルーチン処理
        end

        # 各記号のカウントを初期化
        @maru_count = 0
        @batsu_count = 0
        @sankaku_count = 0
        @oomaru_count = 0

        files.each_with_index do |file, i| # with_indexでインデックスiを追加
          workbook = Roo::Excelx.new(file)
          worksheet = workbook.sheet(0)

          @debagtest = ''
          # if worksheet.cell(4, 24) != nil

          instance_variable_set("@msa_crosstab_kanryou_#{i + 1}", worksheet.cell(4, 24))
          instance_variable_set("@msa_crosstab_recorder_#{i + 1}", worksheet.cell(6, 24))
          instance_variable_set("@msa_crosstab_person_in_charge_#{i + 1}", worksheet.cell(120, 29))
          instance_variable_set("@msa_crosstab_approved_#{i + 1}", worksheet.cell(120, 27))
          @debagtest = worksheet.cell(76, 29)
          Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加
          Rails.logger.info "i= #{i}" # 追加

          # end

          instance_variable_set("@inspector_name_a_#{i + 1}", worksheet.cell(8, 10))
          instance_variable_set("@inspector_name_b_#{i + 1}", worksheet.cell(8, 16))
          instance_variable_set("@inspector_name_c_#{i + 1}", worksheet.cell(8, 22))
          instance_variable_set("@inspector_a_result_#{i + 1}", worksheet.cell(131, 7))
          instance_variable_set("@inspector_b_result_#{i + 1}", worksheet.cell(131, 11))
          instance_variable_set("@inspector_c_result_#{i + 1}", worksheet.cell(131, 15))
        end

        @msa_crosstab_check = '☑'
      else
        @msa_crosstab_check = '☐'
        @msa_crosstab_count = 0
      end
      Rails.logger.info "@msa_crosstab_person_in_charge_0= #{@msa_crosstab_person_in_charge_0}"  # 追加
      Rails.logger.info "@msa_crosstab_person_in_charge_1= #{@msa_crosstab_person_in_charge_1}"  # 追加
      Rails.logger.info "@msa_crosstab_person_in_charge_2= #{@msa_crosstab_person_in_charge_2}"  # 追加
      Rails.logger.info "@msa_crosstab_person_in_charge_3= #{@msa_crosstab_person_in_charge_3}"  # 追加
      Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}" # 追加

    end
  end

  def collect_dimensional_measurement(pro, stage)
    if stage == '寸法測定結果' # 型検
      @kataken_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @kataken_kanryou = pro.end_at.strftime('%y/%m/%d')

      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*#{partnumber}*検定報告書*"
        Rails.logger.info "Path= #{pattern}"

        files = Dir.glob(pattern)
        files.each do |file|
          workbook = nil
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file)
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file)
          else
            break
          end

          # シートの名前が"data"または"データ"を含むかどうかを確認
          matching_sheets = workbook.sheets.select do |name|
            name.downcase.include?('data') || name.include?('データ')
          end

          if matching_sheets.any?
            worksheet = workbook.sheet(matching_sheets.first)

            @kataken_person_in_charge = worksheet.cell(50, 71)
            @cpk_manager = worksheet.cell(50, 76)

            @kataken_kanryou = worksheet.cell(3, 27) if worksheet.cell(3, 27) != nil

            @kataken_cpk_OK = 0
            @kataken_cpk_NG = 0
            (1..200).each do |row|
              next unless worksheet.cell(row, 2) == 'Cpk' # B列はインデックス2

              (3..30).each do |col| # C列からAD列はインデックス3から30
                raw_value = worksheet.cell(row, col)
                next unless raw_value.is_a?(Numeric) # 数値の場合のみ処理を行う

                value = raw_value.to_f
                if value >= 1.67
                  @kataken_cpk_OK += 1
                else
                  @kataken_cpk_NG += 1
                end
              end
            end

            @kataken_spec_OK = 0
            @kataken_spec_NG = 0
            (1..200).each do |row|
              next unless worksheet.cell(row, 2) == 'Spec' # B列はインデックス2

              (3..30).each do |col| # C列からAD列はインデックス3から30
                value = worksheet.cell(row, col)
                if value == 'OK'
                  @kataken_spec_OK += 1
                elsif value == 'NG'
                  @kataken_spec_NG += 1
                end
              end
            end

            @kataken_spec_result = @kataken_spec_NG.zero? ? '合格' : '不合格'
            @kataken_cpk_result = @kataken_cpk_NG.zero? ? '合格' : '不合格'
          else
            @kataken_spec_result = 'データシート無し'
            @kataken_cpk_result = 'データシート無し'
            next # 次のファイルに移動
          end
        end

        @kataken_check = '☑'
      else
        @kataken_check = '☐'
      end
    end
  end

  def collect_initial_process_survey(pro, stage)
    if stage == '初期工程調査結果'
      @cpk_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @cpk_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*工程能力(Ppk)調査表*"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)
        # 各ファイルに対して処理を行う
        files.each do |file|
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # i4のセルの値を取得
          @cpk_person_in_charge = worksheet.cell(50, 71)
          @cpk_manager = worksheet.cell(50, 76)

          satisfied = '工程能力は満足している'
          not_satisfied = '工程能力は不足している'

          # チェックするセルの位置
          check_addresses = %w[E N W AF AO AX BG BP BY].map { |col| "#{col}44" }

          # 初期値
          satisfied_count = 0
          not_satisfied_count = 0

          # すべてのシートをループ
          workbook.sheets.each do |sheet_name|
            worksheet = workbook.sheet(sheet_name)

            check_addresses.each do |cell_address|
              row, col = cell_address_to_position(cell_address)
              cell_value = worksheet.cell(row, col)

              satisfied_count += 1 if cell_value == satisfied
              not_satisfied_count += 1 if cell_value == not_satisfied
            end
          end

          # 結果の設定
          @cpk_result = if not_satisfied_count.positive?
                          not_satisfied
                        elsif satisfied_count.positive?
                          satisfied
                        else
                          '結果なし' # この行は必要に応じて変更または削除してください
                        end
          @cpk_satisfied_count = satisfied_count
          @cpk_not_satisfied_count = not_satisfied_count

          @cpk_person_in_charge = worksheet.cell(50, 76) # 担当者名

          if worksheet.cell(3, 59) != nil
            @cpk_yotei = worksheet.cell(3, 59)
            @cpk_kanryou = worksheet.cell(3, 59)
          end
        end
        @cpk_check = '☑'
      else
        @cpk_check = '☐'
      end
    end
  end

  def collect_prototype_instructions(pro, stage)
    if stage == '試作製造指示書_営業'
      @shisaku_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @shisaku_kanryou = pro.end_at.strftime('%y/%m/%d')
    end
  end

  def collect_mold_instructions(pro, stage)
    if stage == '金型製造指示書_営業'
      @kanagata_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @kanagata_kanryou = pro.end_at.strftime('%y/%m/%d')
    end
  end

  def collect_design_plan(pro, stage)
    if stage == '設計計画書_金型設計'
      @plan_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @plan_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*設計計画書*"
        # pattern = "/myapp/db/documents/NT2394-P43_PM81EB_設計計画書.xls"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)
        # 各ファイルに対して処理を行う
        files.each do |file|
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # i4のセルの値を取得
          @plan_designer = worksheet.cell(4, 9)
          @plan_manager = worksheet.cell(5, 9)
          @plan_customer = worksheet.cell(6, 3)
          @plan_risk = worksheet.cell(41, 4).nil? ? '' : worksheet.cell(41, 4).to_s + worksheet.cell(42, 4).to_s
          @plan_opportunity = if worksheet.cell(43,
                                                4).nil?
                                ''
                              else
                                worksheet.cell(43, 4).to_s + worksheet.cell(44, 4).to_s
                              end

          if worksheet.cell(10, 4) != nil
            @plan_yotei = worksheet.cell(11, 4)
            @plan_kanryou = worksheet.cell(11, 6)
          end
        end
      end
    end
  end

  def collect_dr_concept_minutes(pro, stage)
    if stage == 'DR構想検討会議議事録_生産技術'
      @dr_setsubi_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @dr_setsubi_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*DR構想検討会議議事録*"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)

        @dr_setsubi_count = files.size # 追加　ファイルの数カウントし、何行挿入するか決定する

        if @insert_rows_to_excel_template_dr_setsubi == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
          insert_rows_to_excel_template_dr_setsubi # セルに必要な行数だけ行を挿入するサブルーチン
        end

        # 各ファイルに対して処理を行う
        files.each_with_index do |file, i| # with_indexでインデックスiを追加
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # i4のセルの値を取得
          # @dr_setsubi_designer = worksheet.cell(2, 17)
          # @dr_setsubi_manager = worksheet.cell(2, 16)
          # @dr_setsubi_equipment_name = worksheet.cell(5, 11) #K5
          # @dr_setsubi_shiteki = (11..25).map { |row| worksheet.cell(row, 1)&.to_s}.compact.join("\n")

          instance_variable_set("@dr_setsubi_name_#{i + 1}", worksheet.cell(5, 11))

          instance_variable_set("@dr_setsubi_designer_#{i + 1}", worksheet.cell(2, 17))
          instance_variable_set("@dr_setsubi_manager_#{i + 1}", worksheet.cell(2, 16))
          instance_variable_set("@dr_setsubi_equipment_name_#{i + 1}", worksheet.cell(5, 11))
          instance_variable_set("@dr_setsubi_yotei_#{i + 1}", convert_excel_date(worksheet.cell(5, 15)))
          instance_variable_set("@dr_setsubi_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(5, 15)))
          # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
          # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
          # 以下のように変更します：
          instance_variable_set("@dr_setsubi_shiteki_#{i + 1}",
                                (11..25).map { |row| worksheet.cell(row, 1)&.to_s }
                                .compact
                                .reject(&:empty?)
                                .join("\n"))

          # if worksheet.cell(5, 15) != nil
          #  @dr_setsubi_yotei  =worksheet.cell(5,15)
          #  @dr_setsubi_kanryou=worksheet.cell(5,15)
          # end
        end
        @dr_setsubi_check = '☑'
      else
        @dr_setsubi_check = '☐'
      end
    end
  end

  def collect_progress_management(pro, stage)
    if stage == '進捗管理票_生産技術'
      @dr_seigi_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @dr_seigi_plan_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        # 変数の設定
        partnumber = pro.partnumber # ここには実際の値を設定してください
        # パスとファイル名のパターンを作成
        pattern = "/myapp/db/documents/*#{partnumber}*進捗管理票*"
        # pattern = "/myapp/db/documents/NT2394-P43_PM81EB_設計計画書.xls"
        Rails.logger.info "Path= #{pattern}"
        # パターンに一致するファイルを取得
        files = Dir.glob(pattern)

        @progress_management_count = files.size # 追加　ファイルの数カウントし、何行挿入するか決定する

        if @insert_rows_to_excel_template_progress_management == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
          insert_rows_to_excel_template_progress_management # セルに必要な行数だけ行を挿入するサブルーチン
        end

        # 各ファイルに対して処理を行う
        # files.each do |file|
        files.each_with_index do |file, i| # with_indexでインデックスiを追加
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            break
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          # すみません、混乱を招いてしまったようで。Roo gemはExcelの日付をシリアル日付として読み込む場合があります。
          # Excelでは、日付は1900年1月1日からの日数として保存されます。
          # したがって、数値をRubyのDateオブジェクトに変換するために、Excelの日付のオフセット（1900年1月1日から数えた日数）
          # を使用する必要があります。
          # 次の関数は、Excelのシリアル日付を日付文字列に変換します：

          # def convert_excel_date(serial_date)
          #  # Excelの日付は1900年1月1日から数えた日数として保存されている
          #  base_date = Date.new(1899,12,30)
          #  # シリアル日付を日付に変換
          #  date = base_date + serial_date.to_i
          #  # 1899年12月30日の場合、"-"を返す
          #  return "-" if date == base_date
          #  # 日付を文字列に変換
          #  date.strftime('%Y/%m/%d')
          # end

          instance_variable_set("@progress_management_seigi_equipment_name_#{i + 1}", worksheet.cell(3, 4)) # F列とおもったらD列だった。。

          # @progress_management_seigi_design_name = worksheet.cell(14, 8)           #H13 設計担当者名
          # @progress_management_seigi_design_yotei = convert_excel_date(worksheet.cell(12, 6)) #F12 設計予定日
          # @progress_management_seigi_design_kanryou = convert_excel_date(worksheet.cell(12, 7)) #G12 設計完了日

          instance_variable_set("@progress_management_seigi_design_name_#{i + 1}", worksheet.cell(14, 8))
          instance_variable_set("@progress_management_seigi_design_yotei_#{i + 1}",
                                convert_excel_date(worksheet.cell(12, 6)))
          instance_variable_set("@progress_management_seigi_design_kanryou_#{i + 1}",
                                convert_excel_date(worksheet.cell(12, 7)))

          # @progress_management_seigi_assembly_name = worksheet.cell(27, 8)         #H27 組立担当者名
          # @progress_management_seigi_assembly_yotei = convert_excel_date(worksheet.cell(26, 6)) #F26 組立予定日
          # @progress_management_seigi_assembly_kanryou = convert_excel_date(worksheet.cell(26, 7)) #G26 組立完了日

          instance_variable_set("@progress_management_seigi_assembly_name_#{i + 1}", worksheet.cell(27, 8))
          instance_variable_set("@progress_management_seigi_assembly_yotei_#{i + 1}",
                                convert_excel_date(worksheet.cell(26, 6)))
          instance_variable_set("@progress_management_seigi_assembly_kanryou_#{i + 1}",
                                convert_excel_date(worksheet.cell(26, 7)))

          # @progress_management_seigi_wiring_name = worksheet.cell(30, 8)           #H30 配線担当者名
          # @progress_management_seigi_wiring_yotei = convert_excel_date(worksheet.cell(29, 6)) #F29 配線予定日
          # @progress_management_seigi_wiring_kanryou = convert_excel_date(worksheet.cell(29, 7)) #G29 配線完了日

          instance_variable_set("@progress_management_seigi_wiring_name_#{i + 1}", worksheet.cell(30, 8))
          instance_variable_set("@progress_management_seigi_wiring_yotei_#{i + 1}",
                                convert_excel_date(worksheet.cell(29, 6)))
          instance_variable_set("@progress_management_seigi_wiring_kanryou_#{i + 1}",
                                convert_excel_date(worksheet.cell(29, 7)))

          # @progress_management_seigi_program_name = worksheet.cell(34, 8)          #H34 プログラム担当者名
          # @progress_management_seigi_program_yotei = convert_excel_date(worksheet.cell(33, 6)) #F33 プログラム予定日
          # @progress_management_seigi_program_kanryou = convert_excel_date(worksheet.cell(33, 7)) #G33 プログラム完了日

          instance_variable_set("@progress_management_seigi_program_name_#{i + 1}", worksheet.cell(34, 8))
          instance_variable_set("@progress_management_seigi_program_yotei_#{i + 1}",
                                convert_excel_date(worksheet.cell(33, 6)))
          instance_variable_set("@progress_management_seigi_program_kanryou_#{i + 1}",
                                convert_excel_date(worksheet.cell(33, 7)))

          if worksheet.cell(10, 4) != nil
            @dr_seigi_yotei = worksheet.cell(33, 6) # F33　プログラム予定日
            @dr_seigi_kanryou = worksheet.cell(33, 7) # G33 プログラム完了日
          end
        end
      end
    end
  end

  def collect_initial_flow_record(pro, stage)
    if stage == '初期流動検査記録'
      @shoki_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @shoki_kanryou = pro.end_at.strftime('%y/%m/%d')
      @shoki_check = '☑'
      @shoki_person_in_charge = '石栗'
    end
  end

  def collect_material_specs(pro, stage)
    if stage == '材料仕様書'
      @material_specification_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @material_specification_kanryou = pro.end_at.strftime('%y/%m/%d')
      @material_specification_check = '☑'
    end
  end

  def collect_process_instructions(pro, stage)
    if stage == 'プロセス指示書'
      @wi_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @wi_kanryou = pro.end_at.strftime('%y/%m/%d')
    end
  end

  def insert_rows_to_excel_template_msa
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_msa = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @grr_count >= 2
              @grr_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'GRR' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("品証（\#{?grr_person_in_charge_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?grr_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?grr_kanryou_#{i + 2}}")
      worksheet[row_number][14].change_contents("項番：\#{?grr_no_#{i + 2}} \n GRR値：\#{?grr_#{i + 2}}%、GRR結果：\#{?grr_result_#{i + 2}} \n ndc値：\#{?ndc_#{i + 2}}、ndc結果：\#{?ndc_result#{i + 2}}")

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @msa_crosstab_count >= 2
              @msa_crosstab_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'クロスタブ' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("品証（\#{?msa_crosstab_person_in_charge_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?msa_crosstab_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?msa_crosstab_kanryou_#{i + 2}}")
      worksheet[row_number][14].change_contents("\#{?inspector_name_a_#{i + 2}}：\#{?inspector_a_result_#{i + 2}}、\#{?inspector_name_b_#{i + 2}}：\#{?inspector_b_result_#{i + 2}}、\#{?inspector_name_c_#{i + 2}}：\#{?inspector_c_result_#{i + 2}}")

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template_dr_setsubi
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_dr_setsubi = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @dr_setsubi_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == 'デザインレビュー(設備)' # D列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # @msa_crosstab_countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定
      worksheet[row_number][7].change_contents("生技（\#{?dr_setsubi_designer_#{i + 2}}）")
      worksheet[row_number][10].change_contents("\#{?dr_setsubi_yotei_#{i + 2}}")
      worksheet[row_number][12].change_contents("\#{?dr_setsubi_kanryou_#{i + 2}}")
      # worksheet[row_number][14].change_contents("\#{?dr_setsubi_shiteki_#{i + 2}}")

      content = "設備名：\#{?dr_setsubi_name_#{i + 2}}\n\n\#{?dr_setsubi_shiteki_#{i + 2}}"
      worksheet[row_number][14].change_contents(content)

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 3, insert_row_number + count - 1, 6)

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  def insert_rows_to_excel_template_progress_management
    if @excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report.xlsx')
      @excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/process_design_plan_report_modified.xlsx')
    end
    @insert_rows_to_excel_template_progress_management = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @progress_management_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (13..85).each do |row|
      if worksheet[row][3].value == '設備設計' # D列を参照。
        insert_row_number = row + 4 # 挿入する行番号を取得(3行分下の行から挿入開始)
        break
      end
    end

    # @msa_crosstab_countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      # row_number = insert_row_number + i  # 正しい行番号を計算
      row_number = insert_row_number + (i * 4) # 正しい行番号を計算
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)
      worksheet.insert_row(row_number)

      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定

      worksheet[row_number][14].change_contents("設備名：\#{?progress_management_seigi_equipment_name_#{i + 2}}") # H13 設備名称

      # @progress_management_seigi_design_name = worksheet.cell(14, 8)           #H13 設計担当者名
      worksheet[row_number][7].change_contents("生技（\#{?progress_management_seigi_design_name_#{i + 2}}）") # H13 設計担当者名
      # @progress_management_seigi_design_yotei = convert_excel_date(worksheet.cell(12, 6)) #F12 設計予定日
      worksheet[row_number][10].change_contents("\#{?progress_management_seigi_design_yotei_#{i + 2}}")
      # @progress_management_seigi_design_kanryou = convert_excel_date(worksheet.cell(12, 7)) #G12 設計完了日
      worksheet[row_number][12].change_contents("\#{?progress_management_seigi_design_kanryou_#{i + 2}}")

      # @progress_management_seigi_assembly_name = worksheet.cell(27, 8)         #H27 組立担当者名
      worksheet[row_number + 1][7].change_contents("生技（\#{?progress_management_seigi_assembly_name_#{i + 2}}）") # H27 組立担当者名
      # @progress_management_seigi_assembly_yotei = convert_excel_date(worksheet.cell(26, 6)) #F26 組立予定日
      worksheet[row_number + 1][10].change_contents("\#{?progress_management_seigi_assembly_yotei_#{i + 2}}")
      # @progress_management_seigi_assembly_kanryou = convert_excel_date(worksheet.cell(26, 7)) #G26 組立完了日
      worksheet[row_number + 1][12].change_contents("\#{?progress_management_seigi_assembly_kanryou_#{i + 2}}")

      # @progress_management_seigi_wiring_name = worksheet.cell(30, 8)           #H30 配線担当者名
      worksheet[row_number + 2][7].change_contents("生技（\#{?progress_management_seigi_wiring_name_#{i + 2}}）") # H30 配線担当者名
      # @progress_management_seigi_wiring_yotei = convert_excel_date(worksheet.cell(29, 6)) #F29 配線予定日
      worksheet[row_number + 2][10].change_contents("\#{?progress_management_seigi_wiring_yotei_#{i + 2}}")
      # @progress_management_seigi_wiring_kanryou = convert_excel_date(worksheet.cell(29, 7)) #G29 配線完了日
      worksheet[row_number + 2][12].change_contents("\#{?progress_management_seigi_wiring_kanryou_#{i + 2}}")

      # @progress_management_seigi_program_name = worksheet.cell(34, 8)          #H34 プログラム担当者名
      worksheet[row_number + 3][7].change_contents("生技（\#{?progress_management_seigi_program_name_#{i + 2}}）") # H34 プログラム担当者名
      # @progress_management_seigi_program_yotei = convert_excel_date(worksheet.cell(33, 6)) #F33 プログラム予定日
      worksheet[row_number + 3][10].change_contents("\#{?progress_management_seigi_program_yotei_#{i + 2}}")
      # @progress_management_seigi_program_kanryou = convert_excel_date(worksheet.cell(33, 7)) #G33 プログラム完了日
      worksheet[row_number + 3][12].change_contents("\#{?progress_management_seigi_program_kanryou_#{i + 2}}")

      #    if worksheet.cell(10, 4) != nil
      #      @dr_seigi_yotei  =worksheet.cell(33, 6) #F33　プログラム予定日
      #      @dr_seigi_kanryou=worksheet.cell(33, 7) #G33 プログラム完了日
      #    end

      worksheet[row_number][3].change_contents('設備設計')
      worksheet[row_number + 1][3].change_contents('設備製作')
      worksheet[row_number + 1][5].change_contents('組立')
      worksheet[row_number + 2][5].change_contents('配線')
      worksheet[row_number + 3][5].change_contents('プログラム')

      worksheet.merge_cells(row_number, 3, row_number, 6)

      worksheet.merge_cells(row_number + 1, 3, row_number + 3, 4) # D列、E列を結合

      worksheet.merge_cells(row_number + 1, 5, row_number + 1, 6)
      worksheet.merge_cells(row_number + 2, 5, row_number + 2, 6)
      worksheet.merge_cells(row_number + 3, 5, row_number + 3, 6)

      worksheet.merge_cells(row_number, 14, row_number + 3, 23) # 設備名称のセルを結合

      # H列、I列、J列を結合
      worksheet.merge_cells(row_number, 7, row_number, 9)
      worksheet.merge_cells(row_number, 10, row_number, 11)
      worksheet.merge_cells(row_number, 12, row_number, 13)

      worksheet.merge_cells(row_number + 1, 7, row_number + 1, 9)
      worksheet.merge_cells(row_number + 1, 10, row_number + 1, 11)
      worksheet.merge_cells(row_number + 1, 12, row_number + 1, 13)

      worksheet.merge_cells(row_number + 2, 7, row_number + 2, 9)
      worksheet.merge_cells(row_number + 2, 10, row_number + 2, 11)
      worksheet.merge_cells(row_number + 2, 12, row_number + 2, 13)

      worksheet.merge_cells(row_number + 3, 7, row_number + 3, 9)
      worksheet.merge_cells(row_number + 3, 10, row_number + 3, 11)
      worksheet.merge_cells(row_number + 3, 12, row_number + 3, 13)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    # worksheet.merge_cells(insert_row_number-1, 3, insert_row_number+count-1, 6)

    workbook.write('lib/excel_templates/process_design_plan_report_modified.xlsx')
  end

  # すみません、混乱を招いてしまったようで。Roo gemはExcelの日付をシリアル日付として読み込む場合があります。
  # Excelでは、日付は1900年1月1日からの日数として保存されます。
  # したがって、数値をRubyのDateオブジェクトに変換するために、Excelの日付のオフセット（1900年1月1日から数えた日数）
  # を使用する必要があります。
  # 次の関数は、Excelのシリアル日付を日付文字列に変換します：

  def convert_excel_date(serial_date)
    # Excelの日付は1900年1月1日から数えた日数として保存されている
    base_date = Date.new(1899, 12, 30)
    # シリアル日付を日付に変換
    date = base_date + serial_date.to_i
    # 1899年12月30日の場合、"-"を返す
    return '-' if date == base_date

    # 日付を文字列に変換
    date.strftime('%Y/%m/%d')
  end

  def cell_address_to_position(cell_address)
    col = cell_address.gsub(/\d/, '')
    row = cell_address.gsub(/\D/, '').to_i
    col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
    [row, col_index]
  end

  # 金型製作記録から担当者・日程情報を読み込む
  def collect_kanagata_record
    catch :found do
      @all_products.each do |all|
        stage = @dropdownlist[all.stage.to_i]
        next unless stage == '金型製作記録'

        Rails.logger.info '金型製作記録(添付資料確認前)'
        next unless all.documents.attached?

        pattern = '/myapp/db/documents/**/*.{xls,xlsx}'
        Rails.logger.info "Path= #{pattern}"
        Dir.glob(pattern) do |file|
          next unless file.include?('金型製作記録')

          Rails.logger.info '金型製作記録(添付資料確認後)'
          workbook = case File.extname(file)
                     when '.xlsx' then Roo::Excelx.new(file)
                     when '.xls'  then Roo::Excel.new(file)
                     end
          workbook.sheets.each do |sheet|
            worksheet = workbook.sheet(sheet)
            next if worksheet.last_row.nil?

            (1..worksheet.last_row).each do |i|
              row = worksheet.row(i)
              next unless row[4] == @partnumber

              @dieset_person       = row[11]
              @kanagata_yotei      = row[9]
              @kanagata_kanryou    = row[10]
              @kanagata_katagouzou = row[8]
              @kanagata_remark     = row[12]
              throw :found
            end
          end
        end
      end
    end
  end

  # 治具管理台帳から治具情報を読み込む
  def collect_jig_ledger
    catch :found do
      @all_products.each do |all|
        begin
          stage = @dropdownlist[all.stage.to_i]
          next unless stage.present? && stage == '台帳'
          next unless all.documents&.attached?

          Dir.glob('/myapp/db/documents/**/*.{xls,xlsx}') do |file|
            next unless file.include?('治具管理台帳')

            begin
              workbook = case File.extname(file)
                         when '.xlsx' then Roo::Excelx.new(file)
                         when '.xls'  then Roo::Excel.new(file)
                         else next
                         end

              worksheet = workbook.sheet(0)
              (6..100).each do |row_number|
                cell_value = worksheet.cell(row_number, 9)
                next unless cell_value.present?

                values = cell_value.include?(',') ? cell_value.split(',') : [cell_value]
                Rails.logger.info("Row #{row_number}: Processing values: #{values.inspect}")

                values.each do |value|
                  next unless value.strip == @partnumber

                  @jigu_kanribangou      = worksheet.cell(row_number, 1)
                  @jigu_name             = worksheet.cell(row_number, 2)
                  @jigu_produced_date    = worksheet.cell(row_number, 5)
                  @jigu_seizou_dept      = worksheet.cell(row_number, 6)
                  @jigu_start_useage_date = worksheet.cell(row_number, 7)
                  @jigu_tantou           = worksheet.cell(row_number, 8)
                  @jigu_approved         = worksheet.cell(row_number, 11)
                  throw :found
                end
              end
            rescue StandardError => e
              Rails.logger.error("Error processing file #{file}: #{e.message}")
            end
          end
        rescue StandardError => e
          Rails.logger.error("Error processing product #{all}: #{e.message}")
        end
      end
    end
  end

end
