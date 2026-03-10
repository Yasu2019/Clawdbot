# frozen_string_literal: true

require 'test_helper'

class SuppliersControllerTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers # Deviseのテストヘルパーをインクルード

  setup do
    @supplier = suppliers(:one) # suppliers(:one) はテスト用のサプライヤーフィクスチャを指します
    sign_in users(:one) # users(:one) はテスト用のユーザーフィクスチャを指します
  end

  test 'should get index' do
    get suppliers_url
    assert_response :success
  end

  test 'should get new' do
    get new_supplier_url
    assert_response :success
  end

  test 'should create supplier' do
    assert_difference('Supplier.count') do
      post suppliers_url,
           params: {
             supplier: {
               supplier_name: '新規サプライヤー',
               manufacturer_name: '新規メーカー',
               iso_existence: 'ISO9001取得有り',
               target: true,
               qms: 'ISO 9001',
               second_party_audit: '△',
               supplier_development: '？',
               automotive_related: true,
               departments: '加工課',
               transaction_details: '新規取引詳細',
               address1: '新規住所1',
               address2: '新規住所2',
               postal_code: '123-4567',
               tel: '03-1234-5678',
               fax: '03-1234-5679'
             }
           }
    end

    assert_redirected_to supplier_url(Supplier.last)
  end

  test 'should show supplier' do
    get supplier_url(@supplier)
    assert_response :success
  end

  test 'should get edit' do
    get edit_supplier_url(@supplier)
    assert_response :success
  end

  test 'should update supplier' do
    patch supplier_url(@supplier), params: { supplier: { supplier_name: '更新サプライヤー' } }
    assert_redirected_to supplier_url(@supplier)
    # データベースの値が更新されたことを確認
    @supplier.reload
    assert_equal '更新サプライヤー', @supplier.supplier_name
  end

  test 'should destroy supplier' do
    assert_difference('Supplier.count', -1) do
      delete supplier_url(@supplier)
    end

    assert_redirected_to suppliers_url
  end
end
