# frozen_string_literal: true

class AddVerificationTokenToUsers < ActiveRecord::Migration[7.0]
  def change
    add_column :users, :verification_token, :string
    add_column :users, :token_expiry, :datetime
  end
end
