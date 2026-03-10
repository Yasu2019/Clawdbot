# frozen_string_literal: true

# このクラスはApplicationRecordを継承し、ActiveRecordの機能を使用しています。
class Touan < ApplicationRecord
  after_save :update_cache
  # バリデーション
  validates :kaito, presence: true

  # 保存されるたびにキャッシュを更新するコールバック
  after_save :update_cache

  # CSV インポートに関するメソッド
  def self.import_kaitou(file)
    CSV.foreach(file.path, headers: true) do |row|
      testkaitou = find_by(id: row['id']) || new
      testkaitou.attributes = row.to_hash.slice(*updatable_attributes)
      testkaitou.save
    end
  end

  # 更新を許可するカラムを定義
  def self.updatable_attributes
    %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu kaito user_id
       total_answers correct_answers seikairitsu created_at updated_at]
  end

  private

  # キャッシュの更新をトリガーするメソッド
  def update_cache
    CacheUpdateJob.perform_async(user_id)
  end
end
