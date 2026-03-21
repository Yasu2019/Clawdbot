# frozen_string_literal: true

class ChangeQuizTextColumnsToText < ActiveRecord::Migration[7.0]
  def up
    change_column :testmondais, :mondai, :text
    change_column :testmondais, :mondai_a, :text
    change_column :testmondais, :mondai_b, :text
    change_column :testmondais, :mondai_c, :text
    change_column :testmondais, :kaisetsu, :text

    change_column :touans, :mondai, :text
    change_column :touans, :mondai_a, :text
    change_column :touans, :mondai_b, :text
    change_column :touans, :mondai_c, :text
    change_column :touans, :kaisetsu, :text
  end

  def down
    change_column :testmondais, :mondai, :string
    change_column :testmondais, :mondai_a, :string
    change_column :testmondais, :mondai_b, :string
    change_column :testmondais, :mondai_c, :string
    change_column :testmondais, :kaisetsu, :string

    change_column :touans, :mondai, :string
    change_column :touans, :mondai_a, :string
    change_column :touans, :mondai_b, :string
    change_column :touans, :mondai_c, :string
    change_column :touans, :kaisetsu, :string
  end
end
