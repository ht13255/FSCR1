# 파일명: streamlit_web_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse
import re

# User-Agent 설정
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}

# 제외할 도메인 패턴 (SNS 및 광고 등)
EXCLUDED_DOMAINS = [
    "instagram.com", "twitter.com", "facebook.com", "linkedin.com",
    "pinterest.com", "youtube.com", "ads.com", "doubleclick.net", "googlesyndication.com"
]

# 최대 재시도 횟수
MAX_RETRIES = 3


def fetch_page_content(url):
    """주어진 URL의 HTML 콘텐츠를 가져오는 함수."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            st.warning(f"URL 요청 실패 ({url}): {e}")
    return None


def clean_text(text):
    """텍스트에서 날짜 및 불필요한 패턴 제거."""
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
        r"\b\d{2}/\d{2}/\d{4}\b",  # DD/MM/YYYY
        r"\b\d{1,2} [A-Za-z]+ \d{4}\b"  # DD Month YYYY
    ]
    for pattern in date_patterns:
        text = re.sub(pattern, "", text)
    return text.strip()


def extract_internal_links(base_url, html_content):
    """HTML 페이지에서 내부 링크만 추출."""
    soup = BeautifulSoup(html_content, 'html.parser')
    base_domain = urlparse(base_url).netloc

    all_links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        # 내부 링크만 필터링
        if parsed_url.netloc == base_domain and not any(excluded in parsed_url.netloc for excluded in EXCLUDED_DOMAINS):
            all_links.append(full_url)

    # 중복 제거
    return list(set(all_links))


def scrape_page_content(url):
    """URL에서 텍스트 콘텐츠를 크롤링."""
    html_content = fetch_page_content(url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.title.string if soup.title else "No Title"
    body = clean_text(soup.get_text(separator='\n').strip())
    return {"url": url, "title": title, "content": body}


def crawl_site(base_url, max_pages=100000):
    """사이트 전체 크롤링."""
    visited = set()
    to_visit = [base_url]
    scraped_data = []

    while to_visit and len(scraped_data) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue

        st.info(f"크롤링 중: {current_url}")
        visited.add(current_url)

        # 현재 페이지 크롤링
        page_content = scrape_page_content(current_url)
        if page_content:
            scraped_data.append(page_content)

            # 현재 페이지에서 내부 링크 추출
            new_links = extract_internal_links(base_url, fetch_page_content(current_url))
            for link in new_links:
                if link not in visited and link not in to_visit:
                    to_visit.append(link)

    return scraped_data


def save_to_txt(scraped_data, output_path):
    """크롤링한 데이터를 txt로 저장."""
    with open(output_path, "w", encoding="utf-8") as file:
        for item in scraped_data:
            file.write(f"URL: {item['url']}\n")
            file.write(f"Title: {item['title']}\n")
            file.write(f"Content:\n{item['content']}\n")
            file.write("="*50 + "\n")


def save_to_json(scraped_data, output_path):
    """크롤링한 데이터를 json으로 저장."""
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(scraped_data, file, ensure_ascii=False, indent=4)


# Streamlit App 시작
st.title("내부 링크만 크롤링 및 데이터 저장 (최대 100,000개)")

# 입력
base_url = st.text_input("기본 URL을 입력하세요", value="https://example.com")
max_pages = st.number_input("최대 크롤링 페이지 수", min_value=1, max_value=100000, value=100000)

if st.button("크롤링 시작"):
    if not base_url:
        st.error("기본 URL을 입력하세요.")
    else:
        st.info("크롤링을 시작합니다. 잠시만 기다려주세요...")

        # 사이트 전체 크롤링
        scraped_data = crawl_site(base_url, max_pages=max_pages)

        if not scraped_data:
            st.warning("크롤링된 데이터가 없습니다.")
        else:
            # 데이터 저장
            os.makedirs("output", exist_ok=True)
            txt_path = os.path.join("output", "scraped_data.txt")
            json_path = os.path.join("output", "scraped_data.json")
            save_to_txt(scraped_data, txt_path)
            save_to_json(scraped_data, json_path)

            # 결과 표시
            st.success("크롤링 완료!")
            st.write(f"크롤링된 페이지 수: {len(scraped_data)}")
            st.write("크롤링된 데이터 (최대 5개 미리보기):", scraped_data[:5])
            st.download_button("TXT 파일 다운로드", open(txt_path, "rb"), "scraped_data.txt")
            st.download_button("JSON 파일 다운로드", open(json_path, "rb"), "scraped_data.json")
