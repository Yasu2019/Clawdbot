# app/controllers/suppliers_controller.rb
# frozen_string_literal: true

class SuppliersController < ApplicationController
  before_action :set_supplier, only: %i[show edit update destroy verify_password]

  # GET /suppliers
  def index
    @suppliers = Supplier.includes(documents_attachments: :blob).all
  end

  # GET /suppliers/1
  def show; end

  # GET /suppliers/new
  def new
    @supplier = Supplier.new
  end

  # GET /suppliers/1/edit
  def edit; end

  # POST /suppliers
  def create
    @supplier = Supplier.new(supplier_params)

    if @supplier.save
      redirect_to @supplier, notice: 'Supplier was successfully created.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  # PATCH/PUT /suppliers/1
  def update
    if @supplier.update(supplier_params)
      redirect_to @supplier, notice: 'Supplier was successfully updated.'
    else
      render :edit, status: :unprocessable_entity
    end
  end

  # DELETE /suppliers/1
  def destroy
    @supplier.destroy
    redirect_to suppliers_url, notice: 'Supplier was successfully destroyed.'
  end

  # GET /suppliers/1/verify_password/:blob_id
  def verify_password
    # ここにパスワード確認のロジックを追加します
    # 例: @supplier.verify_password(params[:blob_id])
  end

  private

  # Use callbacks to share common setup or constraints between actions.
  def set_supplier
    @supplier = Supplier.find(params[:id])
  end

  # Only allow a list of trusted parameters through.
  def supplier_params
    params.require(:supplier).permit(:supplier_name, :manufacturer_name, :iso_existence, :target, :qms, :development,
                                     :second_party_audit, :supplier_development, :automotive_related, :departments, :department, :transaction_details, :address1, :address2, :postal_code, :tel, :fax, :filename, :document_name, :issue_date, :feedback_date, :no, documents: [])
  end
end