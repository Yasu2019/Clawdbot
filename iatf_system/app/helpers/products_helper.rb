# frozen_string_literal: true
# comment
module ProductsHelper
  def product_field(value)
    value.blank? ? '----' : value
  end

  def product_date(date)
    date.nil? ? '------' : date.strftime('%y/%m/%d')
  end

end
