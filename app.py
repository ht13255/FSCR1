import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep
from collections import Counter

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

def analyze_page_structure(html_content):
    """HTML 페이지에서 태그, 클래스, ID를 분석하여 선택자 옵션을 제공."""
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

    return tag_count, class_count, id_count

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

if st.button("분석 시작"):
    # 페이지 콘텐츠 가져오기
    main_page_content = fetch_page_content(base_url)
    if not main_page_content:
        st.stop()

    # HTML 구조 분석
    tag_count, class_count, id_count = analyze_page_structure(main_page_content)

    # 분석 결과 표시
    st.write("**태그 빈도수:**")
    st.write(dict(tag_count))

    st.write("**클래스 빈도수 (최대 10개):**")
    st.write(dict(class_count.most_common(10)))

    st.write("**ID 빈도수 (최대 10개):**")
    st.write(dict(id_count.most_common(10)))

    # CSS 선택자 옵션 제공
    st.subheader("크롤링할 CSS 선택자를 선택하세요")
    css_tag = st.selectbox("태그 선택", [""] + list(tag_count.keys()))
    css_class = st.selectbox("클래스 선택 (선택 시 .classname 형식으로 자동 처리)", [""] + list(class_count.keys()))
    css_id = st.selectbox("ID 선택 (선택 시 #id 형식으로 자동 처리)", [""] + list(id_count.keys()))

    # CSS 선택자 생성
    css_selector = ""
    if css_tag:
        css_selector = css_tag
    if css_class:
        css_selector += f".{css_class}" if css_selector else f".{css_class}"
    if css_id:
        css_selector += f"#{css_id}" if css_selector else f"#{css_id}"

    st.write(f"**생성된 CSS 선택자:** `{css_selector}`")

    # 크롤링 시작
    if st.button("크롤링 시작"):
        if not css_selector:
            st.error("CSS 선택자를 선택하거나 직접 입력하세요.")
            st.stop()

        # 링크 수집
        soup = BeautifulSoup(main_page_content, 'html.parser')
        links = [a['href'] for a in soup.select(css_selector) if 'href' in a.attrs]

        if not links:
            st.error("선택자에 해당하는 링크가 없습니다. 선택자를 확인하세요.")
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
