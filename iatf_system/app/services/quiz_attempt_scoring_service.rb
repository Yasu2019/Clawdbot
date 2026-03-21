# frozen_string_literal: true

class QuizAttemptScoringService
  def self.score!(touans)
    new(touans).score!
  end

  def initialize(touans)
    @touans = Array(touans)
  end

  def score!
    return 0.0 if @touans.empty?

    total_answers = @touans.size
    correct_answers = @touans.count(&:correct_answer?)
    success_rate = correct_answers.to_f / total_answers * 100.0

    @touans.each do |touan|
      touan.update_attribute(:seikairitsu, success_rate)
    end

    success_rate
  end
end
