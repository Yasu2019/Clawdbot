# frozen_string_literal: true

# CSR / IATFリスト / ミツイ精密 品質マニュアルを Excel に出力するサービス。
# TouansController#export_to_excel から呼び出される。
class ExportCsrIatfToExcelService
  def self.call(csrs:, iatflists:, mitsuis:)
    new(csrs:, iatflists:, mitsuis:).call
  end

  def initialize(csrs:, iatflists:, mitsuis:)
    @csrs      = csrs
    @iatflists = iatflists
    @mitsuis   = mitsuis
  end

  def call
    package = Axlsx::Package.new
    package.workbook.add_worksheet(name: 'Basic Worksheet') do |sheet|
      sheet.add_row ['箇条', 'MEK様品質ガイドラインVer2', 'IATF規格要求事項', 'ミツイ精密 品質マニュアル']
      sheet.column_widths 15, 40, 40, 40

      build_rows.each { |row| sheet.add_row row }
    end

    package.to_stream.read
  end

  private

  def build_rows
    rows = []
    [@csrs, @iatflists, @mitsuis].each do |records|
      records.each do |record|
        number   = record_number(record)
        csr      = @csrs.find { |c| c.csr_number == number }
        iatflist = @iatflists.find { |i| i.iatf_number == number }
        mitsui   = @mitsuis.find { |m| m.mitsui_number == number }

        next unless csr || iatflist || mitsui

        rows << [number, csr&.csr_content.to_s, iatflist&.iatf_content.to_s, mitsui&.mitsui_content.to_s]
      end
    end

    rows.sort_by { |row| row[0].split('.').map(&:to_i) }.uniq
  end

  def record_number(record)
    if record.respond_to?(:csr_number)     then record.csr_number
    elsif record.respond_to?(:iatf_number) then record.iatf_number
    else                                        record.mitsui_number
    end
  end
end
