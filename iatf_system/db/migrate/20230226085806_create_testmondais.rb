# frozen_string_literal: true

class CreateTestmondais < ActiveRecord::Migration[7.0]
  def change
    create_table :testmondais do |t|
      t.string :kajyou
      t.string :mondai_no
      t.string :rev
      t.string :mondai
      t.string :mondai_a
      t.string :mondai_b
      t.string :mondai_c
      t.string :seikai
      t.string :kaisetsu

      t.timestamps
    end
  end
end
