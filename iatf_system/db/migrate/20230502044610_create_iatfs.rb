# frozen_string_literal: true

# comment
class CreateIatfs < ActiveRecord::Migration[7.0]
  def change
    create_table :iatfs do |t|
      t.string :no
      t.string :name
      t.string :sales
      t.string :process_design
      t.string :production
      t.string :inspection
      t.string :release
      t.string :procurement
      t.string :equipment
      t.string :measurement
      t.string :policy
      t.string :satisfaction
      t.string :audit
      t.string :corrective_action

      t.timestamps
    end
  end
end
