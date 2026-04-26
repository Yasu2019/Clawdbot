# frozen_string_literal: true

# APQP総括・承認書Excelテンプレートに必要なデータを収集するサービス。
# ProductsController#apqp_approved_report から呼び出される。
class ApqpApprovedCreateDataService
  include ProcessFlowCollectable
  def self.call(products:, all_products:, dropdownlist:, partnumber:)
    new(products:, all_products:, dropdownlist:, partnumber:).call
  end

  def initialize(products:, all_products:, dropdownlist:, partnumber:)
    @products     = products
    @all_products = all_products
    @dropdownlist = dropdownlist
    @partnumber   = partnumber
  end

  def call
    @datetime = Time.zone.now
    @apqp_approved_report_excel_template_initial = true
    @apqp_approved_report_insert_rows_to_excel_template = true
    @apqp_approved_report_insert_rows_to_excel_template_msa = true
    @apqp_approved_report_insert_rows_to_excel_template_dr_setsubi = true
    @apqp_approved_report_insert_rows_to_excel_template_progress_management = true
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
    initialize_checkboxes

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= \#{@partnumber}"
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= \#{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= \#{pro.stage}"

      collect_press_work_standard(pro, stage)
      collect_process_flow(pro, stage)
      collect_initial_process_survey(pro, stage)
      collect_msa_grr(pro, stage)
      collect_msa_crosstab(pro, stage)
      collect_control_plan(pro, stage)
      collect_design_plan(pro, stage)
    end

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
    @psw_check = '☐'
    @pf_sales_check = '☐'
    @pf_production_check = '☐'
    @pf_inspectoin_check = '☐'
    @pf_release_check = '☐'
    @pf_process_design_check = '☐'
    @pf_check = '☐'
    @process_layout_check = '☐'
    @processflow_inspection_ckeck = '☐'
    @processflow_mold_ckeck = '☐'
    @inspection_fixtures_mold_check = '☐'
    @inspection_fixtures_stamping_check = '☐'
    @processflow_design_check = '☐'
    @processflow_stamping_check = '☐'
    @processflow_inspection_check = '☐'
    @processflow_mold_check = '☐'
    @processflow_sales_check = '☐'
  end

  def result_variables
    skip = %i[@products @all_products @dropdownlist]
    instance_variables.each_with_object({}) do |ivar, hash|
      next if skip.include?(ivar)
      hash[ivar.to_s.delete('@')] = instance_variable_get(ivar)
    end
  end

  def collect_press_work_standard(pro, stage)
    if %w[プレス作業標準書].include?(stage)
      @stamping_standard_procedure_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @stamping_standard_procedure_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        @stamping_standard_procedure_check = '☑'
        @stamping_standard_procedure_filename = pro.documents.first.filename.to_s
      else
        @stamping_standard_procedure_check = '☐'
      end
    end
  end

  def collect_initial_process_survey(pro, stage)
    if stage == '初期工程調査結果'
      @cpk_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
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
                row, col = cell_address_to_position(cell_address)
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

  def collect_msa_grr(pro, stage)
    if stage == '測定システム解析（MSA)' # GRR
      @grr_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @grr_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''

      if pro.documents.attached?
        grr_docs   = pro.documents.select { |doc| doc.filename.to_s.include?('ゲージR&R') }
        @grr_count = grr_docs.size

        apqp_approved_report_insert_rows_to_excel_template_msa if @apqp_approved_report_insert_rows_to_excel_template_msa

        @grr = 0
        @ndc = 0

        grr_docs.each_with_index do |doc, i|
          filename = doc.filename.to_s
          with_roo_workbook(doc, filename) do |workbook|
            worksheet = workbook.sheet(0)
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

        apqp_approved_report_insert_rows_to_excel_template if @apqp_approved_report_insert_rows_to_excel_template

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
            instance_variable_set("@msa_crosstab_kanryou_#{i + 1}",          worksheet.cell(4, 24))
            instance_variable_set("@msa_crosstab_recorder_#{i + 1}",          worksheet.cell(6, 24))
            instance_variable_set("@msa_crosstab_person_in_charge_#{i + 1}",  worksheet.cell(120, 29))
            instance_variable_set("@msa_crosstab_approved_#{i + 1}",          worksheet.cell(120, 27))
            instance_variable_set("@inspector_name_a_#{i + 1}",               worksheet.cell(8, 10))
            instance_variable_set("@inspector_name_b_#{i + 1}",               worksheet.cell(8, 16))
            instance_variable_set("@inspector_name_c_#{i + 1}",               worksheet.cell(8, 22))
            instance_variable_set("@inspector_a_result_#{i + 1}",             worksheet.cell(131, 7))
            instance_variable_set("@inspector_b_result_#{i + 1}",             worksheet.cell(131, 11))
            instance_variable_set("@inspector_c_result_#{i + 1}",             worksheet.cell(131, 15))
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

  def collect_control_plan(pro, stage)
    if %w[量産コントロールプラン 試作コントロールプラン].include?(stage)
      @controlplan_yotei = pro.deadline_at&.strftime('%y/%m/%d') || ''
      @controlplan_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
      if pro.documents.attached?
        @cp_check = '☑'
        @cp_filename = pro.documents.first.filename.to_s
      else
        @cp_check = '☐'
      end
    end
  end

  def collect_design_plan(pro, stage)
    return unless stage == '設計計画書_金型設計'

    @plan_yotei   = pro.deadline_at&.strftime('%y/%m/%d') || ''
    @plan_kanryou = pro.end_at&.strftime('%y/%m/%d') || ''
    return unless pro.documents.attached?

    pro.documents.each do |doc|
      filename = doc.filename.to_s
      next unless filename.include?('設計計画書')

      with_roo_workbook(doc, filename) do |workbook|
        worksheet      = workbook.sheet(0)
        @plan_designer = worksheet.cell(4, 9)
        @plan_manager  = worksheet.cell(5, 9)
        @plan_customer = worksheet.cell(6, 3)
        @plan_risk     = [worksheet.cell(41, 4), worksheet.cell(42, 4)].compact.map(&:to_s).join
        @plan_opportunity = [worksheet.cell(43, 4), worksheet.cell(44, 4)].compact.map(&:to_s).join

        if worksheet.cell(10, 4)
          @plan_yotei   = worksheet.cell(11, 4)
          @plan_kanryou = worksheet.cell(11, 6)
        end
      end
    end
  end

  def apqp_approved_report_insert_rows_to_excel_template_msa
    if @apqp_approved_report_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report.xlsx')
      @apqp_approved_report_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report_modified.xlsx')
    end
    @apqp_approved_report_insert_rows_to_excel_template_msa = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @grr_count >= 2
              @grr_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (10..85).each do |row|
      if worksheet[row][1].value == 'GRR' # B列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      # worksheet[row_number][7].change_contents("品証（\#{?grr_person_in_charge_#{i + 2}}）")
      # worksheet[row_number][10].change_contents("\#{?grr_yotei_#{i + 2}}")
      # worksheet[row_number][12].change_contents("\#{?grr_kanryou_#{i + 2}}")
      worksheet[row_number][5].change_contents("項番：\#{?grr_no_#{i + 2}} \n GRR値：\#{?grr_#{i + 2}}%、GRR結果：\#{?grr_result_#{i + 2}} \n ndc値：\#{?ndc_#{i + 2}}、ndc結果：\#{?ndc_result#{i + 2}}")

      # H列、I列、J列を結合
      # worksheet.merge_cells(row_number, 7, row_number, 9)
      # worksheet.merge_cells(row_number, 10, row_number, 11)
      # worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 5, row_number, 20)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 1, insert_row_number + count - 1, 4)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/apqp_approved_report_modified.xlsx')
  end

  def apqp_approved_report_insert_rows_to_excel_template
    if @apqp_approved_report_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report.xlsx')
      @apqp_approved_report_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_approved_report_modified.xlsx')
    end
    @apqp_approved_report_insert_rows_to_excel_template = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする
    worksheet = workbook[0]

    count = if @msa_crosstab_count >= 2
              @msa_crosstab_count - 1
            else
              0
            end

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (10..85).each do |row|
      if worksheet[row][1].value == 'クロスタブ' # B列を参照。
        insert_row_number = row + 1 # 挿入する行番号を取得
        break
      end
    end

    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    # countの数だけ38行目と39行目の間に内容を挿入
    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)

      # 新しく追加された行に、品証（#{?msa_crosstab_person_in_charge_#{i+2}}）を設定
      # worksheet[row_number][7].change_contents("品証（\#{?msa_crosstab_person_in_charge_#{i + 2}}）")
      # worksheet[row_number][10].change_contents("\#{?msa_crosstab_yotei_#{i + 2}}")
      # worksheet[row_number][12].change_contents("\#{?msa_crosstab_kanryou_#{i + 2}}")
      worksheet[row_number][5].change_contents("\#{?inspector_name_a_#{i + 2}}：\#{?inspector_a_result_#{i + 2}}、\#{?inspector_name_b_#{i + 2}}：\#{?inspector_b_result_#{i + 2}}、\#{?inspector_name_c_#{i + 2}}：\#{?inspector_c_result_#{i + 2}}")

      # H列、I列、J列を結合
      # worksheet.merge_cells(row_number, 7, row_number, 9)
      # worksheet.merge_cells(row_number, 10, row_number, 11)
      # worksheet.merge_cells(row_number, 12, row_number, 13)
      worksheet.merge_cells(row_number, 5, row_number, 20)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    worksheet.merge_cells(insert_row_number - 1, 1, insert_row_number + count - 1, 4)
    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加

    Rails.logger.info "count= #{count}" # 追加

    workbook.write('lib/excel_templates/apqp_approved_report_modified.xlsx')
  end

  # RailsでAxlsxを使ってxlsxを生成
  # https://qiita.com/necojackarc/items/0dbd672b2888c30c5a38

  # 【Rails】 strftimeの使い方と扱えるクラスについて
  # https://pikawaka.com/rails/strftime

  def cell_address_to_position(cell_address)
    col = cell_address.gsub(/\d/, '')
    row = cell_address.gsub(/\D/, '').to_i
    col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
    [row, col_index]
  end

end
