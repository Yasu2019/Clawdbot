# frozen_string_literal: true

class TouanCollection
  include ActiveModel::Conversion
  extend ActiveModel::Naming
  extend ActiveModel::Translation
  include ActiveModel::AttributeMethods
  include ActiveModel::Validations

  attr_accessor :collection, :user

  def initialize(params, selected_testmondais, user)
    self.user = user
    self.collection = []

    if params.present?
      self.collection = params.map do |value|
        value = value.to_h if value.respond_to?(:to_h)
        Touan.new(
          kaito: value['kaito'],
          kajyou: value['kajyou'],
          mondai: value['mondai'],
          mondai_no: value['mondai_no'],
          mondai_a: value['mondai_a'],
          mondai_b: value['mondai_b'],
          mondai_c: value['mondai_c'],
          seikai: value['seikai'],
          kaisetsu: value['kaisetsu'],
          rev: value['rev'],
          user_id: user.id
        )
      end
    end

    return if collection.present?

    selected_testmondais.each do |test|
      collection << Touan.new(
        kajyou: test.kajyou,
        mondai: test.mondai,
        mondai_no: test.mondai_no,
        mondai_a: test.mondai_a,
        mondai_b: test.mondai_b,
        mondai_c: test.mondai_c,
        seikai: test.seikai,
        kaisetsu: test.kaisetsu,
        rev: test.rev,
        user_id: user.id
      )
    end
  end

  def persisted?
    false
  end

  def save
    collection.all?(&:save)
  end
end
