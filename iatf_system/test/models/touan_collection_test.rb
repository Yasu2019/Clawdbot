# frozen_string_literal: true

require 'test_helper'
require Rails.root.join('app/controllers/touan_collection')

class TouanCollectionTest < ActiveSupport::TestCase
  test 'builds collection from selected testmondai objects when params are empty' do
    user = users(:one)
    testmondai = Testmondai.new(
      kajyou: '8.5',
      mondai_no: 'Q-001',
      mondai: 'Question',
      mondai_a: 'A',
      mondai_b: 'B',
      mondai_c: 'C',
      seikai: 'a',
      kaisetsu: 'Explanation',
      rev: 'URL'
    )

    collection = TouanCollection.new([], [testmondai], user)

    assert_equal 1, collection.collection.size
    assert_equal '8.5', collection.collection.first.kajyou
    assert_equal 'Q-001', collection.collection.first.mondai_no
    assert_equal user.id, collection.collection.first.user_id
  end

  test 'builds collection from submitted params' do
    user = users(:one)
    params = [{
      'kajyou' => '9.1',
      'mondai_no' => 'Q-002',
      'mondai' => 'Another Question',
      'mondai_a' => 'A',
      'mondai_b' => 'B',
      'mondai_c' => 'C',
      'seikai' => 'b',
      'kaisetsu' => 'Explanation',
      'rev' => 'URL',
      'kaito' => 'a'
    }]

    collection = TouanCollection.new(params, [], user)

    assert_equal 1, collection.collection.size
    assert_equal '9.1', collection.collection.first.kajyou
    assert_equal 'a', collection.collection.first.kaito
    assert_equal user.id, collection.collection.first.user_id
  end
end
