# frozen_string_literal: true

class AddSeikairitsuToTouans < ActiveRecord::Migration[7.0]
  def change
    add_column :touans, :seikairitsu, :float, default: 0.0
  end
end
