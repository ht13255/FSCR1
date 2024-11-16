# 파일명: streamlit_web_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep
from urllib.parse import urlparse, urljoin
import re

# User-Agent 설정
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}

# 제외할 SNS 및 광고 도메인
EXCLUDED_DOMAINS = [
    "instagram.com", "twitter.com", "facebook.com", "linkedin.com", 
    "pinterest.com", "youtube.com", "ads", "doubleclick.net", "adservice.google.com"
]

# 최대 재시도 횟수
MAX_RETRIES = 3

def fetch_page_content(url):
    """주어진 URL의 HTML 콘텐츠를 가져오는 함수."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            st.warning(f"재시도 중 ({attempt + 1}/{MAX_RETRIES}): {e}")
            sleep(2)  # 재시도 전 대기
    st.error("최대 재시도 횟수를 초과했습니다.")
    return None

def extract_links(base_url, soup):
    """HTML 페이지에서 가능한 모든 링크를 추출하고 상대 URL을 절대 URL로 변환."""
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href')
        # 절대 URL로 변환
        full_url = urljoin(base_url, href)
        links.add(full_url)
    return links

def filter_links(links, base_domain):
    """SNS 및 광고 도메인을 제외한 내부 링크 필터링."""
    filtered_links = []
    for link in links:
        parsed_link = urlparse(link)
        # 동일 도메인 확인 또는 제외 도메인 필터링
        if parsed_link.netloc == base_domain or not any(excluded in link for excluded in EXCLUDED_DOMAINS):
            filtered_links.append(link)
    return filtered_links

def clean_text(text):
    """텍스트에서 날짜 및 불필요한 패턴 제거."""
    # 날짜 패턴 (YYYY-MM-DD, DD/MM/YYYY 등)
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
        r"\b\d{2}/\d{2}/\d{4}\b",  # DD/MM/YYYY
        r"\b\d{1,2} [A-Za-z]+ \d{4}\b"  # DD Month YYYY
    ]
    for pattern in date_patterns:
        text = re.sub(pattern, "", text)
    return text.strip()

def scrape_site(base_url, max_depth=2):
    """사이트 전체를 크롤링."""
    visited = set()  # 방문한 링크 추적
    to_visit = [base_url]  # 방문할 링크 큐
    scraped_data = []

    for depth in range(max_depth):
        next_to_visit = []
        for url in to_visit:
            if url in visited:
                continue
            visited.add(url)

            page_content = fetch_page_content(url)
            if not page_content:
                continue

            soup = BeautifulSoup(page_content, 'html.parser')
            title = soup.title.string if soup.title else "No Title"
            body = clean_text(soup.get_text(separator='\n').strip())

            # 페이지 데이터를 저장
            scraped_data.append({
                "url": url,
                "title": title,
                "content": body
            })

            # 링크 추출 및 필터링
            links = extract_links(base_url, soup)
            base_domain = urlparse(base_url).netloc
            filtered_links = filter_links(links, base_domain)
            next_to_visit.extend(filtered_links)

        to_visit = next_to_visit  # 다음 깊이의 링크로 이동

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
st.title("모든 사이트 텍스트 크롤링 (SNS/광고 제외)")

# 입력
base_url = st.text_input("기본 URL을 입력하세요", value="https://example.com")
max_depth = st.slider("크롤링 깊이 (Max Depth)", min_value=1, max_value=5, value=2)

if st.button("크롤링 시작"):
    # 크롤링 시작
    scraped_data = scrape_site(base_url, max_depth)

    # 데이터 저장
    os.makedirs("output", exist_ok=True)
    txt_path = os.path.join("output", "scraped_data.txt")
    json_path = os.path.join("output", "scraped_data.json")
    save_to_txt(scraped_data, txt_path)
    save_to_json(scraped_data, json_path)

    # 결과 표시
    st.success("크롤링 완료!")
    st.write("크롤링된 데이터 (최대 5개 미리보기):", scraped_data[:5])
    st.download_button("TXT 파일 다운로드", open(txt_path, "rb"), "scraped_data.txt")
    st.download_button("JSON 파일 다운로드", open(json_path, "rb"), "scraped_data.json")
