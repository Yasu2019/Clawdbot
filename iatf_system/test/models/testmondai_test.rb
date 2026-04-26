# frozen_string_literal: true

require 'test_helper'

class TestmondaiTest < ActiveSupport::TestCase
  test 'updatable_attributes includes core quiz columns' do
    assert_equal %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu],
                 Testmondai.updatable_attributes
  end
end
