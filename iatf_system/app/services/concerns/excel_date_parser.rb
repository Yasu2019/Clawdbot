# frozen_string_literal: true

# Excel セルから日付を安全にパースする共通モジュール。
module ExcelDateParser
  private

  def parse_date(cell_value)
    case cell_value
    when Date, Time
      cell_value
    when String
      begin
        Date.parse(cell_value)
      rescue Date::Error
        cell_value
      end
    when Numeric
      begin
        Date.new(1899, 12, 30) + cell_value.to_i
      rescue Date::Error
        cell_value
      end
    else
      cell_value
    end
  end
end
