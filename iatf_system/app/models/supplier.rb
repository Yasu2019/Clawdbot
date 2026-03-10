# frozen_string_literal: true
# comment
class Supplier < ApplicationRecord
  has_many_attached :documents
end
