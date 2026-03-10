# frozen_string_literal: true

# comment
class CreateIatflists < ActiveRecord::Migration[7.0]
  def change
    create_table :iatflists do |t|
      t.string :iatf_number
      t.text :iatf_content

      t.timestamps
    end
  end
end
