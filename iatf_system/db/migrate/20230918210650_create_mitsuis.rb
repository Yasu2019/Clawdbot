# frozen_string_literal: true

class CreateMitsuis < ActiveRecord::Migration[7.0]
  def change
    create_table :mitsuis do |t|
      t.string :mitsui_number
      t.text :mitsui_content

      t.timestamps
    end
  end
end
