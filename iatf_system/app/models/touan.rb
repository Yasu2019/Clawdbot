# frozen_string_literal: true

class Touan < ApplicationRecord
  after_save :update_cache

  validates :kaito, presence: true

  def self.import_kaitou(file)
    TouanImportService.call(file)
  end

  def self.updatable_attributes
    %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu kaito user_id
       total_answers correct_answers seikairitsu created_at updated_at]
  end

  def correct_answer?
    kaito.present? && seikai.present? && kaito == seikai
  end

  def self.correct_answers_for(user_id:, mondai_no:, kajyou: nil, up_to_id: nil)
    scope = where(user_id:, mondai_no:)
    scope = scope.where(kajyou:) if kajyou.present?
    scope = scope.where('id <= ?', up_to_id) if up_to_id.present?
    scope.select(&:correct_answer?).count
  end

  private

  def update_cache
    CacheUpdateJob.perform_async(user_id)
  end
end
