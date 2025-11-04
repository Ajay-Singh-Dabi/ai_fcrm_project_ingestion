import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import time
import os

BASE_URL = "https://www.dfs.ny.gov/reports_and_publications/press_releases/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_FILE = "dfs_press_releases_content.txt"

# Date range filter
START_DATE = datetime.strptime("2025-09-01", "%Y-%m-%d")
END_DATE = datetime.strptime("2025-11-05", "%Y-%m-%d")


def get_press_release_links(max_pages=50):
    """Collect all press release links from paginated press release listing."""
    all_links = set()

    for page in range(max_pages):
        url = f"{BASE_URL}?page={page}"
        print(f"🌐 Scanning {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"⚠️ Skipping {url} (Status: {resp.status_code})")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("/reports_and_publications/press_releases/pr"):
                    full_url = urljoin(BASE_URL, href)
                    all_links.add(full_url)

            print(f"✅ Found {len(all_links)} total links so far.")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error at {url}: {e}")
            continue

    return sorted(all_links)


def extract_press_release_content(url):
    """Extract title, subtitle, date, and body text from each DFS press release."""
    print(f"📰 Extracting: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"⚠️ Failed to fetch {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_elem = soup.select_one(".field--name-field-heading")
    title = title_elem.get_text(strip=True) if title_elem else "N/A"

    # Subtitle
    subtitle_elem = soup.select_one(".field--name-field-sub-heading")
    subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""

    # Date
    date_elem = soup.select_one(".field--name-published-at time")
    date_text = date_elem.get_text(strip=True) if date_elem else None
    release_date = None
    try:
        if date_text:
            release_date = datetime.strptime(date_text, "%B %d, %Y")
        date_str = release_date.strftime("%Y-%m-%d") if release_date else "N/A"
    except Exception:
        date_str = "N/A"

    # Body
    body_elem = soup.select_one(".field--name-body")
    body_text = body_elem.get_text("\n", strip=True) if body_elem else ""

    # Skip if date not in range
    if not release_date or not (START_DATE <= release_date <= END_DATE):
        print(f"⏭️ Skipped (Out of range): {date_str}")
        return None

    return {
        "url": url,
        "title": title,
        "subtitle": subtitle,
        "date": date_str,
        "body": body_text,
    }


def main():
    os.makedirs("data", exist_ok=True)

    links = get_press_release_links(max_pages=5)
    print(f"\n🔗 Total press release links collected: {len(links)}\n")

    all_results = []
    with open(os.path.join("data", OUTPUT_FILE), "w", encoding="utf-8") as f:
        for i, url in enumerate(links, start=1):
            try:
                data = extract_press_release_content(url)
                if not data:
                    continue

                all_results.append(data)

                f.write(f"==== {i}. {data['title']} ====\n")
                f.write(f"📅 Date: {data['date']}\n")
                f.write(f"🔗 URL: {data['url']}\n")
                if data['subtitle']:
                    f.write(f"🧾 Subtitle: {data['subtitle']}\n")
                f.write("\n" + data['body'] + "\n\n")
                f.write("=" * 80 + "\n\n")

                print(f"✅ Saved: {data['title'][:80]}...")
                time.sleep(1)

            except Exception as e:
                print(f"⚠️ Error processing {url}: {e}")

    print(f"\n✅ All content saved to: data/{OUTPUT_FILE}")
    print(f"🗞️ Total articles extracted (in range): {len(all_results)}")


if __name__ == "__main__":
    main()
