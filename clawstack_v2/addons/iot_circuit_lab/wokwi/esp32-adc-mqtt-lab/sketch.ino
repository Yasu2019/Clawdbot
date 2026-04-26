#include <WiFi.h>
#include <PubSubClient.h>

#define ADC_PIN 34
#define LED_PIN 2
#define BUZZER_PIN 13

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";

// Wokwi Private IoT Gateway経由でMiniPC側MQTTへ接続
const char* MQTT_HOST = "host.wokwi.internal";
const uint16_t MQTT_PORT = 1883;

const char* DEVICE_ID = "esp32-adc-001";
const char* TOPIC_TELEMETRY = "factory/lab/esp32-adc-001/telemetry";
const char* TOPIC_STATUS    = "factory/lab/esp32-adc-001/status";
const char* TOPIC_CMD       = "factory/lab/esp32-adc-001/cmd";

// LTspice結果から調整する値
const float ADC_VREF = 3.3;
const int ADC_BITS = 12;
const int ADC_MAX = 4095;

// 初期値。scripts/03_convert_ltspice_csv_to_calibration.py の結果を見て調整。
int ADC_WARN_HIGH = 3000;
int ADC_ALARM_HIGH = 3500;
int ADC_WARN_LOW = 100;
int ADC_ALARM_LOW = 50;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastPublishMs = 0;
bool forcedAlarm = false;

void connectWiFi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi IP=");
  Serial.println(WiFi.localIP());
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String cmd;
  for (unsigned int i = 0; i < length; i++) cmd += (char)payload[i];
  cmd.trim();

  if (cmd == "ALARM_ON") forcedAlarm = true;
  if (cmd == "ALARM_OFF") forcedAlarm = false;
  if (cmd == "LED_ON") digitalWrite(LED_PIN, HIGH);
  if (cmd == "LED_OFF") digitalWrite(LED_PIN, LOW);

  Serial.print("CMD=");
  Serial.println(cmd);
}

void connectMQTT() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);

  while (!mqtt.connected()) {
    Serial.print("Connecting MQTT...");
    String clientId = String("wokwi-") + DEVICE_ID + "-" + String(random(0xffff), HEX);
    bool ok = mqtt.connect(clientId.c_str(), TOPIC_STATUS, 0, true, "offline");

    if (ok) {
      Serial.println("connected");
      mqtt.publish(TOPIC_STATUS, "online", true);
      mqtt.subscribe(TOPIC_CMD);
    } else {
      Serial.print("failed rc=");
      Serial.println(mqtt.state());
      delay(1000);
    }
  }
}

void publishTelemetry() {
  int adcRaw = analogRead(ADC_PIN);
  float voltage = ((float)adcRaw / ADC_MAX) * ADC_VREF;

  bool warn = adcRaw >= ADC_WARN_HIGH || adcRaw <= ADC_WARN_LOW;
  bool alarm = forcedAlarm || adcRaw >= ADC_ALARM_HIGH || adcRaw <= ADC_ALARM_LOW;

  digitalWrite(LED_PIN, alarm ? HIGH : LOW);
  if (alarm) {
    tone(BUZZER_PIN, 2000, 100);
  } else {
    noTone(BUZZER_PIN);
  }

  char payload[384];
  snprintf(payload, sizeof(payload),
    "{\"device\":\"%s\",\"site\":\"lab\",\"line\":\"demo\",\"machine\":\"adc_demo\","
    "\"adc_raw\":%d,\"voltage\":%.3f,\"warn\":%s,\"alarm\":%s,"
    "\"adc_vref\":%.2f,\"adc_bits\":%d,\"source\":\"wokwi_adc\",\"uptime_ms\":%lu}",
    DEVICE_ID, adcRaw, voltage,
    warn ? "true" : "false",
    alarm ? "true" : "false",
    ADC_VREF, ADC_BITS, millis()
  );

  mqtt.publish(TOPIC_TELEMETRY, payload);
  Serial.println(payload);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  analogReadResolution(ADC_BITS);
  connectWiFi();
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqtt.connected()) connectMQTT();

  mqtt.loop();

  if (millis() - lastPublishMs >= 2000) {
    lastPublishMs = millis();
    publishTelemetry();
  }
}
