import os
import json
import re
import pandas as pd
import docx
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from openai import OpenAI

# --- Initialize OpenAI client (uses OPENAI_API_KEY from env) ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


# ============================================================
# 📂 FILE READERS
# ============================================================
def _read_text_from_docx(file_path):
    """Extract text from a Word document."""
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])


def _read_text_from_excel(file_path):
    """Extract text from all cells in an Excel file."""
    df = pd.read_excel(file_path)
    return "\n".join(df.astype(str).apply(lambda x: " ".join(x), axis=1))


def _read_text_from_html(file_path):
    """Extract visible text from an HTML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    return soup.get_text(separator="\n")


def _read_text_from_pdf(file_path):
    """Extract text from all pages of a PDF."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text


def read_text_auto(file_path):
    """Automatically detect and read supported file types."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        return _read_text_from_pdf(file_path)
    elif ext == ".docx":
        return _read_text_from_docx(file_path)
    elif ext in [".xls", ".xlsx"]:
        return _read_text_from_excel(file_path)
    elif ext in [".html", ".htm"]:
        return _read_text_from_html(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ============================================================
# 🌍 LANGUAGE TRANSLATION
# ============================================================
def translate_to_english(text):
    """Translate non-English text to English using Google Translator."""
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except Exception:
        return text  # Fallback: return original if translation fails


# ============================================================
# 🤖 RISK EXTRACTION
# ============================================================
def extract_red_flags(text, use_gpt=True):
    """
    Extract AML/CFT red flags, risk indicators, and summaries
    using GPT-4.1 if available, else fallback to keyword heuristics.
    """
    text = translate_to_english(text[:8000])  # Translate & trim

    extracted = []
    risk_keywords = [
        "money laundering", "terrorism financing", "suspicious transaction",
        "kyc", "aml", "risk assessment", "high-risk", "threshold", "alert",
        "structuring", "fraud", "sanction", "shell company", "beneficial owner",
        "wire transfer", "cross-border", "politically exposed", "bribery",
        "corruption", "tax evasion", "hawala", "unusual transaction",
        "cash deposit", "front company", "smurfing", "layering", "integration"
    ]

    # --- Heuristic Extraction ---
    for kw in risk_keywords:
        if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
            extracted.append(kw)

    structured = {"risks": extracted, "summary": ""}

    # --- AI Extraction (GPT-4.1) ---
    if use_gpt and os.getenv("OPENAI_API_KEY"):
        try:
            prompt = f"""
            You are an AML risk analysis assistant.
            From the text below, extract potential AML/CFT risks and provide a short summary.
            Respond strictly in JSON with keys: "risks" (list of risk names) and "summary" (paragraph).
            
            Text:
            {text[:7000]}
            """

            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            # print(response)  # Debug log

            content = response.choices[0].message.content.strip()
            
            print(content)
            print(type(content))

            # Some models return extra newlines or markdown
            content = content.replace("```json", "").replace("```", "").strip()
            structured = json.loads(content)
            print(structured)  # Debug log

        except Exception as e:
            structured["summary"] = f"GPT fallback due to error: {e}"

    # --- Safe Merge (Fix for 'unhashable type: dict') ---
    structured["risks"] = list(
        set(
            [
                r["risk"] if isinstance(r, dict) else str(r)
                for r in structured.get("risks", []) + extracted
                if r
            ]
        )
    )

    return {
        "structured": structured,
        "extracted_phrases": structured["risks"]
    }


# ============================================================
# ✅ MAIN (for standalone testing)
# ============================================================
if __name__ == "__main__":
    sample_file = "data/raw/fatf_report.txt"
    if os.path.exists(sample_file):
        text = read_text_auto(sample_file)
        result = extract_red_flags(text)
        print(json.dumps(result, indent=2))
    else:
        print("Sample file not found:", sample_file)
