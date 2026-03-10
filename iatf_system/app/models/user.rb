# frozen_string_literal: true

# このクラスはApplicationRecordを継承し、ActiveRecordの機能を使用しています。
class User < ApplicationRecord
  devise :two_factor_authenticatable,
         otp_secret_encryption_key: ENV.fetch('OTP_SECRET_KEY', nil)
  # Include default devise modules. Others available are:
  # :confirmable, :lockable, :timeoutable, :trackable and :omniauthable
  devise :registerable,
         :recoverable, :rememberable, :validatable
end
