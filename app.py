import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}

EXCLUDED_DOMAINS = [
    "instagram.com", "twitter.com", "facebook.com", "linkedin.com",
    "pinterest.com", "youtube.com", "ads.com", "doubleclick.net", "googlesyndication.com"
]

MAX_RETRIES = 3

# 초기 상태 설정
if "visited" not in st.session_state:
    st.session_state["visited"] = set()

if "to_visit" not in st.session_state:
    st.session_state["to_visit"] = []

def fetch_page_content(url):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException:
            pass
    return None

def clean_text(text):
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{1,2} [A-Za-z]+ \d{4}\b"
    ]
    for pattern in date_patterns:
        text = re.sub(pattern, "", text)
    return text.strip()

def extract_internal_links(base_url, html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    base_domain = urlparse(base_url).netloc
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        if parsed_url.netloc == base_domain and not any(excluded in parsed_url.netloc for excluded in EXCLUDED_DOMAINS):
            links.append(full_url)
    return list(set(links))

def scrape_page_content(url):
    html_content = fetch_page_content(url)
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.title.string if soup.title else "No Title"
    body = clean_text(soup.get_text(separator='\n').strip())
    return {"url": url, "title": title, "content": body}

def crawl_site(base_url, max_pages=100000):
    st.session_state["to_visit"].append(base_url)
    scraped_data = []

    while st.session_state["to_visit"] and len(scraped_data) < max_pages:
        current_url = st.session_state["to_visit"].pop(0)
        if current_url in st.session_state["visited"]:
            continue
        st.session_state["visited"].add(current_url)
        st.info(f"크롤링 중: {current_url}")
        page_data = scrape_page_content(current_url)
        if page_data:
            scraped_data.append(page_data)
            new_links = extract_internal_links(base_url, fetch_page_content(current_url))
            for link in new_links:
                if link not in st.session_state["visited"] and link not in st.session_state["to_visit"]:
                    st.session_state["to_visit"].append(link)
    return scraped_data

def save_to_txt(scraped_data, output_path):
    with open(output_path, "w", encoding="utf-8") as file:
        for item in scraped_data:
            file.write(f"URL: {item['url']}\n")
            file.write(f"Title: {item['title']}\n")
            file.write(f"Content:\n{item['content']}\n")
            file.write("="*50 + "\n")

def save_to_json(scraped_data, output_path):
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(scraped_data, file, ensure_ascii=False, indent=4)

st.title("사이트 전체 크롤링 및 데이터 저장")

base_url = st.text_input("기본 URL을 입력하세요", value="https://example.com")
max_pages = st.number_input("최대 크롤링 페이지 수", min_value=1, max_value=100000, value=100000)

if st.button("크롤링 시작"):
    if not base_url:
        st.error("기본 URL을 입력하세요.")
    else:
        st.info("크롤링을 시작합니다. 잠시만 기다려주세요...")
        scraped_data = crawl_site(base_url, max_pages=max_pages)
        if not scraped_data:
            st.warning("크롤링된 데이터가 없습니다.")
        else:
            os.makedirs("output", exist_ok=True)
            txt_path = os.path.join("output", "scraped_data.txt")
            json_path = os.path.join("output", "scraped_data.json")
            save_to_txt(scraped_data, txt_path)
            save_to_json(scraped_data, json_path)
            st.success("크롤링 완료!")
            st.write(f"크롤링된 페이지 수: {len(scraped_data)}")
            st.download_button("TXT 파일 다운로드", open(txt_path, "rb"), "scraped_data.txt")
            st.download_button("JSON 파일 다운로드", open(json_path, "rb"), "scraped_data.json")
