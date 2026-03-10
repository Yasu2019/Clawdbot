# frozen_string_literal: true

require 'test_helper'

class VerificationControllerTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @user_with_valid_token = users(:valid_token_user)
    @user_with_expired_token = users(:expired_token_user)
    sign_out :user # Deviseのヘルパーメソッドを使用して、すべてのユーザーをログアウトさせる
  end

  test 'verify user with a valid token' do
    get verify_token_path(token: @user_with_valid_token.verification_token)
    assert_redirected_to root_path
  end

  test 'do not verify user with an expired token' do
    get verify_token_path(token: @user_with_expired_token.verification_token)
    assert_redirected_to new_user_session_path
    follow_redirect!
    assert_equal 'トークンが期限切れです。', flash[:alert]
  end

  test 'do not verify user with a non-existent token' do
    get verify_token_path(token: 'nonexistenttoken')
    assert_redirected_to new_user_session_path
    follow_redirect!
    assert_equal 'トークンが存在しません。', flash[:alert]
  end
end
