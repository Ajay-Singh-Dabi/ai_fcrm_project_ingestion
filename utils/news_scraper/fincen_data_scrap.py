import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import os
import time
import fitz  # PyMuPDF

# === Config ===
BASE_URL = "https://www.fincen.gov/news?page={}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_PAGES = 10
OUTPUT_FILE = "fincen_news.txt"

START_DATE = datetime.strptime("2025-09-01", "%Y-%m-%d")
END_DATE = datetime.strptime("2025-11-05", "%Y-%m-%d")

# === Helper: Extract text from PDF URL ===
def extract_pdf_text(pdf_url):
    try:
        print(f"📄 Extracting text from PDF: {pdf_url}")
        resp = requests.get(pdf_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return f"[⚠️ Failed to download PDF: {pdf_url}]"
        pdf_data = resp.content

        text = ""
        with fitz.open(stream=pdf_data, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
        return text.strip() or "[⚠️ No text found in PDF]"
    except Exception as e:
        return f"[⚠️ Error reading PDF {pdf_url}: {e}]"

# === Step 1: Collect FinCEN news links ===
print("🔍 Collecting FinCEN news release links...")
all_links = set()

for page in range(MAX_PAGES):
    url = BASE_URL.format(page)
    print(f"🌐 Visiting: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Skipping {url} (Status: {resp.status_code})")
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            all_links.add(full_url)
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Error at {url}: {e}")

news_releases = sorted(
    link for link in all_links if link.startswith("https://www.fincen.gov/news/news-releases/")
)
print(f"\n📰 Total news releases found: {len(news_releases)}\n")

# === Step 2: Extract each news article ===
def extract_fincen_content(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    title_elem = soup.select_one("h1 span.treas-page-title")
    title = title_elem.get_text(strip=True) if title_elem else "N/A"

    date_elem = soup.select_one(".field--name-field-date-release time")
    date_str = date_elem.get_text(strip=True) if date_elem else None
    try:
        release_date = datetime.strptime(date_str, "%B %d, %Y") if date_str else None
    except:
        release_date = None

    body_elem = soup.select_one(".field--name-body")
    body_text = body_elem.get_text("\n", strip=True) if body_elem else ""

    # Find all PDF links
    pdf_links = []
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".pdf"):
            pdf_links.append(urljoin(url, a["href"]))

    return {
        "url": url,
        "title": title,
        "release_date": release_date,
        "body": body_text,
        "pdfs": pdf_links
    }

# === Step 3: Save all results in one text file ===
os.makedirs("data", exist_ok=True)
output_path = os.path.join("data", OUTPUT_FILE)

with open(output_path, "w", encoding="utf-8") as f_out:
    total_saved = 0

    for url in news_releases:
        try:
            data = extract_fincen_content(url)
            rd = data["release_date"]

            if rd and START_DATE <= rd <= END_DATE:
                total_saved += 1
                date_str = rd.strftime("%Y-%m-%d")

                f_out.write(f"==== {total_saved}. {data['title']} ====\n")
                f_out.write(f"📅 Date: {date_str}\n")
                f_out.write(f"🔗 URL: {data['url']}\n\n")
                f_out.write(f"{data['body']}\n\n")

                # Append PDFs if present
                for pdf_url in data["pdfs"]:
                    pdf_text = extract_pdf_text(pdf_url)
                    f_out.write(f"\n📎 PDF: {pdf_url}\n")
                    f_out.write(f"{pdf_text}\n\n")

                f_out.write("="*120 + "\n\n")
                print(f"✅ Added: {data['title']} ({date_str})")

        except Exception as e:
            print(f"⚠️ Failed to scrape {url}: {e}")

print(f"\n✅ All done! {total_saved} articles (with PDF content) saved to: {output_path}")
