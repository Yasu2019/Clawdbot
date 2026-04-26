#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LTspice CSV -> MQTT replay
#
# Requires:
#   pip install paho-mqtt
#
# Example:
# python scripts/04_publish_ltspice_csv_to_mqtt.py --input ltspice/exported_waveforms/sample_sensor_waveform.csv --voltage-column v_adc --broker 127.0.0.1 --port 1883 --topic factory/lab/ltspice-replay-001/telemetry

import argparse
import csv
import json
import time
from pathlib import Path

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--voltage-column", default="v_adc")
    ap.add_argument("--broker", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="factory/lab/ltspice-replay-001/telemetry")
    ap.add_argument("--vref", type=float, default=3.3)
    ap.add_argument("--adc-bits", type=int, default=12)
    ap.add_argument("--delay", type=float, default=0.2)
    return ap.parse_args()

def to_float(x, default=0.0):
    try:
        return float(str(x).strip().replace("V", ""))
    except Exception:
        return default

def main():
    args = parse_args()
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        raise SystemExit("paho-mqtt is not installed. Run: pip install paho-mqtt")

    adc_max = (2 ** args.adc_bits) - 1
    client = mqtt.Client()
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            v = to_float(row.get(args.voltage_column))
            adc = max(0, min(adc_max, round((v / args.vref) * adc_max)))
            payload = {
                "device": "ltspice-replay-001",
                "site": "lab",
                "line": "demo",
                "machine": "ltspice_replay",
                "time": to_float(row.get("time")),
                "voltage": v,
                "adc_raw": adc,
                "warn": adc >= 3000 or adc <= 100,
                "alarm": adc >= 3500 or adc <= 50,
                "source": "ltspice_csv_python_replay"
            }
            client.publish(args.topic, json.dumps(payload, ensure_ascii=False))
            print(args.topic, payload)
            time.sleep(args.delay)

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
