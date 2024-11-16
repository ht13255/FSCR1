# 파일명: streamlit_web_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep
from collections import Counter
from PIL import Image, ImageOps
from io import BytesIO
import re
from urllib.parse import urlparse

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

def analyze_page_structure(html_content):
    """HTML 페이지에서 태그, 클래스, ID를 분석하여 선택자를 자동 생성."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 태그 카운트
    tags = [tag.name for tag in soup.find_all()]
    tag_count = Counter(tags)

    # 클래스 카운트
    classes = [
        class_name for tag in soup.find_all(class_=True)
        for class_name in tag.get('class', [])
    ]
    class_count = Counter(classes)

    # ID 카운트
    ids = [tag.get('id') for tag in soup.find_all(id=True)]
    id_count = Counter(ids)

    # 가장 빈번한 태그, 클래스, ID를 선택
    most_common_tag = tag_count.most_common(1)[0][0] if tag_count else None
    most_common_class = class_count.most_common(1)[0][0] if class_count else None
    most_common_id = id_count.most_common(1)[0][0] if id_count else None

    return most_common_tag, most_common_class, most_common_id

def generate_css_selector(tag, class_name, id_name):
    """태그, 클래스, ID를 기반으로 CSS 선택자를 생성."""
    selector = ""
    if tag:
        selector = tag
    if class_name:
        selector += f".{class_name}" if selector else f".{class_name}"
    if id_name:
        selector += f"#{id_name}" if selector else f"#{id_name}"
    return selector

def extract_all_links(soup):
    """HTML 페이지에서 가능한 모든 링크를 추출."""
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    return links

def filter_links(base_url, links):
    """SNS 및 외부 링크를 제외한 내부 링크만 필터링."""
    filtered_links = []
    base_domain = urlparse(base_url).netloc

    for link in links:
        parsed_link = urlparse(link)
        # 상대 링크 처리
        if not parsed_link.netloc:
            filtered_links.append(link)
        # 동일 도메인 확인
        elif parsed_link.netloc == base_domain:
            filtered_links.append(link)
        # SNS 및 제외 대상 확인
        elif not any(excluded in parsed_link.netloc for excluded in EXCLUDED_DOMAINS):
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

def process_image(image_url):
    """이미지 다운로드 후 빈칸을 제거."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img = ImageOps.crop(img)  # 이미지의 빈칸 제거
        return img
    except Exception as e:
        st.warning(f"이미지를 처리할 수 없습니다: {e}")
        return None

def scrape_content_from_links(base_url, links):
    """주어진 링크에서 텍스트 및 이미지를 크롤링."""
    scraped_data = []
    for link in links:
        full_url = base_url + link if link.startswith('/') else link
        page_content = fetch_page_content(full_url)
        if not page_content:
            continue

        soup = BeautifulSoup(page_content, 'html.parser')

        # 텍스트 데이터 처리
        title = soup.title.string if soup.title else "No Title"
        body = clean_text(soup.get_text(separator='\n').strip())

        # 이미지 처리
        images = soup.find_all('img', src=True)
        processed_images = [
            process_image(img['src']) for img in images if img['src']
        ]

        scraped_data.append({
            "url": full_url,
            "title": title,
            "content": body,
            "images": processed_images
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
st.title("날짜 제거 및 이미지 처리 웹 크롤링")

# 입력
base_url = st.text_input("기본 URL을 입력하세요", value="https://example.com")

if st.button("크롤링 시작"):
    # 페이지 콘텐츠 가져오기
    main_page_content = fetch_page_content(base_url)
    if not main_page_content:
        st.stop()

    # HTML 구조 분석
    soup = BeautifulSoup(main_page_content, 'html.parser')
    most_common_tag, most_common_class, most_common_id = analyze_page_structure(main_page_content)
    css_selector = generate_css_selector(most_common_tag, most_common_class, most_common_id)
    st.write("**자동으로 선택된 구조**")
    st.write(f"태그: {most_common_tag}, 클래스: {most_common_class}, ID: {most_common_id}")
    st.write(f"**생성된 CSS 선택자:** `{css_selector}`")

    # 가능한 모든 링크 추출
    links = soup.select(css_selector) if css_selector else extract_all_links(soup)
    if not links:
        st.warning("자동 선택된 구조에서 링크를 찾을 수 없습니다. 모든 링크를 수집합니다.")
        links = extract_all_links(soup)

    # SNS 및 외부 링크 제외
    links = filter_links(base_url, links)

    # 중복 제거 및 정리
    links = list(set(links))
    st.write(f"**필터링된 링크 수:** {len(links)}")

    # 데이터 크롤링
    scraped_data = scrape_content_from_links(base_url, links)

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
