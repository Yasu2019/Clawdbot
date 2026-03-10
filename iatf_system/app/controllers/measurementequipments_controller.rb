# frozen_string_literal: true

class MeasurementequipmentsController < ApplicationController
  before_action :set_measurementequipment, only: %i[show edit update destroy]

  # GET /measurementequipments
  def index
    @measurementequipments = Measurementequipment.all
  end

  # GET /measurementequipments/1
  def show; end

  # GET /measurementequipments/new
  def new
    @measurementequipment = Measurementequipment.new
  end

  # GET /measurementequipments/1/edit
  def edit; end

  # POST /measurementequipments
  def create
    @measurementequipment = Measurementequipment.new(measurementequipment_params)

    if @measurementequipment.save
      redirect_to @measurementequipment, notice: 'Measurementequipment was successfully created.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  # PATCH/PUT /measurementequipments/1
  def update
    if @measurementequipment.update(measurementequipment_params)
      redirect_to @measurementequipment, notice: 'Measurementequipment was successfully updated.'
    else
      render :edit, status: :unprocessable_entity
    end
  end

  # DELETE /measurementequipments/1
  def destroy
    @measurementequipment.destroy
    redirect_to measurementequipments_url, notice: 'Measurementequipment was successfully destroyed.'
  end

  private

  # Use callbacks to share common setup or constraints between actions.
  def set_measurementequipment
    @measurementequipment = Measurementequipment.find(params[:id])
  end

  # Only allow a list of trusted parameters through.
  def measurementequipment_params
    params.require(:measurementequipment).permit(:categories, :scope_of_internal_testing_laboratories,
                                                 :product_measurement_item, :measuring_range, :measuring_instrument_test_equipment, :manufacturer, :model_name, :control_no, :measurement_accuracy, :reference_document_no, :calibration_in_house_external, :laboratory_environmental_conditions, :external_calibration_laboratory, :remarks)
  end
end
