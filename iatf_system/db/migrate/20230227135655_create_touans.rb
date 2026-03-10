# frozen_string_literal: true

# comment
class CreateTouans < ActiveRecord::Migration[7.0]
  def change
    create_table :touans do |t|
      t.string :kajyou
      t.string :mondai_no
      t.string :rev
      t.string :mondai
      t.string :mondai_a
      t.string :mondai_b
      t.string :mondai_c
      t.string :seikai
      t.string :kaisetsu
      t.string :kaito
      t.integer :user_id
      t.integer :total_answers
      t.integer :correct_answers

      t.timestamps
    end
  end
end
