# frozen_string_literal: true

# Excelテンプレートに必要なデータを製品ドキュメントから収集するサービス。
# ProductsController#process_design_plan_report から呼び出され、
# 収集した値をコントローラのインスタンス変数に割り当てるためのハッシュを返す。
class ProductCreateDataService
  include ProcessFlowCollectable
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

  def collect_floor_plan_layout(pro, stage)
    if stage == 'フロアプランレイアウト'
      @floor_plan_layout_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @floor_plan_layout_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
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
      @controlplan_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @controlplan_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @cp_check = if pro.documents.attached?
                    '☑'
                  else
                    '☐'
                  end
    end
  end

  def collect_characteristics_matrix(pro, stage)
    if stage == '特性マトリクス'
      @special_characteristics_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @special_characteristics_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
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
      @datou_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @datou_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        @datou_check = '☑'
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('妥当性確認記録')

          with_roo_workbook(doc, filename) do |workbook|
            worksheet      = workbook.sheet(0)
            @datou_result           = worksheet.cell(36, 24).presence || worksheet.cell(41, 13)
            @datou_person_in_charge = worksheet.cell(39, 22)
            @datou_kanryou          = worksheet.cell(37, 6).presence  || worksheet.cell(43, 4)
            Rails.logger.info '妥当性確認'
            Rails.logger.info "@partnumber= #{@partnumber}"
            Rails.logger.info "@datou_result #{@datou_result}"
          end
        end
      else
        @datou_check = '☐'
      end
    end
  end

  def collect_customer_requirements(pro, stage)
    if stage == '顧客要求事項検討会議事録_営業'
      @scr_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @scr_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @scr_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_packaging_specs(pro, stage)
    if stage == '梱包規格・仕様書'
      @packing_instruction_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @packing_instruction_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @packing_instruction_check = if pro.documents.attached?
        '☑'
      else
        '☐'
      end
    end
  end

  def collect_parts_inspection(pro, stage)
    if stage == '部品検査成績書'
      @parts_inspection_report_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @parts_inspection_report_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @parts_inspection_report_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_tech_specs(pro, stage)
    if stage == '技術仕様書'
      @specifications_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @specifications_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @specifications_check = if pro.documents.attached?
                                '☑'
                              else
                                '☐'
                              end
    end

    # 納入仕様書のチェックを追加
    return unless stage == '納入仕様書' || (pro.documents.attached? && pro.documents.any? { |doc| doc.filename.to_s.include?('納入仕様書') })

    @specifications_check = '☑'
    return unless stage == '納入仕様書'

    @specifications_yotei = pro.deadline_at&.strftime('%y/%m/%d') || @specifications_yotei
    @specifications_kanryou = pro.end_at&.strftime('%y/%m/%d') || @specifications_kanryou
  end

  def collect_drawings(pro, stage)
    if stage == '図面（数学的データを含む）' || stage == '図面・仕様書の変更'
      @drawing_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @drawing_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @drawing_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_press_instructions(pro, stage)
    if stage == 'プレス作業手順書'
      @stamping_instruction_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @stamping_instruction_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @stamping_instruction_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_process_inspection_record(pro, stage)
    if stage == '工程検査記録票'
      @process_inspection_record_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @process_inspection_record_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @process_inspection_record_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_visual_inspection_guideline(pro, stage)
    if stage == '外観検査要領書'
      @visual_inspection_youryousho_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @visual_inspection_youryousho_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @visual_inspection_youryousho_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_inspection_procedures(pro, stage)
    if stage == '検査手順書'
      @visual_inspection_tejyunsho_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @visual_inspection_tejyunsho_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @visual_inspection_tejyunsho_check = if pro.documents.attached?
                     '☑'
                   else
                     '☐'
                   end
    end
  end

  def collect_manufacturing_feasibility(pro, stage)
    if stage == '製造実現可能性検討書'
      @scr_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @scr_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @feasibility_check = if pro.documents.attached?
                             '☑'
                           else
                             '☐'
                           end
    end
  end

  def collect_process_fmea(pro, stage)
    if stage == 'プロセスFMEA' || stage == 'プロセス故障モード影響解析（PFMEA）'
      @pfmea_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @pfmea_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''

      if pro.documents.attached?
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('PFMEA')

          with_roo_workbook(doc, filename) do |workbook|
            worksheet               = workbook.sheet(0)
            @pfmea_check            = '☑'
            @pfmea_person_in_charge = worksheet.cell(6, 13)
            Rails.logger.info "PFMEA担当者セル(M6)の値: #{@pfmea_person_in_charge.inspect}"
            Rails.logger.info "担当者: \#{?pfmea_person_in_charge}"
          end
        end
      end

      @pfmea_check ||= '☐'
    end
  end

  def collect_dr_meeting_minutes(pro, stage)
    if stage == 'DR会議議事録_金型設計'
      @dr_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @dr_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('D.R会議議事録')

          with_roo_workbook(doc, filename) do |workbook|
            worksheet = workbook.sheet(0)
            @dr_kanagata_shiteki    = (12..28).map { |row| worksheet.cell(row, 1)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_shochi     = (12..28).map { |row| worksheet.cell(row, 6)&.to_s }.compact.reject(&:empty?).join("\n")
            @dr_kanagata_try_kekka  = (12..28).map { |row| worksheet.cell(row, 11)&.to_s }.compact.reject(&:empty?).join("\n")
          end
        end
        @dr_check = '☑'
      else
        @dr_check = '☐'
      end
    end
  end

  def collect_msa_grr(pro, stage)
    if stage == '測定システム解析（MSA)' # GRR
      @grr_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @grr_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''

      if pro.documents.attached?
        grr_docs   = pro.documents.select { |doc| doc.filename.to_s.include?('ゲージR&R') }
        @grr_count = grr_docs.size

        insert_rows_to_excel_template_msa if @insert_rows_to_excel_template_msa

        @grr = 0
        @ndc = 0

        grr_docs.each_with_index do |doc, i|
          filename = doc.filename.to_s
          with_roo_workbook(doc, filename) do |workbook|
            worksheet  = workbook.sheet(0)
            @debagtest = ''
            instance_variable_set("@grr_kanryou_#{i + 1}", worksheet.cell(2, 8))
            instance_variable_set("@grr_yotei_#{i + 1}",   worksheet.cell(2, 8))
            instance_variable_set("@grr_person_in_charge_#{i + 1}", worksheet.cell(36, 9))
            instance_variable_set("@grr_approved_#{i + 1}", worksheet.cell(36, 9))
            instance_variable_set("@grr_no_#{i + 1}", worksheet.cell(4, 2).to_s)
            instance_variable_set("@grr_#{i + 1}", worksheet.cell(23, 8).round(2))
            instance_variable_set("@ndc_#{i + 1}", worksheet.cell(31, 8).round(2))

            grr_result = if worksheet.cell(23, 8) <= 10
                           '合格'
                         elsif worksheet.cell(23, 8) < 30
                           '十分ではないが合格'
                         else
                           '不合格'
                         end
            instance_variable_set("@grr_result_#{i + 1}", grr_result)
            instance_variable_set("@ndc_result_#{i + 1}", worksheet.cell(31, 8) >= 5 ? '合格' : '不合格')
          end
        end

        @grr_check = '☑'
      else
        @grr_check = '☐'
      end
      Rails.logger.info "@grr_person_in_charge_1= #{@grr_person_in_charge_1}"
      Rails.logger.info "@grr_result_1= #{@grr_result_1}"
      Rails.logger.info "@ndc_result_1= #{@ndc_result_1}"
      Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}"
    end
  end

  def collect_msa_crosstab(pro, stage)
    if stage == '測定システム解析（MSA)' # クロスタブ
      @msa_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @msa_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''

      if pro.documents.attached?
        crosstab_docs       = pro.documents.select { |doc| doc.filename.to_s.include?('計数値MSA報告書') }
        @msa_crosstab_count = crosstab_docs.size

        insert_rows_to_excel_template if @insert_rows_to_excel_template

        @maru_count    = 0
        @batsu_count   = 0
        @sankaku_count = 0
        @oomaru_count  = 0

        crosstab_docs.each_with_index do |doc, i|
          filename = doc.filename.to_s
          with_roo_workbook(doc, filename) do |workbook|
            worksheet  = workbook.sheet(0)
            @debagtest = worksheet.cell(76, 29)
            Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}"
            Rails.logger.info "i= #{i}"
            instance_variable_set("@msa_crosstab_kanryou_#{i + 1}",         worksheet.cell(4, 24))
            instance_variable_set("@msa_crosstab_recorder_#{i + 1}",         worksheet.cell(6, 24))
            instance_variable_set("@msa_crosstab_person_in_charge_#{i + 1}", worksheet.cell(120, 29))
            instance_variable_set("@msa_crosstab_approved_#{i + 1}",         worksheet.cell(120, 27))
            instance_variable_set("@inspector_name_a_#{i + 1}",              worksheet.cell(8, 10))
            instance_variable_set("@inspector_name_b_#{i + 1}",              worksheet.cell(8, 16))
            instance_variable_set("@inspector_name_c_#{i + 1}",              worksheet.cell(8, 22))
            instance_variable_set("@inspector_a_result_#{i + 1}",            worksheet.cell(131, 7))
            instance_variable_set("@inspector_b_result_#{i + 1}",            worksheet.cell(131, 11))
            instance_variable_set("@inspector_c_result_#{i + 1}",            worksheet.cell(131, 15))
          end
        end

        @msa_crosstab_check = '☑'
      else
        @msa_crosstab_check = '☐'
        @msa_crosstab_count = 0
      end
      Rails.logger.info "@msa_crosstab_person_in_charge_0= #{@msa_crosstab_person_in_charge_0}"
      Rails.logger.info "@msa_crosstab_person_in_charge_1= #{@msa_crosstab_person_in_charge_1}"
      Rails.logger.info "@msa_crosstab_person_in_charge_2= #{@msa_crosstab_person_in_charge_2}"
      Rails.logger.info "@msa_crosstab_person_in_charge_3= #{@msa_crosstab_person_in_charge_3}"
      Rails.logger.info "worksheet.cell(76, 29)= #{@debagtest}"
    end
  end

  def collect_dimensional_measurement(pro, stage)
    if stage == '寸法測定結果' # 型検
      @kataken_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @kataken_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''

      if pro.documents.attached?
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('検定報告書')

          with_roo_workbook(doc, filename) do |workbook|
            data_sheet = workbook.sheets.find { |name| name.downcase.include?('data') || name.include?('データ') }
            unless data_sheet
              @kataken_spec_result = 'データシート無し'
              @kataken_cpk_result  = 'データシート無し'
              next
            end

            worksheet = workbook.sheet(data_sheet)
            @kataken_person_in_charge = worksheet.cell(50, 71)
            @cpk_manager              = worksheet.cell(50, 76)
            @kataken_kanryou          = worksheet.cell(3, 27) if worksheet.cell(3, 27)

            @kataken_cpk_OK = 0
            @kataken_cpk_NG = 0
            (1..200).each do |row|
              next unless worksheet.cell(row, 2) == 'Cpk'
              (3..30).each do |col|
                raw_value = worksheet.cell(row, col)
                next unless raw_value.is_a?(Numeric)
                raw_value.to_f >= 1.67 ? @kataken_cpk_OK += 1 : @kataken_cpk_NG += 1
              end
            end

            @kataken_spec_OK = 0
            @kataken_spec_NG = 0
            (1..200).each do |row|
              next unless worksheet.cell(row, 2) == 'Spec'
              (3..30).each do |col|
                value = worksheet.cell(row, col)
                @kataken_spec_OK += 1 if value == 'OK'
                @kataken_spec_NG += 1 if value == 'NG'
              end
            end

            @kataken_spec_result = @kataken_spec_NG.zero? ? '合格' : '不合格'
            @kataken_cpk_result  = @kataken_cpk_NG.zero? ? '合格' : '不合格'
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
      @cpk_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @cpk_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        satisfied     = '工程能力は満足している'
        not_satisfied = '工程能力は不足している'
        check_addresses = %w[E N W AF AO AX BG BP BY].map { |col| "#{col}44" }

        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('工程能力') && filename.include?('Ppk')

          with_roo_workbook(doc, filename) do |workbook|
            satisfied_count     = 0
            not_satisfied_count = 0

            workbook.sheets.each do |sheet_name|
              ws = workbook.sheet(sheet_name)
              check_addresses.each do |cell_address|
                row, col   = cell_address_to_position(cell_address)
                cell_value = ws.cell(row, col)
                satisfied_count     += 1 if cell_value == satisfied
                not_satisfied_count += 1 if cell_value == not_satisfied
              end
            end

            worksheet = workbook.sheet(0)
            @cpk_result = if not_satisfied_count.positive?
                            not_satisfied
                          elsif satisfied_count.positive?
                            satisfied
                          else
                            '結果なし'
                          end
            @cpk_satisfied_count     = satisfied_count
            @cpk_not_satisfied_count = not_satisfied_count
            @cpk_person_in_charge    = worksheet.cell(50, 76)
            @cpk_manager             = worksheet.cell(50, 71)

            if worksheet.cell(3, 59)
              @cpk_yotei   = worksheet.cell(3, 59)
              @cpk_kanryou = worksheet.cell(3, 59)
            end
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
      @shisaku_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @shisaku_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
    end
  end

  def collect_mold_instructions(pro, stage)
    if stage == '金型製造指示書_営業'
      @kanagata_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @kanagata_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
    end
  end

  def collect_design_plan(pro, stage)
    if stage == '設計計画書_金型設計'
      @plan_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @plan_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('設計計画書')

          with_roo_workbook(doc, filename) do |workbook|
            worksheet         = workbook.sheet(0)
            @plan_designer    = worksheet.cell(4, 9)
            @plan_manager     = worksheet.cell(5, 9)
            @plan_customer    = worksheet.cell(6, 3)
            @plan_risk        = [worksheet.cell(41, 4), worksheet.cell(42, 4)].compact.map(&:to_s).join
            @plan_opportunity = [worksheet.cell(43, 4), worksheet.cell(44, 4)].compact.map(&:to_s).join

            if worksheet.cell(10, 4)
              @plan_yotei   = worksheet.cell(11, 4)
              @plan_kanryou = worksheet.cell(11, 6)
            end
          end
        end
      end
    end
  end

  def collect_dr_concept_minutes(pro, stage)
    if stage == 'DR構想検討会議議事録_生産技術'
      @dr_setsubi_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @dr_setsubi_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        setsubi_docs      = pro.documents.select { |doc| doc.filename.to_s.include?('DR構想検討会議議事録') }
        @dr_setsubi_count = setsubi_docs.size

        insert_rows_to_excel_template_dr_setsubi if @insert_rows_to_excel_template_dr_setsubi

        setsubi_docs.each_with_index do |doc, i|
          filename = doc.filename.to_s
          with_roo_workbook(doc, filename) do |workbook|
            worksheet = workbook.sheet(0)
            instance_variable_set("@dr_setsubi_name_#{i + 1}",           worksheet.cell(5, 11))
            instance_variable_set("@dr_setsubi_designer_#{i + 1}",       worksheet.cell(2, 17))
            instance_variable_set("@dr_setsubi_manager_#{i + 1}",        worksheet.cell(2, 16))
            instance_variable_set("@dr_setsubi_equipment_name_#{i + 1}", worksheet.cell(5, 11))
            instance_variable_set("@dr_setsubi_yotei_#{i + 1}",    convert_excel_date(worksheet.cell(5, 15)))
            instance_variable_set("@dr_setsubi_kanryou_#{i + 1}",  convert_excel_date(worksheet.cell(5, 15)))
            instance_variable_set("@dr_setsubi_shiteki_#{i + 1}",
                                  (11..25).map { |row| worksheet.cell(row, 1)&.to_s }.compact.reject(&:empty?).join("\n"))
          end
        end
        @dr_setsubi_check = '☑'
      else
        @dr_setsubi_check = '☐'
      end
    end
  end

  def collect_progress_management(pro, stage)
    if stage == '進捗管理票_生産技術'
      @dr_seigi_yotei        = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @dr_seigi_plan_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        progress_docs              = pro.documents.select { |doc| doc.filename.to_s.include?('進捗管理票') }
        @progress_management_count = progress_docs.size

        insert_rows_to_excel_template_progress_management if @insert_rows_to_excel_template_progress_management

        progress_docs.each_with_index do |doc, i|
          filename = doc.filename.to_s
          with_roo_workbook(doc, filename) do |workbook|
            worksheet = workbook.sheet(0)
            instance_variable_set("@progress_management_seigi_equipment_name_#{i + 1}", worksheet.cell(3, 4))
            instance_variable_set("@progress_management_seigi_design_name_#{i + 1}",    worksheet.cell(14, 8))
            instance_variable_set("@progress_management_seigi_design_yotei_#{i + 1}",   convert_excel_date(worksheet.cell(12, 6)))
            instance_variable_set("@progress_management_seigi_design_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(12, 7)))
            instance_variable_set("@progress_management_seigi_assembly_name_#{i + 1}",    worksheet.cell(27, 8))
            instance_variable_set("@progress_management_seigi_assembly_yotei_#{i + 1}",   convert_excel_date(worksheet.cell(26, 6)))
            instance_variable_set("@progress_management_seigi_assembly_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(26, 7)))
            instance_variable_set("@progress_management_seigi_wiring_name_#{i + 1}",    worksheet.cell(30, 8))
            instance_variable_set("@progress_management_seigi_wiring_yotei_#{i + 1}",   convert_excel_date(worksheet.cell(29, 6)))
            instance_variable_set("@progress_management_seigi_wiring_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(29, 7)))
            instance_variable_set("@progress_management_seigi_program_name_#{i + 1}",    worksheet.cell(34, 8))
            instance_variable_set("@progress_management_seigi_program_yotei_#{i + 1}",   convert_excel_date(worksheet.cell(33, 6)))
            instance_variable_set("@progress_management_seigi_program_kanryou_#{i + 1}", convert_excel_date(worksheet.cell(33, 7)))

            if worksheet.cell(10, 4)
              @dr_seigi_yotei   = worksheet.cell(33, 6)
              @dr_seigi_kanryou = worksheet.cell(33, 7)
            end
          end
        end
      end
    end
  end

  def collect_initial_flow_record(pro, stage)
    if stage == '初期流動検査記録'
      @shoki_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @shoki_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @shoki_check = '☑'
      @shoki_person_in_charge = '石栗'
    end
  end

  def collect_material_specs(pro, stage)
    if stage == '材料仕様書'
      @material_specification_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @material_specification_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      @material_specification_check = '☑'
    end
  end

  def collect_process_instructions(pro, stage)
    if stage == 'プロセス指示書'
      @wi_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @wi_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
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
      safe_merge_cells(worksheet, row_number, 7, row_number, 9)
      safe_merge_cells(worksheet, row_number, 10, row_number, 11)
      safe_merge_cells(worksheet, row_number, 12, row_number, 13)
      safe_merge_cells(worksheet, row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    safe_merge_cells(worksheet, insert_row_number - 1, 3, insert_row_number + count - 1, 6)
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
      safe_merge_cells(worksheet, row_number, 7, row_number, 9)
      safe_merge_cells(worksheet, row_number, 10, row_number, 11)
      safe_merge_cells(worksheet, row_number, 12, row_number, 13)
      safe_merge_cells(worksheet, row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    safe_merge_cells(worksheet, insert_row_number - 1, 3, insert_row_number + count - 1, 6)
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
      safe_merge_cells(worksheet, row_number, 7, row_number, 9)
      safe_merge_cells(worksheet, row_number, 10, row_number, 11)
      safe_merge_cells(worksheet, row_number, 12, row_number, 13)
      safe_merge_cells(worksheet, row_number, 14, row_number, 23)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    safe_merge_cells(worksheet, insert_row_number - 1, 3, insert_row_number + count - 1, 6)

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

      safe_merge_cells(worksheet, row_number, 3, row_number, 6)
      safe_merge_cells(worksheet, row_number + 1, 3, row_number + 3, 4)
      safe_merge_cells(worksheet, row_number + 1, 5, row_number + 1, 6)
      safe_merge_cells(worksheet, row_number + 2, 5, row_number + 2, 6)
      safe_merge_cells(worksheet, row_number + 3, 5, row_number + 3, 6)
      safe_merge_cells(worksheet, row_number, 14, row_number + 3, 23)

      # 行ごとの結合 (7-9, 10-11, 12-13)
      (0..3).each do |offset|
        safe_merge_cells(worksheet, row_number + offset, 7, row_number + offset, 9)
        safe_merge_cells(worksheet, row_number + offset, 10, row_number + offset, 11)
        safe_merge_cells(worksheet, row_number + offset, 12, row_number + offset, 13)
      end
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

  def safe_merge_cells(worksheet, r1, c1, r2, c2)
    return if r1 == r2 && c1 == c2

    worksheet.merged_cells&.delete_if do |m|
      ref = RubyXL::Reference.new(m.ref)
      row_overlap = ([ref.row_range.first, r1].max <= [ref.row_range.last, r2].min)
      col_overlap = ([ref.col_range.first, c1].max <= [ref.col_range.last, c2].min)
      row_overlap && col_overlap
    end

    worksheet.merge_cells(r1, c1, r2, c2)
  end
end
