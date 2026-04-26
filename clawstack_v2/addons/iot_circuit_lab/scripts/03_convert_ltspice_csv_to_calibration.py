#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# LTspice CSV -> ADC calibration JSON
#
# Example:
# python scripts/03_convert_ltspice_csv_to_calibration.py --input ltspice/exported_waveforms/sample_sensor_waveform.csv --voltage-column v_adc --vref 3.3 --adc-bits 12 --output wokwi/calibration/adc_calibration.generated.json

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--voltage-column", default="v_adc")
    ap.add_argument("--vref", type=float, default=3.3)
    ap.add_argument("--adc-bits", type=int, default=12)
    ap.add_argument("--output", required=True)
    return ap.parse_args()

def to_float(x):
    if x is None:
        return None
    s = str(x).strip().replace("V", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    adc_max = (2 ** args.adc_bits) - 1

    rows = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if args.voltage_column not in reader.fieldnames:
            raise SystemExit(f"Voltage column '{args.voltage_column}' not found. columns={reader.fieldnames}")
        for row in reader:
            v = to_float(row.get(args.voltage_column))
            if v is not None:
                rows.append(v)

    if not rows:
        raise SystemExit("No valid voltage data found.")

    def adc_count(v):
        return max(0, min(adc_max, round((v / args.vref) * adc_max)))

    adc_values = [adc_count(v) for v in rows]

    min_v, max_v, mean_v = min(rows), max(rows), mean(rows)
    min_adc, max_adc, mean_adc = min(adc_values), max(adc_values), round(mean(adc_values))

    warn_high = min(adc_max, max(0, round(max_adc * 0.90)))
    alarm_high = min(adc_max, max(warn_high + 1, round(max_adc * 0.97)))
    warn_low = max(0, round(min_adc + (max_adc - min_adc) * 0.03))
    alarm_low = max(0, round(min_adc + (max_adc - min_adc) * 0.01))

    result = {
        "source_csv": str(input_path),
        "voltage_column": args.voltage_column,
        "vref": args.vref,
        "adc_bits": args.adc_bits,
        "adc_max": adc_max,
        "stats": {
            "samples": len(rows),
            "min_voltage": min_v,
            "max_voltage": max_v,
            "mean_voltage": mean_v
        },
        "adc_counts": {
            "min": min_adc,
            "max": max_adc,
            "mean": mean_adc
        },
        "suggested_thresholds": {
            "warn_high_adc": warn_high,
            "alarm_high_adc": alarm_high,
            "warn_low_adc": warn_low,
            "alarm_low_adc": alarm_low
        },
        "wokwi_cpp_snippet": {
            "ADC_WARN_HIGH": warn_high,
            "ADC_ALARM_HIGH": alarm_high,
            "ADC_WARN_LOW": warn_low,
            "ADC_ALARM_LOW": alarm_low
        },
        "notes": [
            "しきい値は自動案です。実機のノイズ、管理幅、安全要求に合わせて調整してください。",
            "ESP32 ADCは直線性・精度に限界があるため、必要に応じて実測校正してください。"
        ]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
