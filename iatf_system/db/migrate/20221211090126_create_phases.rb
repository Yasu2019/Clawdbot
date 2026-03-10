# frozen_string_literal: true

class CreatePhases < ActiveRecord::Migration[7.0]
  def change
    create_table :phases do |t|
      t.string :name
      t.string :ancestry

      t.timestamps
    end
  end
end
