# frozen_string_literal: true

# comment
class CreateCsrs < ActiveRecord::Migration[7.0]
  def change
    create_table :csrs do |t|
      t.string :csr_number
      t.text :csr_content

      t.timestamps
    end
  end
end
