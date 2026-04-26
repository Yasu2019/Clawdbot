try:
    import pdfplumber
    print("pdfplumber is installed")
except ImportError:
    print("pdfplumber is not installed")

try:
    import PyPDF2
    print("PyPDF2 is installed")
except ImportError:
    print("PyPDF2 is not installed")

try:
    import fitz # PyMuPDF
    print("PyMuPDF (fitz) is installed")
except ImportError:
    print("PyMuPDF is not installed")
