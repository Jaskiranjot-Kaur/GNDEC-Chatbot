from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.text

def links_from_page(url: str):
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    out = []
    
    for a in soup.find_all("a"):
        text = a.get_text(" ", strip=True)
        href = a.get("href")
        
        # We removed the '#' from the ignore list so it grabs the Table of Contents
        if not href or href.startswith(('javascript:', 'mailto:')):
            continue
            
        # If it's an anchor link (like #D2_CS_A), attach it directly to the URL
        if href.startswith('#'):
            full_url = url + href
        else:
            full_url = urljoin(url, href)
            
        out.append({"title": text, "url": full_url})
        
    return out