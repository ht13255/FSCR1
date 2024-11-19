import os
import pandas as pd
import numpy as np
import cv2
from pytube import YouTube
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
from deepLabCut import analyze_videos
from openpose import OpenPose


# 1. YouTube에서 선수 하이라이트 검색 및 다운로드
def download_highlight(player_name: str, output_dir: str = "./match_videos/") -> str:
    """YouTube에서 선수 하이라이트 영상을 검색하고 다운로드."""
    search_query = f"{player_name} highlights football"
    print(f"'{search_query}' YouTube 검색 중...")

    # Selenium 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(), options=chrome_options)

    try:
        # YouTube 검색
        driver.get(f"https://www.youtube.com/results?search_query={search_query}")
        video_elements = driver.find_elements(By.ID, "video-title")
        first_video_url = video_elements[0].get_attribute("href")
        print(f"다운로드할 URL: {first_video_url}")

        # YouTube 다운로드
        yt = YouTube(first_video_url)
        video_stream = yt.streams.filter(file_extension="mp4").first()
        output_path = os.path.join(output_dir, f"{player_name}_highlight.mp4")
        video_stream.download(output_path=output_path)
        print(f"'{player_name}' 하이라이트 다운로드 완료: {output_path}")
        return output_path

    finally:
        driver.quit()


# 2. Whoscored에서 선수 스탯 검색
def collect_stats_from_whoscored(player_name: str) -> pd.DataFrame:
    """Whoscored에서 선수 데이터를 검색 및 수집."""
    print(f"'{player_name}'의 Whoscored 데이터를 검색 중...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(), options=chrome_options)

    try:
        # Whoscored 검색
        driver.get("https://www.whoscored.com/")
        search_box = driver.find_element(By.NAME, "search")
        search_box.send_keys(player_name)
        search_box.send_keys(Keys.RETURN)

        # 첫 번째 검색 결과 클릭
        driver.implicitly_wait(5)
        first_result = driver.find_element(By.CSS_SELECTOR, "a.result-link")
        first_result.click()

        # 스탯 데이터 크롤링
        driver.implicitly_wait(5)
        stats_table = driver.find_element(By.ID, "player-statistics")
        stats_html = stats_table.get_attribute("outerHTML")
        stats_data = pd.read_html(stats_html)[0]
        print(f"'{player_name}'의 스탯 데이터 수집 완료.")
        return stats_data

    finally:
        driver.quit()


# 3. 영상 분석 기능
def analyze_video_with_deeplabcut(video_path: str):
    """DeepLabCut으로 영상 내 객체 검출."""
    analyze_videos(video_path)
    print(f"DeepLabCut 분석 완료: {video_path}")


def analyze_video_with_openpose(video_path: str):
    """OpenPose를 활용하여 행동 분석."""
    pose_model = OpenPose(model_path="./models/openpose/")
    keypoints = pose_model.analyze(video_path)
    return keypoints


# 4. 스탯 분석 기능
def calculate_performance_metrics(stats_data: pd.DataFrame) -> pd.DataFrame:
    """성능 지표 계산."""
    stats_data['pass_success_rate'] = stats_data['successful_passes'] / stats_data['total_passes']
    stats_data['goal_contribution'] = stats_data['goals'] + stats_data['assists']
    return stats_data


def expected_goals_model(stats_data: pd.DataFrame) -> pd.DataFrame:
    """기대 득점 모델 구축."""
    xg_model = RandomForestClassifier()
    features = stats_data[['shot_distance', 'shot_angle', 'pressure']]
    labels = stats_data['goal']
    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2)
    xg_model.fit(X_train, y_train)
    stats_data['expected_goals'] = xg_model.predict_proba(features)[:, 1]
    return stats_data


# 5. 시각화 및 보고서 생성
def visualize_stats(stats_data: pd.DataFrame):
    """스탯 데이터 시각화."""
    plt.figure(figsize=(10, 6))
    sns.barplot(x='player', y='goal_contribution', data=stats_data)
    plt.title("선수별 경기 기여도")
    plt.xlabel("선수")
    plt.ylabel("경기 기여도")
    plt.show()


def generate_report(player_name: str, stats_data: pd.DataFrame):
    """선수의 장단점 및 미래 잠재력 평가 보고서 생성."""
    player_data = stats_data[stats_data['player'] == player_name]
    current_rating = player_data['current_rating'].values[0]
    potential_rating = player_data['potential_rating'].values[0]
    strengths = player_data[['strengths']].values[0]
    weaknesses = player_data[['weaknesses']].values[0]
    print(f"""
    선수: {player_name}
    현재 능력: {current_rating}
    잠재력: {potential_rating}
    장점: {strengths}
    약점: {weaknesses}
    """)


# 메인 실행
if __name__ == "__main__":
    # 선수 이름 입력
    player_name = input("분석할 선수 이름을 입력하세요: ")

    # 1. YouTube 하이라이트 다운로드
    video_path = download_highlight(player_name)

    # 2. 영상 분석
    analyze_video_with_deeplabcut(video_path)
    keypoints = analyze_video_with_openpose(video_path)

    # 3. Whoscored 스탯 데이터 수집 및 분석
    stats_data = collect_stats_from_whoscored(player_name)
    stats_with_metrics = calculate_performance_metrics(stats_data)
    stats_with_xg = expected_goals_model(stats_with_metrics)

    # 4. 시각화 및 보고서 생성
    visualize_stats(stats_with_xg)
    generate_report(player_name, stats_with_xg)