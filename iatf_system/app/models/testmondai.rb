# frozen_string_literal: true

# このクラスはApplicationRecordを継承し、ActiveRecordの機能を使用しています。
class Testmondai < ApplicationRecord
  # 【Ruby on Rails】CSVインポート
  # https://qiita.com/seitarooodayo/items/c9d6955a12ca0b1fd1d4

  def self.import_test(file)
    CSV.foreach(file.path, headers: true) do |row|
      # IDが見つかれば、レコードを呼び出し、見つかれなければ、新しく作成
      testmondai = find_by(id: row['id']) || new
      # CSVからデータを取得し、設定する
      testmondai.attributes = row.to_hash.slice(*updatable_attributes)
      # 保存する
      testmondai.save
    end
  end

  # 更新を許可するカラムを定義
  def self.updatable_attributes
    %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu]
  end

  # def self.import_test(file)
  #  ActiveRecord::Base.transaction do
  #    CSV.foreach(file.path, headers: true) do |row|
  #      testmondai_data = row.to_hash.slice(*updatable_attributes)
  #      testmondai = find_by(kajyou: testmondai_data["kajyou"], mondai_no: testmondai_data["mondai_no"]) || new
  #      testmondai.update(testmondai_data)
  #    end
  #  end
  # end

  # def self.import_test(file)
  #  transaction do
  #    CSV.foreach(file.path, headers: true) do |row|
  #      # CSVからデータを取得
  #      testmondai_data = row.to_hash.slice(*updatable_attributes)

  #      # kajyou と mondai_no の組み合わせで既存のレコードを検索
  #      testmondai = find_by(kajyou: testmondai_data["kajyou"], mondai_no: testmondai_data["mondai_no"])

  #      # 既存のレコードが見つからなければ、新しいレコードを作成
  #      testmondai ||= new

  #      # データを設定して保存
  #      testmondai.attributes = testmondai_data
  #      testmondai.save!
  #    end
  #    end
  # end

  # 更新を許可するカラムを定義
  # def self.updatable_attributes
  #  ["kajyou", "mondai_no","rev","mondai","mondai_a","mondai_b","mondai_c","seikai","kaisetsu"]
  # end
end
