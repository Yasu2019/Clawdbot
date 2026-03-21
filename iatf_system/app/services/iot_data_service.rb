# frozen_string_literal: true

# IoT センサーデータを CSV から読み込むサービス。
# ProductsController#iot から呼び出される。
class IotDataService
  IOT_DIR = '/myapp/db/record/iot'

  CSV_SOURCES = {
    temp:                      'SHT31Temp.csv',
    humi:                      'SHT31Humi.csv',
    komatsu25t3_shot:          'ShotKomatsu25t3.csv',
    komatsu25t3_spm:           'SPMKomatsu25t3.csv',
    komatsu25t3_chokotei:      'StampingchokoteiKomatsu25t3.csv',
    komatsu25t3_jyotai:        'JYOTAIKomatsu25t3.csv',
    chokoteiDobby30t4:         'chokoteiDobby30t4.csv',
    JYOTAIDobby30t4:           'JYOTAIDobby30t4.csv',
    StampingJYOTAIAmada80t3:   'StampingJYOTAIAmada80t3.csv',
    StampingchokoteiAmada80t3: 'StampingchokoteiAmada80t3.csv',
    SPMAmada80t3:              'SPMAmada80t3.csv',
    ShotAmada80t3:             'ShotAmada80t3.csv'
  }.freeze

  def self.call
    new.call
  end

  def call
    timetoday = Time.current.strftime('%Y_%m_%d')
    CSV_SOURCES.each_with_object({}) do |(key, filename), result|
      result[key] = load_csv("#{IOT_DIR}/#{timetoday}#{filename}")
    end
  end

  private

  def load_csv(path)
    return nil unless File.file?(path)
    [].tap do |data|
      CSV.foreach(path, headers: true) { |row| data << [row[0], row[1]] }
    end
  end
end
