# frozen_string_literal: true

# APQP計画書Excelテンプレートに必要なデータを収集するサービス。
# ProductsController#apqp_plan_report から呼び出される。
class ApqpPlanCreateDataService
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
    @apqp_plan_excel_template_initial = true
    @apqp_plan_insert_rows_to_excel_template = true
    @apqp_plan_insert_rows_to_excel_template_dr_setsubi = true
    @apqp_plan_insert_rows_to_excel_template_progress_management = true
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
      Rails.logger.info "stage= #{stage}"

      collect_inspection_fixtures(pro, stage)

      collect_control_plan(pro, stage)

      collect_msa(pro, stage)

      collect_qualified_lab_docs(pro, stage)



      collect_validation_record(pro, stage)

      collect_manufacturing_feasibility(pro, stage)






      #if stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'
      #  @processflow_yotei = pro.deadline_at.strftime('%y/%m/%d')
      #  @processflow_kanryou = pro.end_at.strftime('%y/%m/%d')
      #  if pro.documents.attached?
      #    @processflow_check = '☑'
      #    @processflow_filename = pro.documents.first.filename.to_s
      #  else
      #    #@processflow_check = '☐'
      #  end
      #end

      


      collect_process_flow(pro, stage)

      














      collect_msa_crosstab(pro, stage)

      collect_psw_first(pro, stage)

      collect_dimensional_measurement(pro, stage)

      collect_pfmea(pro, stage)

      collect_characteristics_matrix(pro, stage)

      collect_process_flow_diagram(pro, stage)


      collect_floor_plan_layout(pro, stage)

      collect_psw_second(pro, stage)

      collect_dr_meeting_minutes(pro, stage)

      collect_initial_process_survey(pro, stage)

      collect_prototype_instructions(pro, stage)

      collect_mold_instructions(pro, stage)

      collect_design_plan(pro, stage)

      collect_customer_requirements(pro, stage)

      collect_dr_setsubi(pro, stage)
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
    @special_check = '☐'
    @pf_check = '☐'
    @process_layout_check = '☐'
    @crosstab_check = '☐'
    @inspection_fixtures_mold_check = '☐'
    @inspection_fixtures_stamping_check = '☐'
  end

  def result_variables
    skip = %i[@products @all_products @dropdownlist]
    instance_variables.each_with_object({}) do |ivar, hash|
      next if skip.include?(ivar)
      hash[ivar.to_s.delete('@')] = instance_variable_get(ivar)
    end
  end

  def collect_inspection_fixtures(pro, stage)
    if stage == '検査補助具'
      if pro.documents.attached?
        filename = pro.documents.first.filename.to_s
        if filename.include?("成形")
        @inspection_fixtures_mold_filename = filename
        @inspection_fixtures_mold_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @inspection_fixtures_mold_kanryou = pro.end_at.strftime('%y/%m/%d')  
        @inspection_fixtures_mold_check = '☑'
        else
        @inspection_fixtures_stamping_filename = filename
        @inspection_fixtures_stamping_yotei = pro.deadline_at.strftime('%y/%m/%d')
        @inspection_fixtures_stamping_kanryou = pro.end_at.strftime('%y/%m/%d')  
        @inspection_fixtures_stamping_check = '☑'
        end
      else
        @inspection_fixtures_mold_check = '☐'
        @inspection_fixtures_stamping_check = '☐'
      end
    end
  end

  def collect_control_plan(pro, stage)
    if stage == '量産コントロールプラン' || stage == '試作コントロールプラン' || stage == "先行生産（Pre-launch,量産試作）コントロールプラン"
      @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @cp_check = '☑'
        @cp_filename = pro.documents.first.filename.to_s
      else
        #@cp_check = '☐'
      end
    end
  end

  def collect_msa(pro, stage)
    if stage == '測定システム解析（MSA)' # GRR
      @grr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @grr_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @grr_check = '☑'
        @grr_filename = pro.documents.first.filename.to_s
      else
        @grr_check = '☐'
      end
    end
  end

  def collect_qualified_lab_docs(pro, stage)
    if stage == '有資格試験所文書'
      @documented_information_of_qualified_laboratories_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @documented_information_of_qualified_laboratories_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @documented_information_of_qualified_laboratories_check = '☑'
        @documented_information_of_qualified_laboratories_filename = pro.documents.first.filename.to_s
      else
        @documented_information_of_qualified_laboratories_check = '☐'
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
        if files.empty?
          Rails.logger.info "該当するファイルが見つかりませんでした。"
        end

        files.each do |file|
          workbook = nil
          case File.extname(file)
          when '.xlsx'
            workbook = Roo::Excelx.new(file)
          when '.xls'
            workbook = Roo::Excel.new(file)
          else
            return # 次のファイルへ
          end

          begin
            # 最初のシートを取得
            worksheet = workbook.sheet(0)

            # セルの値を取得
            @datou_result = worksheet.cell(36, 24).presence || worksheet.cell(41, 13)
            @datou_person_in_charge = worksheet.cell(39, 22)
            @datou_kanryou = worksheet.cell(37, 6).presence || worksheet.cell(43, 4)
            @datou_filename = pro.documents.first.filename.to_s
            Rails.logger.info '妥当性確認'
            Rails.logger.info "@partnumber= #{@partnumber}"
            Rails.logger.info "@datou_result #{@datou_result}"
          rescue => e
            Rails.logger.error "ファイル処理中にエラーが発生しました: #{e.message}"
          end
        end
      else
        @datou_check = '☐'
        Rails.logger.info "添付ファイルがありません。"
      end
    end
  end

  def collect_manufacturing_feasibility(pro, stage)
    if stage == '製造実現可能性検討書'
      @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @feasibility_check = '☑'
        @feasibility_filename = pro.documents.first.filename.to_s
      else
        #@feasibility_check = '☐'
      end
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
                            return
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
                  return
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
                @processflow_filename_stamping = pro.documents.first.filename.to_s

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
                              return
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
                    return
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
                  @processflow_filename_mold = pro.documents.first.filename.to_s

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
            return unless filename.include?('プロセスフロー')

            begin
              temp_file = Tempfile.new(['temp', File.extname(filename)])
              temp_file.binmode
              temp_file.write(doc.download)
              temp_file.rewind

              workbook = case File.extname(filename).downcase
                        when '.xlsx' then Roo::Excelx.new(temp_file.path)
                        when '.xls'  then Roo::Excel.new(temp_file.path)
                        else
                          return
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
                return
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
                @processflow_filename_sales = pro.documents.first.filename.to_s
                Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
              elsif filename.include?('工程設計')
                @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_design_dept = workbook.cell(4, 13).to_s.strip
                @processflow_design_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_design_kanryou = pro.end_at.strftime('%y/%m/%d')
                @processflow_design_check='☑'
                @processflow_filename_design = pro.documents.first.filename.to_s
                Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
              elsif filename.include?('検査')
                @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
                @processflow_inspection_dept = workbook.cell(4, 13).to_s.strip
                @processflow_inspection_yotei = pro.deadline_at.strftime('%y/%m/%d')
                @processflow_inspection_kanryou = pro.end_at.strftime('%y/%m/%d')
                @processflow_inspection_check='☑'
                @processflow_filename_inspection = pro.documents.first.filename.to_s
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

  def collect_msa_crosstab(pro, stage)
    if stage == '測定システム解析（MSA)' # クロスタブ
      @crosstab_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @crosstab_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @crosstab_check = '☑'
        @crosstab_filename = pro.documents.first.filename.to_s
      else
        #@crosstab_check = '☐'
      end
    end
  end

  def collect_psw_first(pro, stage)
    if stage == '部品提出保証書（PSW)'
      @psw_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @psw_kanryou = pro.end_at.strftime('%y/%m/%d')
      Rails.logger.info "@psw_yotei #{@psw_yotei}" # 追加
      if pro.documents.attached?
        @psw_check = '☑'

        # 変数の設定
        partnumber = pro.partnumber
        # 部品提出保証書の前にpartnumberがあるケース
        pattern1 = "/myapp/db/documents/*#{partnumber}部品提出保証書*"
        # 部品提出保証書の後にpartnumberがあるケース
        pattern2 = "/myapp/db/documents/*部品提出保証書*#{partnumber}*"

        # ログにパターンを出力
        Rails.logger.info "Pattern1= #{pattern1}"
        Rails.logger.info "Pattern2= #{pattern2}"

        # 両方のパターンにマッチするファイルを検索
        files = Dir.glob(pattern1) + Dir.glob(pattern2)
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
          (25..30).each do |row|
            if worksheet.cell(row, 2)&.to_s == '■'
              @psw_level = worksheet.cell(row, 3)&.to_s
              break # 一度見つかったらループを終了
            end
          end
        end # files.each do |file| の終了
      end # if pro.documents.attached? の終了
    end # if stage == '部品提出保証書（PSW)' の終了
  end

  def collect_dimensional_measurement(pro, stage)
    if stage == '寸法測定結果' # 型検
      @kataken_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @kataken_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @kataken_check = '☑'
        @kataken_filename = pro.documents.first.filename.to_s
      else
       #@kataken_check = '☐'
      end
    end
  end

  def collect_pfmea(pro, stage)
    if stage == 'プロセス故障モード影響解析（PFMEA）' ||   stage == 'プロセスFMEA'
      @pfmea_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @pfmea_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @pfmea_check = '☑'
        @pfmea_filename = pro.documents.first.filename.to_s
      else
        #@pfmea_check = '☐'
      end
    end
  end

  def collect_characteristics_matrix(pro, stage)
    if stage == '特性マトリクス'
      @special_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @special_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @special_check = '☑'
        @special_filename = pro.documents.first.filename.to_s
      else
        #special_check = '☐'
      end
    end
  end

  def collect_process_flow_diagram(pro, stage)
    if stage == '工程フロー図'
      @pf_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @pf_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @pf_check = '☑'
        @pf_filename = pro.documents.first.filename.to_s
      else
        @pf_check = '☐'
      end
    end
  end

  def collect_floor_plan_layout(pro, stage)
    if stage == 'フロアプランレイアウト'
      @floor_plan_layout_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @floor_plan_layout_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @floor_plan_layout_check = '☑'
        @floor_plan_layout_filename = pro.documents.first.filename.to_s
      else
        #@floor_plan_layout_check = '☐'
      end
    end
  end

  def collect_psw_second(pro, stage)
    if stage == '部品提出保証書（PSW)'
      @psw_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @psw_kanryou = pro.end_at.strftime('%y/%m/%d')
      Rails.logger.info "@psw_yotei #{@psw_yotei}" # 追加
      if pro.documents.attached?
        @psw_check = '☑'

      # 変数の設定
      partnumber = pro.partnumber
      # 部品提出保証書の前にpartnumberがあるケース
      pattern1 = "/myapp/db/documents/*#{partnumber}*部品提出保証書*"
      # 部品提出保証書の後にpartnumberがあるケース
      pattern2 = "/myapp/db/documents/*部品提出保証書*#{partnumber}*"

      # ログにパターンを出力
      Rails.logger.info "Pattern1= #{pattern1}"
      Rails.logger.info "Pattern2= #{pattern2}"

      # 両方のパターンにマッチするファイルを検索
      files = Dir.glob(pattern1) + Dir.glob(pattern2)
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
          # 指定の範囲で各行をチェック
          (25..30).each do |row|
            if worksheet.cell(row, 2)&.to_s == '■'
              @psw_level = worksheet.cell(row, 3)&.to_s
              break # 一度見つかったらループを終了
            end
          end

          @psw_filename = pro.documents.first.filename.to_s
        end
      else
        #@psw_check = '☐'
      end
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
        @dr_check_filename = pro.documents.first.filename.to_s
      else
        #@dr_check = '☐'
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
        @cpk_check_filename = pro.documents.first.filename.to_s
      else
        #@cpk_check = '☐'
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
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*#{partnumber}*設計計画書*"
        Rails.logger.info "Path= #{pattern}"
        files = Dir.glob(pattern)
        files.each do |file|
          # Excelファイルを開く
          if File.extname(file) == '.xlsx'
            workbook = Roo::Excelx.new(file) # xlsxの場合はこちらを使用
          elsif File.extname(file) == '.xls'
            workbook = Roo::Excel.new(file) # xlsの場合はこちらを使用
          else
            return # 不明なファイル形式の場合は次のファイルへ
          end

          # 最初のシートを取得
          worksheet = workbook.sheet(0)

          return unless worksheet.cell(10, 4)

          year_cell = worksheet.cell(3, 9)

          @plan_customer = worksheet.cell(6, 8)

          @plan_yotei = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
          @plan_kanryou = format_date_from_cells(year_cell,  worksheet.cell(11, 4).to_s)
          @actual_yotei = format_date_from_cells(year_cell,  worksheet.cell(11, 4).to_s)
          @actual_kanryou = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)

          @plan_design_start = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
          @plan_design_end = format_date_from_cells(year_cell, worksheet.cell(11, 4).to_s)
          @actual_design_start = format_date_from_cells(year_cell, worksheet.cell(10, 6).to_s)
          @actual_design_end = format_date_from_cells(year_cell, worksheet.cell(11, 6).to_s)

          @plan_datou_start = format_date_from_cells(year_cell, worksheet.cell(17, 4).to_s)
          @plan_datou_end = format_date_from_cells(year_cell, worksheet.cell(17, 4).to_s)
          @actual_datou_start = format_date_from_cells(year_cell, worksheet.cell(17, 6).to_s)
          @actual_datou_end = format_date_from_cells(year_cell, worksheet.cell(17, 6).to_s)
        end
      end
    end
  end

  def collect_customer_requirements(pro, stage)
    if stage == '顧客要求事項検討会議事録_営業'
      @scr_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @scr_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @scr_check = '☑'

        # 変数の設定
        partnumber = pro.partnumber
        pattern = "/myapp/db/documents/*顧客要求検討会議事録*#{partnumber}*"
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
          @plan_scr_start = worksheet.cell(5, 6)
          @plan_scr_end = worksheet.cell(5, 6)
          @actual_scr_start = worksheet.cell(5, 6)
          @actual_scr_end = worksheet.cell(5, 6)
        end
      else
        #@scr_check = '☐'
      end
    end
  end

  def collect_dr_setsubi(pro, stage)
    return unless stage == 'DR構想検討会議議事録_生産技術'

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

      if @apqp_plan_insert_rows_to_excel_template_dr_setsubi == true # 初回のファイルのみ挿入サブルーチンに飛ぶ
        apqp_plan_insert_rows_to_excel_template_dr_setsubi # セルに必要な行数だけ行を挿入するサブルーチン
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
        workbook.sheet(0)

        # i4のセルの値を取得

        # ファイル名の取得
        filename = File.basename(file)

        # インスタンス変数にファイル名を設定
        instance_variable_set("@dr_setsubi_filename_#{i + 1}", filename)

        # もちろん、空欄の場合に改行が登録されないようにコードを変更することができます。
        # 具体的には、セルの内容が空の文字列である場合、それを配列に含めないようにする必要があります。これを実現するために、配列の生成の際に compact メソッドと reject メソッドを使用して空の文字列を取り除きます。
        # 以下のように変更します：
        # instance_variable_set("@dr_setsubi_shiteki_#{i + 1}",
        # (11..25).map { |row| worksheet.cell(row, 1)&.to_s }
        # .compact
        # .reject(&:empty?)
        # .join("\n"))

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


  def apqp_plan_insert_rows_to_excel_template_dr_setsubi
    if @apqp_plan_excel_template_initial == true # Excelテンプレートが初期値の場合
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_plan_report.xlsx')
      @apqp_plan_excel_template_initial = false
    else
      workbook = RubyXL::Parser.parse('lib/excel_templates/apqp_plan_report_modified.xlsx')
    end
    @apqp_plan_insert_rows_to_excel_template_dr_setsubi = false # 初回のファイルのみサブルーチン処理したのでfalseにして次のファイルから飛ばないようにする

    worksheet = workbook[0]

    count = @dr_setsubi_count - 1

    count = 0 if count.negative?

    insert_row_number = 0 # 挿入する行番号を格納する変数
    (20..30).each do |row|
      next unless worksheet[row][5].value == 'デザインレビュー(設備設計)' # D列を参照。

      insert_row_number = row + 1 # 挿入する行番号を取得

      break
    end

    Rails.logger.info "insert_row_number= #{insert_row_number}" # 追加
    Rails.logger.info "count= #{count}" # 追加

    count.times do |i|
      row_number = insert_row_number + i # 正しい行番号を計算
      worksheet.insert_row(row_number)
      Rails.logger.info "row_number= #{row_number}" # 追加
    
      # 新しく追加された行に、生技（#{?dr_setsubi_designer_#{i+2}}）を設定
      worksheet[row_number][12].change_contents("報告書名：\#{?dr_setsubi_filename_#{i + 2}}")
    
      # 横方向の結合のみループ内で実行
      worksheet.merge_cells(row_number, 12, row_number, 19)
    end
    
    # ループ終了後に縦方向の結合を実行
    if count > 0
      # 開始行は最初に挿入した行、終了行は最後に挿入した行
      start_row = insert_row_number
      end_row = insert_row_number + count - 1
      
      # 5列目から11列目の結合
      worksheet.merge_cells(start_row-1, 5, end_row, 11)
      # 4列目の結合
      worksheet.merge_cells(start_row-1, 4, end_row, 4)
    end

    # worksheet.merge_cells メソッドは、セルの範囲を結合するために使用されます。
    # 指定されたコマンド worksheet.merge_cells(40, 3, 41, 6) において、引数は以下のように解釈されます：
    # 最初の2つの数字 (40, 3) は、結合を開始するセルを指定します。この場合、41行目のD列（インデックス3はD列を示す）のセル、すなわちセルD41を示します。
    # 次の2つの数字 (41, 6) は、結合を終了するセルを指定します。この場合、42行目のG列（インデックス6はG列を示す）のセル、すなわちセルG42を示します。
    # したがって、このコマンドにより、セルD41からG42までの範囲（D41, E41, F41, G41, D42, E42, F42, G42の8つのセル）が結合されます。

    # worksheet.merge_cells(insert_row_number-1, 3, insert_row_number+count-1, 6)

    workbook.write('lib/excel_templates/apqp_plan_report_modified.xlsx')
  end

  #   end

  #  end


  def cell_address_to_position(cell_address)
    col = cell_address.gsub(/\d/, '')
    row = cell_address.gsub(/\D/, '').to_i
    col_index = col.chars.map { |char| char.ord - 'A'.ord + 1 }.reduce(0) { |acc, val| (acc * 26) + val }
    [row, col_index]
  end

  def format_date_from_cells(year_cell, month_day_cell)
    year = if year_cell.is_a?(Date)
             year_cell.strftime('%Y')
           else
             year_cell.slice(0, 4)
           end
    "\#{year}/\#{month_day_cell}"
  end

end
