@echo off
cd /d "%~dp0"
python scripts\03_convert_ltspice_csv_to_calibration.py --input ltspice\exported_waveforms\sample_sensor_waveform.csv --voltage-column v_adc --vref 3.3 --adc-bits 12 --output wokwi\calibration\adc_calibration.generated.json
pause
