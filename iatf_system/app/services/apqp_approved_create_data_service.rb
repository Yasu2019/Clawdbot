# frozen_string_literal: true

# APQP総括・承認書Excelテンプレートに必要なデータを収集するサービス。
# ProductsController#apqp_approved_report から呼び出される。
class ApqpApprovedCreateDataService
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
    @partnumber = params[:partnumber]

    @apqp_approved_report_excel_template_initial = true # Excelテンプレートを初期値にする
    @apqp_approved_report_insert_rows_to_excel_template = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @apqp_approved_report_insert_rows_to_excel_template_msa = true # MSAクロスタブを初期値にする。これをしておかないと、ファイルの数だけ挿入サブルーチンに飛んでしまう。
    @apqp_approved_report_insert_rows_to_excel_template_dr_setsubi = true # 初回のファイルのみ挿入サブルーチンに飛ぶ
    @apqp_approved_report_insert_rows_to_excel_template_progress_management = true # 初回のファイルのみ挿入サブルーチンに飛ぶ

    @datetime = Time.zone.now
    @name = 'm-kubo'
    @multi_lines_text = "Remember kids,\nthe magic is with in you.\nI'm princess m-kubo."
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
    @processflow_design_check = '☐'
    


#    catch :found do
#      @all_products.each do |all|
#        stage = @dropdownlist[all.stage.to_i]
#        Rails.logger.info "Stage: #{stage}, all.stage: #{all.stage.to_i},Documents attached: #{all.documents.attached?}"

#        Rails.logger.info "Current stage: #{stage}"
#        case stage
#        when '営業プロセスフロー'
#          Rails.logger.info 'Inside the condition for 営業プロセスフロー'
#          @pf_sales_check = all.documents.attached? ? '☑' : '☐'
#          Rails.logger.info "@pf_sales_check: #{@pf_sales_check}"
#        when '製造工程設計プロセスフロー'
#          @pf_process_design_check = all.documents.attached? ? '☑' : '☐'

#        when '製造プロセスフロー'
#          @pf_production_check = all.documents.attached? ? '☑' : '☐'

#        when '製品検査プロセスフロー'
#          @pf_inspectoin_check = all.documents.attached? ? '☑' : '☐'

#        when '引渡しプロセスフロー'
#          @pf_release_check = all.documents.attached? ? '☑' : '☐'

#        end

#        if @pf_sales_check && @pf_process_design_check && @pf_production_check && @pf_inspectoin_check && @pf_release_check
#          Rails.logger.info 'All checks completed.'
#          # throw :found
#        end
#      end
#    end

    @products.each do |pro|
      @partnumber = pro.partnumber
      Rails.logger.info "@partnumber= #{@partnumber}" # 追加
      @materialcode = pro.materialcode
      Rails.logger.info "@pro.stage= #{@dropdownlist[pro.stage.to_i]}"
      stage = @dropdownlist[pro.stage.to_i]
      Rails.logger.info "pro.stage(number)= #{pro.stage}"




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

  def result_variables
    skip = %i[@products @all_products @dropdownlist]
    instance_variables.each_with_object({}) do |ivar, hash|
      next if skip.include?(ivar)
      hash[ivar.to_s.delete('@')] = instance_variable_get(ivar)
    end
  end

  def collect_press_work_standard(pro, stage)
    if %w[プレス作業標準書].include?(stage)
      @stamping_standard_procedure_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @stamping_standard_procedure_kanryou = pro.end_at.strftime('%y/%m/%d')
      if pro.documents.attached?
        @stamping_standard_procedure_check = '☑'
        @stamping_standard_procedure_filename = pro.documents.first.filename.to_s
      else
        @stamping_standard_procedure_check = '☐'
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

        if @apqp_approved_report_insert_rows_to_excel_template_msa == true # 初回のファイルのみサブルーチン処理
          apqp_approved_report_insert_rows_to_excel_template_msa # ファイルの数だけ行を挿入するサブルーチン処理
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

        if @apqp_approved_report_insert_rows_to_excel_template == true # 初回のファイルのみサブルーチン処理
          apqp_approved_report_insert_rows_to_excel_template # ファイルの数だけ行を挿入するサブルーチン処理
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

  def collect_control_plan(pro, stage)
    if %w[量産コントロールプラン 試作コントロールプラン].include?(stage)
      @controlplan_yotei = pro.deadline_at.strftime('%y/%m/%d')
      @controlplan_kanryou = pro.end_at.strftime('%y/%m/%d')
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

    @plan_yotei = pro.deadline_at.strftime('%y/%m/%d')
    @plan_kanryou = pro.end_at.strftime('%y/%m/%d')
    return unless pro.documents.attached?

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
