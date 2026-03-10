import pypdf
import sys

def extract_text(pdf_path, output_path):
    try:
        reader = pypdf.PdfReader(pdf_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                f.write(f"--- PAGE {i+1} ---\n")
                f.write(text + "\n\n")
        print(f"Successfully extracted text to {output_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    extract_text(sys.argv[1], sys.argv[2])
