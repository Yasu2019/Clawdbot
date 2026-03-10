# frozen_string_literal: true

class MemoryUsageMailer < ApplicationMailer
  default from: 'mitsui.seimitsu.iatf16949@gmail.com'

  def send_cache_count(email, cache_counts)
    @cache_counts = cache_counts

    mail(to: email, subject: 'キャッシュ数の通知')
  end

  def send_memory_usage_with_success_message(email, current_memory, max_memory, min_memory, avg_memory,
                                             stackprof_results, backup_message, cache_counts)
    @current_memory = current_memory
    @max_memory = max_memory
    @min_memory = min_memory
    @avg_memory = avg_memory
    @backup_message = backup_message
    @stackprof_results = stackprof_results
    @cache_counts = cache_counts

    mail(to: email, subject: 'アプリのメモリ使用量の統計とデータベースバックアップの通知')
  end
end
