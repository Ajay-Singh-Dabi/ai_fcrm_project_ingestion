import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import os
import time
from io import BytesIO
from pdfminer.high_level import extract_text

BASE_URL = "https://www.federalreserve.gov/newsevents/pressreleases.htm"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---- Define Date Range ----
START_DATE = datetime.strptime("2025-09-01", "%Y-%m-%d")
END_DATE = datetime.strptime("2025-11-05", "%Y-%m-%d")

# ---- Output ----
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "federal_reserve_press_releases.txt")

def get_yearly_press_pages():
    """Get yearly press release list pages (like 2025-press.htm)."""
    current_year = str(datetime.now().year)
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    yearly_pages = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(f"/newsevents/pressreleases/{current_year}-press.htm"):
            full_url = urljoin(BASE_URL, href)
            yearly_pages.append(full_url)

    return sorted(set(yearly_pages))

def get_press_links_from_page(page_url):
    """Extract all press release links from a yearly page."""
    resp = requests.get(page_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("/newsevents/pressreleases/") and href.endswith(".htm"):
            links.append(urljoin(page_url, href))
    return sorted(set(links))

def extract_pdf_text(pdf_url):
    """Download and extract text from a PDF."""
    try:
        print(f"   📄 Extracting text from PDF: {pdf_url}")
        resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        pdf_text = extract_text(BytesIO(resp.content))
        return pdf_text.strip()
    except Exception as e:
        print(f"   ⚠️ Failed to extract PDF text from {pdf_url}: {e}")
        return ""

def extract_press_release_details(url):
    """Extract title, date, text, and PDF links (and extract PDF content too)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ---- Extract date ----
        date_tag = soup.find("p", class_="article__time")
        date_text = date_tag.get_text(strip=True) if date_tag else None
        if not date_text:
            return None

        try:
            pub_date = datetime.strptime(date_text, "%B %d, %Y")
        except ValueError:
            return None

        # ---- Check date range ----
        if not (START_DATE <= pub_date <= END_DATE):
            return None

        # ---- Extract title ----
        title_tag = soup.find("h3", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"

        # ---- Extract webpage content ----
        paragraphs = []
        for p in soup.select("#article p"):
            text = p.get_text(" ", strip=True)
            if text and "For release" not in text:
                paragraphs.append(text)
        content = "\n\n".join(paragraphs)

        # ---- Extract PDFs and read their content ----
        pdf_links = [
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if a["href"].lower().endswith(".pdf")
        ]

        pdf_content = ""
        for pdf_link in pdf_links:
            pdf_content += f"\n\n--- PDF: {pdf_link} ---\n"
            pdf_content += extract_pdf_text(pdf_link)

        # ---- Combine all content ----
        combined_content = f"{content}\n\n{pdf_content.strip()}"

        # ---- Append to single file ----
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write("="*120 + "\n")
            f.write(f"Title: {title}\n")
            f.write(f"Date: {pub_date.strftime('%Y-%m-%d')}\n")
            f.write(f"URL: {url}\n")
            if pdf_links:
                f.write("\nPDF Links:\n")
                for link in pdf_links:
                    f.write(f"- {link}\n")
            f.write("\n\nContent:\n")
            f.write(combined_content)
            f.write("\n\n")

        print(f"✅ Appended: {title}")
        return True

    except Exception as e:
        print(f"❌ Error parsing {url}: {e}")
        return False

if __name__ == "__main__":
    # Clear file if already exists
    open(OUTPUT_FILE, "w", encoding="utf-8").close()

    yearly_pages = get_yearly_press_pages()
    all_links = []
    for page in yearly_pages:
        print(f"\n🔗 Fetching from: {page}")
        press_links = get_press_links_from_page(page)
        all_links.extend(press_links)

    print(f"\n📰 Found {len(all_links)} total press release links")
    print(f"\n📅 Filtering and saving articles between {START_DATE.date()} and {END_DATE.date()}")

    for link in all_links:
        extract_press_release_details(link)
        time.sleep(0.5)  # gentle delay for server

    print(f"\n🎯 Extraction complete. All saved in: {OUTPUT_FILE}")
