# 파일: streamlit_web_scraper.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os

def fetch_page_content(url):
    """주어진 URL의 HTML 콘텐츠를 가져오는 함수."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"URL 요청 실패: {e}")
        return None

def scrape_content_from_links(base_url, links):
    """주어진 링크에서 텍스트 콘텐츠를 추출하는 함수."""
    scraped_data = []
    for link in links:
        full_url = base_url + link if link.startswith('/') else link
        page_content = fetch_page_content(full_url)
        if not page_content:
            continue
        
        soup = BeautifulSoup(page_content, 'html.parser')
        # HTML에서 텍스트를 추출 (필요에 따라 태그를 변경)
        title = soup.title.string if soup.title else "No Title"
        body = soup.get_text(separator='\n').strip()
        scraped_data.append({"url": full_url, "title": title, "content": body})
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
st.title("웹 크롤링 및 데이터 저장")

# 입력
base_url = st.text_input("기본 URL을 입력하세요", value="https://example.com")
link_selector = st.text_input("크롤링할 링크의 CSS 선택자를 입력하세요", value="a")  # 기본은 모든 링크

if st.button("크롤링 시작"):
    # HTML 콘텐츠 가져오기
    main_page_content = fetch_page_content(base_url)
    if not main_page_content:
        st.stop()

    # HTML 파싱 및 링크 수집
    soup = BeautifulSoup(main_page_content, 'html.parser')
    links = [a['href'] for a in soup.select(link_selector) if 'href' in a.attrs]

    # 데이터 크롤링
    scraped_data = scrape_content_from_links(base_url, links)

    # 저장 경로 설정
    os.makedirs("output", exist_ok=True)
    txt_path = os.path.join("output", "scraped_data.txt")
    json_path = os.path.join("output", "scraped_data.json")

    # 데이터 저장
    save_to_txt(scraped_data, txt_path)
    save_to_json(scraped_data, json_path)

    # 결과 표시
    st.success("크롤링 완료!")
    st.write("크롤링된 데이터 (최대 5개 미리보기):", scraped_data[:5])
    st.download_button("TXT 파일 다운로드", open(txt_path, "rb"), "scraped_data.txt")
    st.download_button("JSON 파일 다운로드", open(json_path, "rb"), "scraped_data.json")
