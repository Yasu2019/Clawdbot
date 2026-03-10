# frozen_string_literal: true

class CreateMeasurementequipments < ActiveRecord::Migration[7.0]
  def change
    create_table :measurementequipments do |t|
      t.string :categories
      t.string :scope_of_internal_testing_laboratories
      t.string :product_measurement_item
      t.string :measuring_range
      t.string :measuring_instrument_test_equipment
      t.string :manufacturer
      t.string :equipment_model_name
      t.string :control_no
      t.string :measurement_accuracy
      t.string :reference_document_no
      t.string :calibration_in_house_external
      t.string :laboratory_environmental_conditions
      t.string :external_calibration_laboratory
      t.string :remarks

      t.timestamps
    end
  end
end
