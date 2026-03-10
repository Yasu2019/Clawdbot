# frozen_string_literal: true

require 'test_helper'

class MeasurementequipmentsControllerTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @measurementequipment = measurementequipments(:one)
    sign_in users(:one)
  end

  test 'should get index' do
    get measurementequipments_url
    assert_response :success
  end

  test 'should get new' do
    get new_measurementequipment_url
    assert_response :success
  end

  test 'should create measurementequipment' do
    assert_difference('Measurementequipment.count') do
      post measurementequipments_url, params: { measurementequipment: {
        categories: 'Category',
        scope_of_internal_testing_laboratories: 'Scope',
        product_measurement_item: 'Item',
        measuring_range: 'Range',
        measuring_instrument_test_equipment: 'Equipment',
        manufacturer: 'Manufacturer',
        equipment_model_name: 'ModelName',
        control_no: 'ControlNo',
        measurement_accuracy: 'Accuracy',
        reference_document_no: 'DocumentNo',
        calibration_in_house_external: 'InHouse',
        laboratory_environmental_conditions: 'Conditions',
        external_calibration_laboratory: 'ExternalLab',
        remarks: 'Remarks'
      } }
    end
    assert_redirected_to measurementequipment_path(Measurementequipment.last)
  end

  test 'should show measurementequipment' do
    get measurementequipment_url(@measurementequipment)
    assert_response :success
  end

  test 'should get edit' do
    get edit_measurementequipment_url(@measurementequipment)
    assert_response :success
  end

  test 'should update measurementequipment' do
    patch measurementequipment_url(@measurementequipment), params: { measurementequipment: {
      categories: 'UpdatedCategory',
      equipment_model_name: 'UpdatedModelName'
      # 他の属性も必要に応じて更新
    } }
    assert_redirected_to measurementequipment_path(@measurementequipment)
  end

  test 'should destroy measurementequipment' do
    assert_difference('Measurementequipment.count', -1) do
      delete measurementequipment_url(@measurementequipment)
    end
    assert_redirected_to measurementequipments_url
  end
end
