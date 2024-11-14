# app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Streamlit 설정
st.title("동적 웹사이트 크롤러")
st.write("내부 링크를 크롤링하여 JSON 및 TXT 형식으로 저장합니다.")

# URL 입력
base_url = st.text_input("크롤링할 사이트 URL을 입력하세요 (예: https://example.com)")

# 저장 폴더 설정
output_folder = "crawled_data"
os.makedirs(output_folder, exist_ok=True)

# 크롤링된 페이지를 JSON과 TXT로 저장하는 함수
def save_page_content(url, content, format="json"):
    file_name = f"{output_folder}/{urlparse(url).netloc}_{urlparse(url).path.strip('/').replace('/', '_')}"
    if format == "json":
        with open(f"{file_name}.json", "w", encoding="utf-8") as f:
            json.dump({"url": url, "content": content}, f, ensure_ascii=False, indent=4)
        return f"{file_name}.json"
    elif format == "txt":
        with open(f"{file_name}.txt", "w", encoding="utf-8") as f:
            f.write(content)
        return f"{file_name}.txt"

# 내부 링크를 필터링하는 함수
def is_internal_link(base, link):
    return urlparse(link).netloc == urlparse(base).netloc or urlparse(link).netloc == ""

# HTML 분석 및 주요 콘텐츠 추출 함수
def analyze_html(soup):
    # HTML에서 주요 정보 추출
    title = soup.title.string if soup.title else "제목 없음"
    description = ""
    for meta in soup.find_all("meta", {"name": "description"}):
        description = meta.get("content", "")
    
    # 주요 텍스트 요소 추출 (h1, h2, h3, p 태그)
    headers = []
    for header in soup.find_all(["h1", "h2", "h3"]):
        headers.append(header.get_text(strip=True))
    
    paragraphs = []
    for paragraph in soup.find_all("p"):
        paragraphs.append(paragraph.get_text(strip=True))
    
    # 분석 결과를 딕셔너리 형태로 반환
    return {
        "title": title,
        "description": description,
        "headers": headers,
        "paragraphs": paragraphs
    }

# HTTP 요청을 여러 방식으로 시도하는 함수
def request_with_retry(url):
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }
    
    try:
        return session.get(url, headers=headers, timeout=5)
    except requests.RequestException as e:
        st.write(f"{url} 요청 실패: {e}")
        return None

# 메인 크롤러 함수
def crawl_site(base_url):
    visited = set()
    to_visit = [base_url]
    saved_files = []

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        response = request_with_retry(current_url)

        if response and response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            page_data = analyze_html(soup)  # HTML 분석하여 주요 정보 추출
            save_page_content(current_url, page_data, format="json")
            save_page_content(current_url, "\n".join(page_data['paragraphs']), format="txt")

            saved_files.append((f"{current_url}.json", f"{current_url}.txt"))

            # 내부 링크 수집
            for link in soup.find_all("a", href=True):
                full_url = urljoin(base_url, link["href"])
                if is_internal_link(base_url, full_url) and full_url not in visited:
                    to_visit.append(full_url)
        else:
            st.write(f"{current_url} 크롤링 실패: 모든 요청 실패")
    
    return saved_files

# 크롤링 시작 버튼
if st.button("크롤링 시작"):
    if base_url:
        with st.spinner("크롤링 중입니다... 잠시만 기다려 주세요."):
            results = crawl_site(base_url)
        
        st.success("크롤링 완료!")
        
        for json_file, txt_file in results:
            st.write(f"{json_file} 파일 다운로드:")
            with open(json_file, "rb") as f:
                st.download_button(label="JSON 다운로드", data=f, file_name=json_file)

            with open(txt_file, "rb") as f:
                st.download_button(label="TXT 다운로드", data=f, file_name=txt_file)
    else:
        st.warning("크롤링할 URL을 입력하세요.")
