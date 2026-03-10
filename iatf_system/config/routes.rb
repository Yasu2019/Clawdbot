# frozen_string_literal: true

Rails.application.routes.draw do
  Rails.logger.debug "ルーティングが読み込まれました"
  get '/favicon.ico', to: 'public#favicon'
  get '/robots.:format' => 'public#robots'

  mount LetterOpenerWeb::Engine, at: '/letter_opener' if Rails.env.development?

  resources :two_step_verifications, only: %i[new create]

  get 'verify/:token', to: 'verification#verify', as: :verify_token

  get 'products/export_to_excel', to: 'products#export_to_excel', as: 'export_to_excel_product'

  get 'measurementequipments/index' => 'measurementequipments#index', as: 'index_measurementequipments'

  resources :measurementequipments

  get 'suppliers/index' => 'suppliers#index', as: 'index_suppliers'
  resources :suppliers do
    member do
      get 'verify_password/:blob_id', to: 'downloadable#verify_password', as: :supplier_verify_password
    end
  end

  devise_for :users, controllers: {
    sessions: 'users/sessions'
  }

  devise_scope :user do
    patch '/users/sign_in', to: 'users/sessions#create'
    get '/users/two_step_verification', to: 'users/sessions#new_two_step_verification'
    post '/users/two_step_verification', to: 'users/sessions#create_two_step_verification'
  end

  get 'touans/export_to_excel', to: 'touans#export_to_excel'

  get 'touans/iatf_csr_mitsui' => 'touans#iatf_csr_mitsui', as: 'iatf_csr_mitsui_touan'

  get 'touans/testmondai' => 'touans#testmondai', as: 'testmondai_touan'
  get 'touans/index' => 'touans#index', as: 'index_touan'
  get 'touans/kekka' => 'touans#kekka', as: 'kekka_touan'
  get 'touans/xlsx' => 'touans#xlsx', as: 'xlsx_touan'
  get 'touans/member_current_status' => 'touans#member_current_status', as: 'member_current_status_touan'

  resources :touans, only: %i[index new create destroy] do
    collection do
      delete 'delete_related'
      delete 'delete_testmondai', as: 'delete_testmondai'
    end
  end

  get 'products/process_design_plan_report' => 'products#process_design_plan_report', as: 'rubyxl_product'
  get 'products/apqp_plan_report' => 'products#apqp_plan_report', as: 'rubyxl_apqp_plan_report_product'
  get 'products/apqp_approved_report' => 'products#apqp_approved_report', as: 'rubyxl_apqp_approved_report_product'

  get 'products/iot' => 'products#iot', as: 'iot_product'
  get 'products/graph' => 'products#graph', as: 'graph_product'
  get 'products/calendar' => 'products#calendar', as: 'calendar_product'
  get 'products/training' => 'products#training', as: 'training_product'
  get 'products/index2' => 'products#index2', as: 'index2_product'
  get 'products/index3' => 'products#index3', as: 'index3_product'
  get 'products/index4' => 'products#index4', as: 'index4_product'
  get 'products/index8' => 'products#index8', as: 'index8_product'
  get 'products/index9' => 'products#index9', as: 'index9_product'

  get 'products/xlsx' => 'products#xlsx', as: 'xlsx_product'
  get 'products/download' => 'products#download', as: 'download_product'
  get 'products/process_design_download' => 'products#process_design_download', as: 'process_design_download'

  root to: 'products#index'

  resources :products, only: %i[index new create show edit update] do
    collection do 
      post :import
      get 'export_phases_to_excel'
      get 'audit_correction_report'  
      get 'audit_improvement_opportunity'  
      get 'in_process_nonconforming_product_control_form'  
    end
    member do
      get 'verify_password/:blob_id', to: 'downloadable#verify_password', as: :product_verify_password
      post 'verify_password/:blob_id', to: 'downloadable#verify_password_post', as: :product_verify_password_post
      post 'download', to: 'downloadable#download'
    end
  end

  resources :touans, only: [] do
    member do
      get 'verify_password/:blob_id', to: 'downloadable#verify_password', as: :touan_verify_password
      post 'download', to: 'downloadable#download'
    end
  end

  resources :touans do
    collection { post :import_test }
    collection { post :import_kaitou }
  end
end