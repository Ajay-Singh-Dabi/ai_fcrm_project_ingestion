import requests
from bs4 import BeautifulSoup
import os, io, tempfile
import pdfplumber

def fetch_fatf_reports(limit=10):
    """
    Fetches recent FATF publications that link to PDFs. Returns list of dicts with title and url.
    """
    base = "https://www.fatf-gafi.org"
    list_url = "https://www.fatf-gafi.org/en/publications.html"
    resp = requests.get(list_url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    reports = []
    # FATF lists publication links; find anchors containing .pdf
    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.lower().endswith(".pdf"):
            title = a.get_text(strip=True) or os.path.basename(href)
            url = href if href.startswith("http") else base + href
            reports.append({"title": title, "url": url})
            if len(reports) >= limit:
                break
    return reports

def download_and_extract_pdf_text(url):
    """
    Downloads PDF from url and extracts text using pdfplumber. Returns combined text.
    """
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpf:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                tmpf.write(chunk)
        tmpf.flush()
        tmp_path = tmpf.name
    try:
        with pdfplumber.open(tmp_path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        return "\\n".join(pages)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
