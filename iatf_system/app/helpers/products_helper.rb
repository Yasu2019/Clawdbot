# frozen_string_literal: true
# comment
module ProductsHelper
  def product_field(value)
    value.blank? ? '----' : value
  end

  def product_date(date)
    date.nil? ? '------' : date.strftime('%y/%m/%d')
  end

  def product_stage_status(products, koumo, dropdownlist)
    matched = products.select { |product| dropdownlist[product.stage.to_i] == koumo }
    return :none if matched.empty?

    return :complete if matched.any? { |product| product.status.to_s == '完了' }
    return :wip if matched.any? { |product| product.status.to_s.include?('仕掛') }

    :none
  end

  def product_type_candidates(products)
    candidates = products.flat_map do |product|
      extract_type_candidates(product.documentname.to_s, product.materialcode.to_s)
    end

    normalized = candidates.map(&:strip).reject(&:blank?).uniq
    normalized.presence || ['識別候補なし']
  end

  private

  def extract_type_candidates(documentname, materialcode)
    values = []

    [
      /増面型No\.?\s*\d+/,
      /量産型No\.?\s*\d+/,
      /\d+号機/,
      /\d+型/,
      /PM[A-Z0-9]+/
    ].each do |pattern|
      documentname.scan(pattern) { |match| values << match }
    end

    values << materialcode if materialcode.present?
    values
  end

end
