# 파일명: universal_text_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep
import re
from urllib.parse import urljoin, urlparse

# User-Agent 설정
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}

# 최대 재시도 횟수
MAX_RETRIES = 3

# 제외할 도메인 패턴 (SNS 등)
EXCLUDED_DOMAINS = [
    "instagram.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
    "pinterest.com",
    "youtube.com"
]

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

def extract_all_links(soup, base_url):
    """HTML 페이지에서 모든 링크를 추출."""
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        links.append(full_url)
    return links

def filter_links(links, base_url):
    """SNS 및 외부 링크를 제외한 내부 링크만 필터링."""
    base_domain = urlparse(base_url).netloc
    filtered_links = []
    for link in links:
        parsed_link = urlparse(link)
        if parsed_link.netloc == base_domain or not parsed_link.netloc:
            filtered_links.append(link)
        elif not any(excluded in parsed_link.netloc for excluded in EXCLUDED_DOMAINS):
            filtered_links.append(link)
    return list(set(filtered_links))  # 중복 제거

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

def scrape_content_from_links(base_url, links):
    """주어진 링크에서 텍스트 콘텐츠를 크롤링."""
    scraped_data = []
    for link in links:
        page_content = fetch_page_content(link)
        if not page_content:
            continue

        soup = BeautifulSoup(page_content, 'html.parser')
        title = soup.title.string if soup.title else "No Title"
        body = clean_text(soup.get_text(separator='\n').strip())
        
        scraped_data.append({
            "url": link,
            "title": title,
            "content": body
        })
    return scraped_data

def save_to_txt(scraped_data, output_path):
    """크롤링한 텍스트 데이터를 txt로 저장."""
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
st.title("모든 사이트 크롤링 및 텍스트 저장")

# 입력
base_url = st.text_input("크롤링할 기본 URL을 입력하세요", value="https://example.com")

if st.button("크롤링 시작"):
    # HTML 콘텐츠 가져오기
    main_page_content = fetch_page_content(base_url)
    if not main_page_content:
        st.stop()

    # BeautifulSoup을 사용해 HTML 파싱
    soup = BeautifulSoup(main_page_content, 'html.parser')

    # 모든 링크 추출 및 필터링
    all_links = extract_all_links(soup, base_url)
    filtered_links = filter_links(all_links, base_url)
    st.write(f"**추출된 링크 수:** {len(filtered_links)}")

    # 링크에서 텍스트 데이터 크롤링
    scraped_data = scrape_content_from_links(base_url, filtered_links)

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
