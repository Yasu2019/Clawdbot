# frozen_string_literal: true

class TouanCollection
  include ActiveModel::Conversion
  extend ActiveModel::Naming
  extend ActiveModel::Translation
  include ActiveModel::AttributeMethods
  include ActiveModel::Validations

  attr_accessor :collection, :user # userを追加

  # def initialize(params, testmondais, user)  # userを引数に追加
  # selected_testmondais を引数に追加
  def initialize(params, selected_testmondais, user)
    self.user = user # userをセット
    self.collection = []

    # ここに重複なくランダムに10件の問題を選択するコードを追加
    # testmondais = testmondais.sample(10)

    # binding.pry
    if params.present?
      self.collection = params.map do |value|
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
          user_id: user.id # 試験をするUserのidを登録しています
        )
      end
    end
    # params が存在しない場合、selected_testmondais を使って @collection をセット
    return if collection.present?

    #  testmondais.each do |test|
    selected_testmondais.each do |test|
      touan = Touan.new(
        kajyou: test.kajyou,
        mondai: test.mondai,
        mondai_no: test.mondai_no,
        mondai_a: test.mondai_a,
        mondai_b: test.mondai_b,
        mondai_c: test.mondai_c,
        seikai: test.seikai,
        kaisetsu: test.kaisetsu,
        rev: test.rev,
        user_id: user.id # 試験をするUserのidを登録するために、インスタンスを生成しています
      )
      @collection << touan
    end
  end

  def persisted?
    false
  end

  def save
    @collection.each(&:save)
  end
end
