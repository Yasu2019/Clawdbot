import pdfplumber
import os

pdf_path = r"D:\Clawdbot_Docker_20260125\iatf_system\db\documents\IATF 16949 内部監査資料_箇条8.5.1.5 TPM_IATF 16949  Total Productive Maintenance (TPM) Process.pdf"
output_path = r"D:\Clawdbot_Docker_20260125\scratch\tpm_script.txt"

print(f"Opening PDF: {pdf_path}")

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    # Try alternative with single space just in case
    pdf_path = pdf_path.replace("  ", " ")
    if not os.path.exists(pdf_path):
        print(f"Error: File also not found at {pdf_path}")
        exit(1)

try:
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(all_text)
    print(f"Successfully extracted text to {output_path}")
except Exception as e:
    print(f"An error occurred: {e}")
