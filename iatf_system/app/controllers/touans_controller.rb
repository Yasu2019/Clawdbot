# frozen_string_literal: true

class TouansController < ApplicationController
  OWNER_MAPPING = {
    'sales'            => %w[sales 営業プロセス],
    'process_design'   => %w[process_design 製造工程設計プロセス],
    'production'       => %w[production 製造プロセス],
    'inspection'       => %w[inspection 製品検査プロセス],
    'release'          => %w[release 引渡しプロセス],
    'procurement'      => %w[procurement 購買プロセス],
    'equipment'        => %w[equipment 設備管理プロセス],
    'measurement'      => %w[measurement 測定機器管理プロセス],
    'policy'           => %w[policy 方針プロセス],
    'satisfaction'     => %w[satisfaction 顧客満足プロセス],
    'audit'            => %w[audit 内部監査プロセス],
    'corrective_action' => %w[corrective_action 改善プロセス]
  }.freeze

  def export_to_excel
    @csrs = Csr.all
    @iatflists = Iatflist.all
    @mitsuis = Mitsui.all

    p = Axlsx::Package.new
    wb = p.workbook

    wb.add_worksheet(name: 'Basic Worksheet') do |sheet|
      sheet.add_row ['箇条', 'MEK様品質ガイドラインVer2', 'IATF規格要求事項', 'ミツイ精密 品質マニュアル']

      sheet.column_widths 15, 40, 40, 40

      rows = []
      [@csrs, @iatflists, @mitsuis].each do |records|
        records.each do |record|
          number = if record.respond_to?(:csr_number)
                     record.csr_number
                   else
                     record.respond_to?(:iatf_number) ? record.iatf_number : record.mitsui_number
                   end
          corresponding_csr = @csrs.find { |csr| csr.csr_number == number }
          corresponding_iatflist = @iatflists.find { |i| i.iatf_number == number }
          corresponding_mitsui = @mitsuis.find { |m| m.mitsui_number == number }

          next unless corresponding_csr || corresponding_iatflist || corresponding_mitsui

          rows << [
            number,
            corresponding_csr ? corresponding_csr.csr_content : '',
            corresponding_iatflist ? corresponding_iatflist.iatf_content : '',
            corresponding_mitsui ? corresponding_mitsui.mitsui_content : ''
          ]
        end
      end

      unique_rows = rows.sort_by { |row| row[0].split('.').map(&:to_i) }.uniq

      unique_rows.each do |row|
        sheet.add_row row
      end
    end

    send_data p.to_stream.read, filename: 'export.xlsx', type: 'application/xlsx'
  end

  def member_current_status
    @touans = Touan.all
    @user = current_user
    @users = User.all
  end

  def xlsx
    @touans = Touan.all
    respond_to do |format|
      format.html
      format.xlsx do
        generate_xlsx
      end
    end
  end

  def import_test
    result = Testmondai.import_test(params[:file])
    flash[:notice] = "問題CSVを処理しました: #{result.summary}"
    flash[:alert] = result.errors.first(5).join(' | ') if result.error_count.positive?
    redirect_to testmondai_touan_path
  end

  def import_kaitou
    result = Touan.import_kaitou(params[:file])
    flash[:notice] = "解答CSVを処理しました: #{result.summary}"
    flash[:alert] = result.errors.first(5).join(' | ') if result.error_count.positive?
    redirect_to touans_path
  end

  def delete_testmondai
    @testmondai = Testmondai.find(params[:testmondai_id])
    @testmondai.destroy
    respond_to do |format|
      format.html { redirect_to testmondai_touan_path, notice: 'Testmondai was successfully destroyed.' }
      format.json { head :no_content }
    end
  end

  def testmondai
    @user = current_user
    @testmondais = Testmondai.all
  end

  def delete_related
    target_date = DateTime.parse(params[:target_date])
    Touan.where(user_id: current_user.id, created_at: (target_date - 1.minute)..(target_date + 1.minute)).destroy_all

    flash[:notice] = '関連するTouanレコードを削除しました。'
    redirect_to touans_url
  end

  def index
    @user = current_user
    if params[:owner_select].present?
      session[:owner_select] = params[:owner_select]
      @owner_select = params[:owner_select]
    else
      @owner_select = session[:owner_select]
    end

    @products = Rails.cache.fetch("products_#{current_user.id}") do
      Product.where.not(documentnumber: nil).includes(:documents_attachments)
    end

    @touans = Touan.where(user_id: current_user.id)

    @auditor = current_user.auditor
    @csrs = Csr.all
    @iatflists = Iatflist.all

    @iatf_data, @iatf_data_sub = iatf_data_for(@user.owner)
    @process_name = OWNER_MAPPING.dig(@user.owner, 1)

    @iatf_data_audit, @iatf_data_audit_sub = iatf_data_for(@owner_select)
    @owner_select_jp = OWNER_MAPPING.dig(@owner_select, 1)
  end

  def new
    @touan = Touan.new
    @owner_select = session[:owner_select]

    @user = current_user
    @testmondais = Testmondai.where(kajyou: params[:kajyou])

    selected_testmondais = QuizQuestionSelectionService.call(
      user: @user,
      kajyou: params[:kajyou]
    )

    @touans = TouanCollection.new([], selected_testmondais, @user)
  end

  def create
    @user = current_user
    @touans = TouanCollection.new(touans_params, [], @user)
    if @touans.save
      grouped_touans = @touans.collection.group_by { |touan| [touan.user_id, touan.created_at.change(usec: 0)] }

      grouped_touans.each_value do |touans|
        QuizAttemptScoringService.score!(touans)
      end

      redirect_to touans_url
    else
      render :new
    end
  end

  def destroy
    @touan = Touan.find(params[:id])
    @touan.destroy
    respond_to do |format|
      format.html { redirect_to touans_url, notice: 'Touan was successfully destroyed.' }
      format.json { head :no_content }
    end
  end

  def iatf_csr_mitsui
    @products = Product.where.not(documentnumber: nil).includes(:documents_attachments)
    @csrs = Csr.all
    @iatflists = Iatflist.all
    @mitsuis = Mitsui.all
  end

  def kekka
    @touans = Touan.where(created_at: Time.zone.parse(params[:created_at]) - 1.minute..Time.zone.parse(params[:created_at]) + 1.minute)
    @user = current_user

    @touans.each do |touan|
      total_answers = Touan.where(kajyou: touan.kajyou,
                                  user_id: current_user.id).where(mondai_no: touan.mondai_no).count
      correct_answers = Touan.correct_answers_for(
        user_id: current_user.id,
        kajyou: touan.kajyou,
        mondai_no: touan.mondai_no,
        up_to_id: touan.id
      )

      touan.seikairitsu = correct_answers.to_f / total_answers * 100
      touan.total_answers = total_answers
      touan.correct_answers = correct_answers
    end
  end

  private

  def iatf_data_for(owner_key)
    key = OWNER_MAPPING.dig(owner_key, 0)
    return [[], []] if key.nil?

    [Iatf.where("#{key}": '2'), Iatf.where("#{key}": '1')]
  end

  def touans_params
    params.require(:touans).map do |p|
      p.permit(:kajyou, :kaito, :mondai, :mondai_a, :mondai_b, :mondai_c, :user_id, :seikai, :kaisetsu, :mondai_no, :seikairitsu,
               :total_answers, :correct_answers, :rev, :created_at, :updated_at)
    end
  end

  def generate_xlsx
    Axlsx::Package.new(encoding: 'UTF-8') do |p|
      p.workbook.add_worksheet(name: '登録答案一覧') do |sheet|
        styles = p.workbook.styles
        title = styles.add_style(bg_color: 'c0c0c0', b: true)
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

      send_data(p.to_stream.read,
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename: "登録答案一覧(#{Time.current.strftime('%Y_%m_%d_%H_%M_%S')}).xlsx")
    end
  end
end
