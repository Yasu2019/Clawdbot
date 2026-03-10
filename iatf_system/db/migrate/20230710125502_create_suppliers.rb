# frozen_string_literal: true

# comment
class CreateSuppliers < ActiveRecord::Migration[7.0]
  def change
    create_table :suppliers do |t|
      t.string :no
      t.string :supplier_name
      t.string :manufacturer_name
      t.string :iso_existence
      t.string :target
      t.string :qms
      t.string :development
      t.string :second_party_audit
      t.string :supplier_development
      t.string :automotive_related
      t.string :departments
      t.string :department
      t.string :transaction_details
      t.string :address1
      t.string :address2
      t.string :postal_code
      t.string :tel
      t.string :fax
      t.string :filename
      t.string :document_name
      t.datetime :issue_date
      t.datetime :feedback_date

      t.timestamps
    end
  end
end
