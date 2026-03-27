import io
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
from PIL import Image


# ── PDF ──────────────────────────────────────────────────────────────────────
def extract_pdf_text(file) -> str:
    """
    Extract text from uploaded PDF (Streamlit UploadedFile).
    """
    try:
        file_bytes = file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        text = ""
        for page in doc:
            text += page.get_text()

        return text.strip()

    except Exception as e:
        print(f"⚠️ PDF extraction failed: {e}")
        return ""


# ── CSV ──────────────────────────────────────────────────────────────────────
def extract_csv(file) -> dict:
    """
    Extract structured info from CSV.
    Returns columns + small sample (safe for LLM context).
    """
    try:
        df = pd.read_csv(file)

        return {
            "columns": list(df.columns),
            "rows_sample": df.head(5).to_dict(orient="records"),
            "row_count": len(df),
        }

    except Exception as e:
        print(f"⚠️ CSV extraction failed: {e}")
        return {}


# ── IMAGE OCR ────────────────────────────────────────────────────────────────
def extract_image_text(file) -> str:
    """
    Extract text from images using OCR (Tesseract).
    """
    try:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
        return text.strip()

    except Exception as e:
        print(f"⚠️ Image OCR failed: {e}")
        return ""


# ── RECORD BUILDING ──────────────────────────────────────────────────────────
def build_doc_record(text: str) -> dict:
    """
    Convert extracted text into JSONL-compatible record.
    Keeps text bounded to avoid LLM overflow.
    """
    return {
        "type": "user_document",
        "text": text[:3000] if text else "",
    }