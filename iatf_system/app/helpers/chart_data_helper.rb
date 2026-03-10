# frozen_string_literal: true

module ChartDataHelper
  def calculate_chart_data(iatf_data, touans)
    chart_kajyou = []
    chart_average_score = []

    iatf_data.each do |iatf|
      next unless iatf.no

      only_kajyou = touans.where(kajyou: iatf.no)
      correct_count = only_kajyou.select { |ave| ave.seikai == ave.kaito }.size
      total_count = only_kajyou.size

      kari_average_score = total_count.positive? ? (correct_count.to_f / total_count * 100) : 0.0

      chart_kajyou.push(iatf.no)
      chart_average_score.push(kari_average_score)
    end

    [chart_kajyou, chart_average_score]
  end
end
