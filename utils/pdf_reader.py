import io
import pdfplumber

def read_text_from_file(uploaded_file):
    """
    Accepts a Streamlit uploaded file or a local file path and returns extracted text.
    """
    try:
        content = uploaded_file.read()
        if content[:4] == b'%PDF':
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
        else:
            try:
                return content.decode('utf-8')
            except Exception:
                return content.decode('latin-1')
    except Exception:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
        except Exception:
            with open(uploaded_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
