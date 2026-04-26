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
    send_data(
      ExportCsrIatfToExcelService.call(csrs: Csr.all, iatflists: Iatflist.all, mitsuis: Mitsui.all),
      filename: 'export.xlsx',
      type: 'application/xlsx'
    )
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
        send_data(
          GenerateTouanXlsxService.call(touans: @touans),
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          filename: "登録答案一覧(#{Time.current.strftime('%Y_%m_%d_%H_%M_%S')}).xlsx"
        )
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
    if params[:kajyou].blank?
      flash[:alert] = '箇条を選択してからテストを開始してください。'
      redirect_to index_touan_path and return
    end

    @touan = Touan.new
    @owner_select = session[:owner_select]

    @user = current_user
    @testmondais = Testmondai.where(kajyou: params[:kajyou])

    selected_testmondais = QuizQuestionSelectionService.call(
      user: @user,
      kajyou: params[:kajyou]
    )

    if selected_testmondais.empty?
      flash[:alert] = "「#{params[:kajyou]}」の出題対象問題がありません（全問正解率50%以上または5回以上解答済み）。"
      redirect_to index_touan_path and return
    end

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

      redirect_to kekka_touan_path(created_at: @touans.collection.first.created_at)
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
    @user   = current_user
    @touans = Touan.where(created_at: Time.zone.parse(params[:created_at]) - 1.minute..Time.zone.parse(params[:created_at]) + 1.minute)
    @touans.each { |t| t.calculate_stats!(user_id: @user.id) }
  end

  private

  def iatf_data_for(owner_key)
    key = OWNER_MAPPING.dig(owner_key, 0)
    return [[], []] if key.nil?

    [Iatf.where("#{key}": '2'), Iatf.where("#{key}": '1')]
  end

  def touans_params
    raw = params.require(:touans)
    list = raw.is_a?(Array) ? raw : raw.values
    list.map do |p|
      p = ActionController::Parameters.new(p) if p.is_a?(Hash)
      p.permit(:kajyou, :kaito, :mondai, :mondai_a, :mondai_b, :mondai_c, :user_id, :seikai, :kaisetsu, :mondai_no, :seikairitsu,
               :total_answers, :correct_answers, :rev, :created_at, :updated_at)
    end
  end

end
