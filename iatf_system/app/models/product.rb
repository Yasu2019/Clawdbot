# frozen_string_literal: true

class Product < ApplicationRecord
  has_many_attached :documents

  # Ransackable attributes
  def self.ransackable_attributes(auth_object = nil)
    %w[partnumber materialcode documentname description category phase stage status
       start_time deadline_at end_at goal_attainment_level_eq]
  end

  # Ransackable associations
  def self.ransackable_associations(auth_object = nil)
    []
  end

  # Ransackable scopes
  def self.ransackable_scopes(auth_object = nil)
    [:start_time_between, :deadline_at_between, :end_at_between, :goal_attainment_level_gteq]
  end
  
  # Scopes for date and numeric fields
  scope :start_time_between, ->(start_date, end_date) { where(start_time: start_date..end_date) }
  scope :deadline_at_between, ->(start_date, end_date) { where(deadline_at: start_date..end_date) }
  scope :end_at_between, ->(start_date, end_date) { where(end_at: start_date..end_date) }
  scope :goal_attainment_level_gteq, ->(value) { where('goal_attainment_level >= ?', value) }

  # CSV import method
  def self.import(file)
    CSV.foreach(file.path, headers: true) do |row|
      product = find_by(id: row['id']) || new
      product.attributes = row.to_hash.slice(*updatable_attributes)
      product.save
    end
  end

  # Updatable attributes for CSV import
  def self.updatable_attributes
    %w[id partnumber materialcode documentname description category phase stage 
       start_time deadline_at end_at goal_attainment_level status]
  end
end
