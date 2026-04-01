# frozen_string_literal: true

require "json"

class UpdateHistoryService
  HISTORY_PATH = Rails.root.join("db/update_history.json")
  AUTO_DIFF_STATUS_PATH = Rails.root.join("..", "data", "workspace", "iatf_seed_auto_update_status.json").cleanpath

  class << self
    def call
      new.call
    end
  end

  def call
    entries = load_entries.sort_by { |entry| entry["recorded_at"].to_s }.reverse
    {
      total: entries.length,
      entries: entries,
      auto_diff_status: load_auto_diff_status
    }
  end

  private

  def load_entries
    return [] unless File.exist?(HISTORY_PATH)

    JSON.parse(File.read(HISTORY_PATH, encoding: "utf-8"))
  rescue StandardError
    []
  end

  def load_auto_diff_status
    return {} unless File.exist?(AUTO_DIFF_STATUS_PATH)

    JSON.parse(File.read(AUTO_DIFF_STATUS_PATH, encoding: "utf-8"))
  rescue StandardError
    {}
  end
end
