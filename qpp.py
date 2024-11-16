# streamlit_app.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from fpdf import FPDF
import os

# 광고 패턴 설정
AD_PATTERNS = ["ads", "tracking", "promo", "banner"]

# 상태 저장 파일
STATUS_FILE = "crawl_status.json"

# 상태 저장 함수
def save_status(status):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=4)

# 상태 로드 함수
def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# PDF 저장 함수
def save_as_pdf(results, output_file):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for url, data in results.items():
        pdf.cell(200, 10, txt=f"URL: {url}", ln=True, align='L')
        pdf.ln(10)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 10, txt="Links:")
        for link in data["links"]:
            pdf.multi_cell(0, 10, txt=link)
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 10, txt="Content:")
        pdf.multi_cell(0, 10, txt=data["content"])
        pdf.ln(10)
    pdf.output(output_file)

# 크롤링 함수
def crawl_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        # 광고 필터링
        filtered_links = [link['href'] for link in links if not any(pattern in link['href'] for pattern in AD_PATTERNS)]
        return filtered_links, soup.get_text()
    except requests.exceptions.RequestException as e:
        st.warning(f"HTTP 요청 실패: {e}. 우회 방식으로 시도합니다.")
        # 우회 방식 (BeautifulSoup을 HTML 파일로 파싱)
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.content, "html.parser")
            links = soup.find_all("a", href=True)
            filtered_links = [link['href'] for link in links if not any(pattern in link['href'] for pattern in AD_PATTERNS)]
            return filtered_links, soup.get_text()
        except Exception as ex:
            st.error(f"우회 실패: {ex}")
            return [], ""

# Streamlit UI
def main():
    st.title("다중 URL 크롤러")
    st.write("입력한 URL의 링크를 크롤링하고 JSON과 PDF로 저장합니다.")

    # URL 입력
    urls = st.text_area("크롤링할 URL 입력 (여러 URL은 줄 바꿈으로 구분)", height=150)
    urls = [url.strip() for url in urls.split("\n") if url.strip()]
    save_pdf = st.checkbox("PDF 형식으로 저장")
    start_crawl = st.button("크롤링 시작")

    # 이전 상태 로드
    status = load_status()

    if start_crawl and urls:
        st.info("크롤링 진행 중...")
        results = {}
        for url in urls:
            st.write(f"크롤링 중: {url}")
            links, content = crawl_url(url)
            results[url] = {"links": links, "content": content}
            status[url] = "완료"

            # 상태 저장
            save_status(status)

        # JSON 저장
        json_file = "crawl_results.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        st.success(f"크롤링 완료! 결과가 {json_file}에 저장되었습니다.")

        # PDF 저장
        if save_pdf:
            pdf_file = "crawl_results.pdf"
            save_as_pdf(results, pdf_file)
            st.success(f"PDF 파일로 저장 완료: {pdf_file}")

if __name__ == "__main__":
    main()