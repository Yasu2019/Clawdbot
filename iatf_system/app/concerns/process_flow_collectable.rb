# frozen_string_literal: true

# プロセスフロー図ファイルからデータを収集する共通ロジック。
# ApqpPlanCreateDataService / ApqpApprovedCreateDataService / ProductCreateDataService で使用。
#
# 収集する変数:
#   @processflow_check               ☑/☐
#   @processflow_stamping_*          プレスファイル由来
#   @processflow_mold_*              成形ファイル由来
#   @processflow_sales_*             営業ファイル由来
#   @processflow_design_*            工程設計ファイル由来
#   @processflow_inspection_*        検査ファイル由来
#   @processflow_filename_*          各ファイル名（テンプレートが使わない場合は無視される）
module ProcessFlowCollectable
  private

  def collect_process_flow(pro, stage)
    return unless stage == 'プロセスフロー図' || stage == 'プロセスフロー図(Phase3)'

    if pro.documents.attached?
      @processflow_check = '☑'

      begin
        press_file_found = false

        # プレスファイルを探す
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('プロセスフロー') && filename.include?('プレス')

          press_file_found = true
          with_roo_workbook(doc, filename) do |workbook|
            sheet = find_target_sheet(workbook, row: 2, cols: [21, 22])
            next unless sheet

            workbook.default_sheet = sheet
            @processflow_stamping_person_in_charge = workbook.cell(2, 21).to_s.strip
            @processflow_stamping_dept             = workbook.cell(4, 13).to_s.strip
            @processflow_stamping_yotei            = pro.deadline_at&.strftime('%y/%m/%d') || ''
            @processflow_stamping_check            = '☑'
            @processflow_filename_stamping         = filename
            Rails.logger.info "プレス承認者: \#{?processflow_stamping_person_in_charge}"
          end
          break
        end

        # プレスファイルがない場合は成形ファイルを探す
        unless press_file_found
          pro.documents.each do |doc|
            filename = doc.filename.to_s
            next unless filename.include?('プロセスフロー') && filename.include?('成形')

            with_roo_workbook(doc, filename) do |workbook|
              sheet = find_target_sheet(workbook, row: 2, cols: [21, 22])
              next unless sheet

              workbook.default_sheet = sheet
              @processflow_mold_person_in_charge = workbook.cell(2, 21).to_s.strip
              @processflow_mold_dept             = workbook.cell(4, 13).to_s.strip
              @processflow_mold_yotei            = pro.deadline_at&.strftime('%y/%m/%d') || ''
              @processflow_mold_kanryou          = pro.end_at&.strftime('%y/%m/%d') || ''
              @processflow_mold_check            = '☑'
              @processflow_filename_mold         = filename
              Rails.logger.info "成形承認者: \#{?processflow_mold_person_in_charge}"
            end
            break
          end
        end

        # 営業・工程設計・検査ファイルは毎回確認
        pro.documents.each do |doc|
          filename = doc.filename.to_s
          next unless filename.include?('プロセスフロー')

          with_roo_workbook(doc, filename) do |workbook|
            sheet = find_target_sheet(workbook, row: 2, cols: [21, 22])
            next unless sheet

            workbook.default_sheet = sheet
            if filename.include?('営業')
              @processflow_sales_person_in_charge = workbook.cell(2, 21).to_s.strip
              @processflow_sales_dept             = workbook.cell(4, 13).to_s.strip
              @processflow_sales_yotei            = pro.deadline_at&.strftime('%y/%m/%d') || ''
              @processflow_sales_kanryou          = pro.end_at&.strftime('%y/%m/%d') || ''
              @processflow_sales_check            = '☑'
              @processflow_filename_sales         = filename
              Rails.logger.info "営業承認者: \#{?processflow_sales_person_in_charge}"
            elsif filename.include?('工程設計')
              @processflow_design_person_in_charge = workbook.cell(2, 21).to_s.strip
              @processflow_design_dept             = workbook.cell(4, 13).to_s.strip
              @processflow_design_yotei            = pro.deadline_at&.strftime('%y/%m/%d') || ''
              @processflow_design_kanryou          = pro.end_at&.strftime('%y/%m/%d') || ''
              @processflow_design_check            = '☑'
              @processflow_filename_design         = filename
              Rails.logger.info "工程設計承認者: \#{?processflow_design_person_in_charge}"
            elsif filename.include?('検査')
              @processflow_inspection_person_in_charge = workbook.cell(2, 21).to_s.strip
              @processflow_inspection_dept             = workbook.cell(4, 13).to_s.strip
              @processflow_inspection_yotei            = pro.deadline_at&.strftime('%y/%m/%d') || ''
              @processflow_inspection_kanryou          = pro.end_at&.strftime('%y/%m/%d') || ''
              @processflow_inspection_check            = '☑'
              @processflow_filename_inspection         = filename
              Rails.logger.info "検査引渡し承認者: \#{?processflow_inspection_person_in_charge}"
            end
          end
        end

      rescue StandardError => e
        Rails.logger.error "ファイル処理エラー: #{e.message}"
      end
    else
      @processflow_check = '☐'
    end
  end

  # Active Storage ドキュメントを Tempfile 経由で Roo workbook として開き、ブロックに渡す。
  # 不明な拡張子の場合はスキップ（next）する。Tempfile は確実にクローズ・削除される。
  def with_roo_workbook(doc, filename)
    temp_file = Tempfile.new(['temp', File.extname(filename)])
    workbook  = nil
    begin
      temp_file.binmode
      temp_file.write(doc.download)
      temp_file.rewind

      workbook = case File.extname(filename).downcase
                 when '.xlsx' then Roo::Excelx.new(temp_file.path)
                 when '.xls'  then Roo::Excel.new(temp_file.path)
                 else
                   Rails.logger.warn "未対応ファイル形式: #{filename}"
                   return
                 end

      yield workbook
    rescue StandardError => e
      Rails.logger.error "Workbook処理エラー (#{filename}): #{e.message}"
    ensure
      workbook&.close if defined?(workbook) && workbook
      temp_file.close
      temp_file.unlink
    end
  end

  # row 行の cols 列のいずれかに値があるシートを返す。見つからなければ nil。
  def find_target_sheet(workbook, row:, cols:)
    Rails.logger.info "利用可能なシート: #{workbook.sheets.inspect}"
    workbook.sheets.each do |sheet_name|
      workbook.default_sheet = sheet_name
      return sheet_name if cols.any? { |col| workbook.cell(row, col).present? }
    end
    Rails.logger.warn "必要なデータを含むシートが見つかりませんでした"
    nil
  end
end
