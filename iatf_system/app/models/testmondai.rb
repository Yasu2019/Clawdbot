# frozen_string_literal: true

class Testmondai < ApplicationRecord
  validates :kajyou, :mondai_no, :mondai, :mondai_a, :mondai_b, :mondai_c, :seikai, presence: true
  validates :seikai, inclusion: { in: %w[a b c] }

  def self.import_test(file)
    TestmondaiImportService.call(file)
  end

  def self.updatable_attributes
    %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu]
  end

  def answer_options
    {
      'a' => mondai_a,
      'b' => mondai_b,
      'c' => mondai_c
    }
  end
end
