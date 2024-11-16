import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep

# User-Agent 설정
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
}

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

def scrape_links(base_url, css_selector):
    """주어진 URL의 페이지에서 지정된 CSS 선택자로 링크를 수집."""
    page_content = fetch_page_content(base_url)
    if not page_content:
        return []
    
    soup = BeautifulSoup(page_content, 'html.parser')
    links = [a['href'] for a in soup.select(css_selector) if 'href' in a.attrs]
    return links

def scrape_content_from_links(base_url, links):
    """주어진 링크에서 텍스트 콘텐츠를 추출."""
    scraped_data = []
    for link in links:
        full_url = base_url + link if link.startswith('/') else link
        page_content = fetch_page_content(full_url)
        if not page_content:
            continue

        soup = BeautifulSoup(page_content, 'html.parser')
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
    # robots.txt 확인 메시지 추가
    robots_url = f"{base_url.rstrip('/')}/robots.txt"
    try:
        robots_response = requests.get(robots_url, headers=HEADERS)
        if robots_response.status_code == 200:
            st.write("robots.txt 내용:\n", robots_response.text)
            if "Disallow: /" in robots_response.text:
                st.warning("크롤링이 제한된 사이트일 수 있습니다.")
    except:
        st.warning("robots.txt를 확인할 수 없습니다.")

    # 링크 수집
    links = scrape_links(base_url, link_selector)
    if not links:
        st.error("링크를 찾을 수 없습니다. CSS 선택자를 확인하세요.")
        st.stop()

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
