# frozen_string_literal: true

class Testmondai < ApplicationRecord
  def self.import_test(file)
    TestmondaiImportService.call(file)
  end

  def self.updatable_attributes
    %w[id kajyou mondai_no rev mondai mondai_a mondai_b mondai_c seikai kaisetsu]
  end
end
