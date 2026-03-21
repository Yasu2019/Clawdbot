# frozen_string_literal: true

require 'test_helper'

class TouanTest < ActiveSupport::TestCase
  test 'correct_answer? is true only when kaito matches seikai' do
    touan = Touan.new(kaito: 'a', seikai: 'a')
    assert touan.correct_answer?

    touan.kaito = 'b'
    assert_not touan.correct_answer?
  end

  test 'correct_answers_for counts only matching answers' do
    user = users(:one)
    Touan.create!(kajyou: '1', mondai_no: 'Q1', seikai: 'a', kaito: 'a', user_id: user.id)
    Touan.create!(kajyou: '1', mondai_no: 'Q1', seikai: 'a', kaito: 'b', user_id: user.id)
    Touan.create!(kajyou: '1', mondai_no: 'Q2', seikai: 'c', kaito: 'c', user_id: user.id)

    assert_equal 1, Touan.correct_answers_for(user_id: user.id, mondai_no: 'Q1')
    assert_equal 1, Touan.correct_answers_for(user_id: user.id, mondai_no: 'Q1', kajyou: '1')
    assert_equal 1, Touan.correct_answers_for(user_id: user.id, mondai_no: 'Q2')
  end
end
