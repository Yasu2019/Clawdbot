# frozen_string_literal: true

class QuizQuestionSelectionService
  DEFAULT_LIMIT = 10
  DEFAULT_MAX_SUCCESS_RATE = 50.0
  DEFAULT_MAX_TOTAL_ANSWERS = 5

  def self.call(user:, kajyou:, limit: DEFAULT_LIMIT,
                max_success_rate: DEFAULT_MAX_SUCCESS_RATE,
                max_total_answers: DEFAULT_MAX_TOTAL_ANSWERS)
    new(
      user:,
      kajyou:,
      limit:,
      max_success_rate:,
      max_total_answers:
    ).call
  end

  def initialize(user:, kajyou:, limit:, max_success_rate:, max_total_answers:)
    @user = user
    @kajyou = kajyou
    @limit = limit
    @max_success_rate = max_success_rate
    @max_total_answers = max_total_answers
  end

  def call
    low_priority_candidates.sample(@limit)
  end

  private

  def low_priority_candidates
    stats = Testmondai.where(kajyou: @kajyou).map do |testmondai|
      total_answers = Touan.where(
        mondai_no: testmondai.mondai_no,
        kajyou: testmondai.kajyou,
        user_id: @user.id
      ).count

      correct_answers = Touan.correct_answers_for(
        user_id: @user.id,
        mondai_no: testmondai.mondai_no,
        kajyou: testmondai.kajyou
      )

      success_rate = total_answers.positive? ? (correct_answers.to_f / total_answers * 100.0) : 0.0

      {
        testmondai:,
        total_answers:,
        success_rate:
      }
    end

    stats
      .select do |stat|
        stat[:success_rate] < @max_success_rate && stat[:total_answers] < @max_total_answers
      end
      .map { |stat| stat[:testmondai] }
  end
end
