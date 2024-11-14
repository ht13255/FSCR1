import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os

# Streamlit 설정
st.title("웹사이트 크롤러")
st.write("내부 링크를 크롤링하여 JSON 및 TXT 형식으로 저장합니다.")

# URL 입력
base_url = st.text_input("크롤링할 사이트 URL을 입력하세요 (예: https://example.com)")

# 크롤링된 페이지를 JSON과 TXT로 저장하는 함수
def save_page_content(url, content, format="json"):
    file_name = f"{urlparse(url).netloc}_{urlparse(url).path.strip('/').replace('/', '_')}"
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

        try:
            response = requests.get(current_url, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 페이지 내용 저장
            json_file = save_page_content(current_url, soup.get_text(), format="json")
            txt_file = save_page_content(current_url, soup.get_text(), format="txt")
            saved_files.append((json_file, txt_file))

            # 내부 링크 수집
            for link in soup.find_all("a", href=True):
                full_url = urljoin(base_url, link["href"])
                if is_internal_link(base_url, full_url) and full_url not in visited:
                    to_visit.append(full_url)

        except requests.RequestException as e:
            st.write(f"{current_url} 크롤링 실패: {e}")
    
    return saved_files

# 크롤링 시작 버튼
if st.button("크롤링 시작"):
    if base_url:
        with st.spinner("크롤링 중입니다... 잠시만 기다려 주세요."):
            os.makedirs("crawled_data", exist_ok=True)  # 저장 폴더 생성
            results = crawl_site(base_url)
        
        # 크롤링 완료 메시지와 파일 다운로드
        st.success("크롤링 완료!")
        
        for json_file, txt_file in results:
            st.write(f"{json_file} 파일 다운로드:")
            with open(json_file, "rb") as f:
                st.download_button(label="JSON 다운로드", data=f, file_name=json_file)

            with open(txt_file, "rb") as f:
                st.download_button(label="TXT 다운로드", data=f, file_name=txt_file)
    else:
        st.warning("크롤링할 URL을 입력하세요.")
