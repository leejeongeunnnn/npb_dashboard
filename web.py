import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import textwrap
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import stadium_layouts
import plotly.graph_objects as go

# 웹사이트 기본 설정
st.set_page_config(page_title="일본 프로야구 대시보드", page_icon="⚾", layout="wide")

# 한국어 팀 이름 -> 일본어 팀 이름 매핑
TEAM_MAPPING = {
    "소프트뱅크": "ソフトバンク",
    "오릭스": "オリックス",
    "롯데": "ロッテ",
    "지바롯데": "ロッテ",
    "지바 롯데": "ロッテ",
    "라쿠텐": "楽天",
    "세이부": "西武",
    "니혼햄": "日本ハム",
    "요미우리": "巨人",
    "자이언츠": "巨人",
    "한신": "阪神",
    "주니치": "中日",
    "요코하마": "DeNA",
    "데나": "DeNA",
    "야쿠르트": "ヤクルト",
    "히로시마": "広島"
}

# 각 팀의 한국어 명칭 및 대표 컬러 설정
TEAM_INFO = {
    "巨人": {"kr": "요미우리 자이언츠", "color": "#F97316"},
    "阪神": {"kr": "한신 타이거스", "color": "#EAB308"},
    "中日": {"kr": "주니치 드래곤즈", "color": "#3B82F6"},
    "DeNA": {"kr": "요코하마 DeNA 베이스타스", "color": "#2563EB"},
    "ヤクルト": {"kr": "야쿠르트 스왈로스", "color": "#475569"},
    "広島": {"kr": "히로시마 도요 카프", "color": "#EF4444"},
    "ソフトバンク": {"kr": "소프트뱅크 호크스", "color": "#FBBF24"},
    "オリックス": {"kr": "오릭스 버팔로즈", "color": "#1E293B"},
    "ロッテ": {"kr": "지바 롯데 마린스", "color": "#94A3B8"},
    "楽天": {"kr": "라쿠텐 골든이글스", "color": "#991B1B"},
    "西武": {"kr": "세이부 라이온즈", "color": "#2563EB"},
    "日本ハム": {"kr": "니혼햄 파이터즈", "color": "#06B6D4"}
}

# 선수 이름 일본어 -> 한국어 매핑 사전 (공백 제거 후 매핑)
import player_translations
PLAYER_NAME_TRANSLATION = player_translations.PLAYER_NAME_TRANSLATION


def translate_player_name(jp_name):
    """일본어 선수 이름을 한국어 번역으로 매핑. 매핑되지 않은 경우 원래 이름 반환."""
    if not jp_name:
        return jp_name
    # 공백 제거 및 특수 기호 정규화
    clean = jp_name.replace(" ", "").replace("\u3000", "").replace("\xa0", "")
    return PLAYER_NAME_TRANSLATION.get(clean, jp_name)

# 각 팀의 홈구장 및 공식 사이트 정보 (위경도 포함)
TEAM_STADIUM_INFO = {
    "巨人": {
        "team_name_kr": "요미우리 자이언츠",
        "stadium_kr": "도쿄 돔",
        "stadium_jp": "東京ドーム",
        "address": "東京都文京区後楽1-3-61",
        "website": "https://www.giants.jp/",
        "lat": 35.70562,
        "lon": 139.75191
    },
    "阪神": {
        "team_name_kr": "한신 타이거스",
        "stadium_kr": "한신 고시엔 구장",
        "stadium_jp": "阪神甲子園球場",
        "address": "兵庫県西宮市甲子園町1-82",
        "website": "https://hanshintigers.jp/",
        "lat": 34.72121,
        "lon": 135.36162
    },
    "中日": {
        "team_name_kr": "주니치 드래곤즈",
        "stadium_kr": "반테린 돔 나고야",
        "stadium_jp": "バンテリンドーム ナゴヤ",
        "address": "愛知県名古屋市東区大幸南1-1-1",
        "website": "https://dragons.jp/",
        "lat": 35.18595,
        "lon": 136.94745
    },
    "DeNA": {
        "team_name_kr": "요코하마 DeNA 베이스타스",
        "stadium_kr": "요코하마 스타디움",
        "stadium_jp": "横浜スタジアム",
        "address": "神奈川県横浜市中区横浜公園",
        "website": "https://www.baystars.co.jp/",
        "lat": 35.44332,
        "lon": 139.64010
    },
    "ヤクルト": {
        "team_name_kr": "야쿠르트 스왈로스",
        "stadium_kr": "메이지 진구 야구장",
        "stadium_jp": "明治神宮野球場",
        "address": "東京都新宿区霞ヶ丘町3-1",
        "website": "https://www.yakult-swallows.co.jp/",
        "lat": 35.67437,
        "lon": 139.71708
    },
    "広島": {
        "team_name_kr": "히로시마 도요 카프",
        "stadium_kr": "마쓰다 줌줌 스타디움 히로시마",
        "stadium_jp": "MAZDA Zoom-Zoom スタジアム広島",
        "address": "広島県広島市南区南蟹屋2-3-1",
        "website": "https://www.carp.co.jp/",
        "lat": 34.39183,
        "lon": 132.48472
    },
    "ソフトバンク": {
        "team_name_kr": "소프트뱅크 호크스",
        "stadium_kr": "미즈호 PayPay 돔 후쿠오카",
        "stadium_jp": "みずほPayPayドーム福岡",
        "address": "福岡県福岡市中央区地行浜2-2-2",
        "website": "https://www.softbankhawks.co.jp/",
        "lat": 33.59539,
        "lon": 130.36223
    },
    "オリックス": {
        "team_name_kr": "오릭스 버팔로즈",
        "stadium_kr": "교세라 돔 오사카",
        "stadium_jp": "京セラドーム大阪",
        "address": "大阪府大阪市西区千代崎3-中2-1",
        "website": "https://www.buffaloes.co.jp/",
        "lat": 34.66924,
        "lon": 135.47615
    },
    "ロッテ": {
        "team_name_kr": "지바 롯데 마린스",
        "stadium_kr": "조조 마린 스타디움",
        "stadium_jp": "ZOZOマリンスタジアム",
        "address": "千葉県千葉市美浜区美浜1",
        "website": "https://www.marines.co.jp/",
        "lat": 35.64513,
        "lon": 140.03079
    },
    "楽天": {
        "team_name_kr": "라쿠텐 골든이글스",
        "stadium_kr": "라쿠텐 모바일 파크 미야기",
        "stadium_jp": "楽天モバイルパーク宮城",
        "address": "宮城県仙台市宮城野区宮城野2-11-6",
        "website": "https://www.rakuteneagles.jp/",
        "lat": 38.25656,
        "lon": 140.90253
    },
    "西武": {
        "team_name_kr": "세이부 라이온즈",
        "stadium_kr": "벨루나 돔",
        "stadium_jp": "ベルーナドーム",
        "address": "埼玉県所沢市上山口2135",
        "website": "https://www.seibulions.jp/",
        "lat": 35.76861,
        "lon": 139.42052
    },
    "日本ハム": {
        "team_name_kr": "니혼햄 파이터즈",
        "stadium_kr": "에스콘 필드 홋카이도",
        "stadium_jp": "エスコンフィールドHOKKAIDO",
        "address": "北海道北広島市Fビレッジ1番地",
        "website": "https://www.fighters.co.jp/",
        "lat": 42.99042,
        "lon": 141.55442
    }
}

def get_japanese_team_name(korean_name):
    korean_name_clean = korean_name.strip()
    if korean_name_clean in TEAM_MAPPING:
        return TEAM_MAPPING[korean_name_clean]
    for k, v in TEAM_MAPPING.items():
        if k in korean_name_clean or korean_name_clean in k:
            return v
    return korean_name_clean

# 야후 재팬 팀 ID 매핑
TEAM_IDS = {
    "巨人": "1",
    "ヤクルト": "2",
    "DeNA": "3",
    "中日": "4",
    "阪神": "5",
    "広島": "6",
    "西武": "7",
    "日本ハム": "8",
    "ロッテ": "9",
    "オリックス": "11",
    "ソフトバンク": "12",
    "楽天": "376"
}

def get_team_id(korean_name):
    jp_name = get_japanese_team_name(korean_name)
    return TEAM_IDS.get(jp_name)

# 야후 재팬 리그 순위표 크롤링 함수
def fetch_league_standings():
    url = "https://baseball.yahoo.co.jp/npb/standings/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table', class_='bb-rankTable')
        
        if len(tables) < 2:
            return None, None
            
        def parse_table(table):
            rows = table.find_all('tr')
            teams = []
            first_wins = None
            first_losses = None
            
            for r in rows:
                tds = r.find_all('td')
                if len(tds) >= 8:
                    rank_raw = tds[0].text.strip()
                    rank = "1위" if rank_raw in ["優勝", "1"] else f"{rank_raw}위"
                    name = tds[1].find('a').text.strip() if tds[1].find('a') else tds[1].text.strip()
                    games = tds[2].text.strip()
                    wins = tds[3].text.strip()
                    losses = tds[4].text.strip()
                    draws = tds[5].text.strip()
                    pct = tds[6].text.strip()
                    raw_diff = tds[7].text.strip() # 야후 재팬 원본: 바로 앞 팀과의 승차
                    
                    # 1위 팀 기준 공식 게임차 계산: ((1위승 - 팀승) + (팀패 - 1위패)) / 2.0
                    try:
                        w_val = int(wins)
                        l_val = int(losses)
                        if first_wins is None:
                            first_wins = w_val
                            first_losses = l_val
                            calc_diff_str = "-"
                        else:
                            diff_val = ((first_wins - w_val) + (l_val - first_losses)) / 2.0
                            calc_diff_str = f"{diff_val:.1f}" if diff_val % 1 != 0 else f"{int(diff_val):.1f}"
                    except Exception:
                        calc_diff_str = raw_diff
                    
                    teams.append({
                        '순위': rank,
                        '팀명': TEAM_INFO.get(name, {"kr": name})["kr"],
                        '경기': games,
                        '승': wins,
                        '패': losses,
                        '무': draws,
                        '승률': pct,
                        '게임차 (1위 기준)': calc_diff_str,
                        '앞 팀 차': raw_diff
                    })
            return teams
            
        central_teams = parse_table(tables[0])
        pacific_teams = parse_table(tables[1])
        return central_teams, pacific_teams
    except Exception as e:
        print(f"[ERROR] Fetch standings failed: {e}")
        return None, None

# 야후 재팬 야구 뉴스 헤드라인 크롤링 함수
def fetch_npb_news():
    url = "https://baseball.yahoo.co.jp/npb/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        seen_links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'news.yahoo.co.jp/articles/' in href:
                title = a.text.strip()
                if title and len(title) > 10 and href not in seen_links:
                    seen_links.add(href)
                    translated_title = title
                    # 일본어 팀명을 한국어로 변환
                    for jp, info in TEAM_INFO.items():
                        translated_title = translated_title.replace(jp, info['kr'])
                    
                    news_list.append({
                        'title': translated_title,
                        'url': href
                    })
                    if len(news_list) >= 10:
                        break
        return news_list
    except Exception as e:
        print(f"[ERROR] Fetch news failed: {e}")
        return []

# 최애 팀 최근 5경기 결과 크롤링 함수
def fetch_recent_games(team_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    def get_games_for_month(month_str=None):
        url = f"https://baseball.yahoo.co.jp/npb/teams/{team_id}/schedule"
        params = {}
        if month_str:
            params['month'] = month_str
        try:
            res = requests.get(url, params=params, headers=headers)
            res.encoding = 'utf-8'
            soup_month = BeautifulSoup(res.text, 'html.parser')
            table = soup_month.find('table', class_='bb-calendarTable')
            
            month_games = []
            if not table:
                return month_games
                
            cells = table.find_all('td', class_='bb-calendarTable__data')
            for cell in cells:
                if '試合終了' not in cell.text:
                    continue
                
                date_el = cell.find(class_='bb-calendarTable__date')
                opp_el = cell.find(class_='bb-calendarTable__versusLogo')
                score_el = cell.find(class_='bb-calendarTable__score')
                venue_el = cell.find(class_='bb-calendarTable__venue')
                
                if not date_el or not opp_el or not score_el:
                    continue
                    
                day = date_el.text.strip()
                opp_jp = opp_el.text.strip()
                opp_kr = TEAM_INFO.get(opp_jp, {"kr": opp_jp})["kr"]
                venue = venue_el.text.strip() if venue_el else "알 수 없음"
                
                home_el = score_el.find(class_='bb-calendarTable__home')
                away_el = score_el.find(class_='bb-calendarTable__away')
                home_score_val = int(home_el.text.strip()) if home_el and home_el.text.strip().isdigit() else 0
                away_score_val = int(away_el.text.strip()) if away_el and away_el.text.strip().isdigit() else 0
                
                win_span = cell.find('span', class_=lambda x: x and ('win' in x or 'lose' in x or 'draw' in x))
                result = "무승부"
                if win_span:
                    label = win_span.get('aria-label', '')
                    classes = win_span.get('class', [])
                    if '勝利' in label or any('win' in c for c in classes):
                        result = "승리"
                    elif '敗' in label or any('lose' in c for c in classes):
                        result = "패배"
                        
                if result == "승리":
                    my_score = max(home_score_val, away_score_val)
                    opp_score = min(home_score_val, away_score_val)
                elif result == "패배":
                    my_score = min(home_score_val, away_score_val)
                    opp_score = max(home_score_val, away_score_val)
                else:
                    my_score = home_score_val
                    opp_score = away_score_val
                    
                display_month = month_str.split('-')[1] if month_str else datetime.date.today().strftime("%m")
                display_month_clean = str(int(display_month))
                
                month_games.append({
                    'day_sort': int(day),
                    '날짜': f"{display_month_clean}월 {day}일",
                    '상대팀': opp_kr,
                    '결과': result,
                    '스코어': f"{my_score} - {opp_score}",
                    '구장': venue
                })
            
            month_games.sort(key=lambda x: x['day_sort'])
            return month_games
        except Exception as e:
            print(f"[ERROR] Failed to fetch schedule for month {month_str}: {e}")
            return []
            
    today = datetime.date.today()
    current_month_str = today.strftime("%Y-%m")
    games = get_games_for_month(current_month_str)
    
    if len(games) < 5:
        year, month = today.year, today.month
        first_day = datetime.date(year, month, 1)
        prev_month_last_day = first_day - datetime.timedelta(days=1)
        prev_month_str = prev_month_last_day.strftime("%Y-%m")
        
        prev_games = get_games_for_month(prev_month_str)
        games = prev_games + games
        
    return games[-5:]

# 프리미엄 CSS 주입 (기본 라이트 모드)
custom_css_light = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

/* 전체 컨테이너 폰트 및 스타일 변경 */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', 'Noto Sans KR', sans-serif !important;
}

/* Glassmorphism 카드 스타일 */
.match-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.match-card:hover {
    transform: translateY(-2px);
    border-color: #cbd5e1;
    background: #f8fafc;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
}

/* 최애 팀 하이라이트 카드 */
.match-card-fav {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border: 2px solid #f59e0b;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 8px 32px rgba(245, 158, 11, 0.12);
    position: relative;
}

.match-card-fav::before {
    content: "★ FAVORITE TEAM MATCH";
    position: absolute;
    top: 10px;
    right: 15px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #d97706;
    letter-spacing: 0.05em;
}

.match-card-fav:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(245, 158, 11, 0.2);
}

.match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 8px;
    margin-bottom: 12px;
}

.match-venue {
    font-size: 0.8rem;
    color: #4b5563;
    display: flex;
    align-items: center;
    gap: 4px;
}

.match-status-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 20px;
    text-transform: uppercase;
}

.status-finished {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
}

.status-live {
    background-color: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.25);
    animation: pulse 2s infinite;
}

.status-upcoming {
    background-color: rgba(59, 130, 246, 0.1);
    color: #2563eb;
    border: 1px solid rgba(59, 130, 246, 0.25);
}

.badge-series {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    color: #b45309;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 12px;
    border: 1px solid #fcd34d;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.bracket-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    margin-bottom: 12px;
}

.match-teams-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.team-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.team-info {
    display: flex;
    align-items: center;
    gap: 10px;
}

.team-color-indicator {
    width: 5px;
    height: 20px;
    border-radius: 2.5px;
}

.team-name-kr {
    font-size: 1.05rem;
    font-weight: 600;
    color: #111827;
}

.team-name-jp {
    font-size: 0.8rem;
    color: #4b5563;
    margin-left: 5px;
}

.team-score-val {
    font-size: 1.4rem;
    font-weight: 700;
    color: #111827;
    min-width: 30px;
    text-align: right;
}

.score-winner {
    color: #059669 !important;
}

.score-loser {
    color: #9ca3af !important;
}

.stadium-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    margin-top: 10px;
}

.stadium-card h3 {
    color: #111827 !important;
}

.stadium-card p {
    color: #6b7280 !important;
}

.stadium-card span {
    color: #1f2937 !important;
}

.news-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    transition: transform 0.2s, box-shadow 0.2s;
}

.news-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.news-card span {
    color: #1e3a8a !important;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
}
</style>
"""

# 다크 모드용 CSS
custom_css_dark = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

/* 전체 컨테이너 폰트 및 스타일 변경 */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', 'Noto Sans KR', sans-serif !important;
    background-color: #0f172a !important;
    color: #f8fafc !important;
}

[data-testid="stSidebar"] {
    background-color: #1e293b !important;
}

/* 다크모드 하의 일반 스트림릿 텍스트 */
h1, h2, h3, h4, h5, h6, p, label, li, span {
    color: #f8fafc !important;
}

/* Glassmorphism 카드 스타일 */
.match-card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.match-card:hover {
    transform: translateY(-2px);
    border-color: #475569 !important;
    background: #334155 !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

/* 최애 팀 하이라이트 카드 */
.match-card-fav {
    background: linear-gradient(135deg, #78350f 0%, #451a03 100%) !important;
    border: 2px solid #f59e0b !important;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 8px 32px rgba(245, 158, 11, 0.2);
    position: relative;
}

.match-card-fav::before {
    content: "★ FAVORITE TEAM MATCH";
    position: absolute;
    top: 10px;
    right: 15px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #fbbf24 !important;
    letter-spacing: 0.05em;
}

.match-card-fav:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(245, 158, 11, 0.3);
}

.match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #334155;
    padding-bottom: 8px;
    margin-bottom: 12px;
}

.match-venue {
    font-size: 0.8rem;
    color: #cbd5e1 !important;
    display: flex;
    align-items: center;
    gap: 4px;
}

.match-status-badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 20px;
    text-transform: uppercase;
}

.status-finished {
    background-color: #334155 !important;
    color: #cbd5e1 !important;
    border: 1px solid #475569 !important;
}

.status-live {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171 !important;
    border: 1px solid rgba(239, 68, 68, 0.4);
    animation: pulse 2s infinite;
}

.status-upcoming {
    background-color: rgba(59, 130, 246, 0.2);
    color: #60a5fa !important;
    border: 1px solid rgba(59, 130, 246, 0.4);
}

.badge-series {
    background: linear-gradient(135deg, #78350f 0%, #451a03 100%) !important;
    color: #fde68a !important;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 12px;
    border: 1px solid #b45309 !important;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.bracket-card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    margin-bottom: 12px;
}

.match-teams-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.team-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.team-info {
    display: flex;
    align-items: center;
    gap: 10px;
}

.team-color-indicator {
    width: 5px;
    height: 20px;
    border-radius: 2.5px;
}

.team-name-kr {
    font-size: 1.05rem;
    font-weight: 600;
    color: #f8fafc !important;
}

.team-name-jp {
    font-size: 0.8rem;
    color: #94a3b8 !important;
    margin-left: 5px;
}

.team-score-val {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f8fafc !important;
    min-width: 30px;
    text-align: right;
}

.score-winner {
    color: #34d399 !important;
}

.score-loser {
    color: #64748b !important;
}

.stadium-card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    margin-top: 10px;
}

.stadium-card h3 {
    color: #f8fafc !important;
}

.stadium-card p {
    color: #94a3b8 !important;
}

.stadium-card span {
    color: #cbd5e1 !important;
}

.news-card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s, box-shadow 0.2s;
}

.news-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.news-card span {
    color: #60a5fa !important;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
}
</style>
"""

# ★ 1. 웹사이트가 사용자의 최애 팀을 기억하게 만들기 (세션 상태)
if 'my_team' not in st.session_state:
    st.session_state['my_team'] = "소프트뱅크" # 기본값

if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False

# 사이드바에서 다크모드 토글 생성
with st.sidebar:
    st.markdown("### 🌓 화면 모드 설정")
    dark_mode = st.toggle("다크 모드 활성화", value=st.session_state['dark_mode'])
    st.session_state['dark_mode'] = dark_mode

# 다크모드 여부에 따라 알맞은 CSS 주입
if st.session_state['dark_mode']:
    st.markdown(custom_css_dark, unsafe_allow_html=True)
else:
    st.markdown(custom_css_light, unsafe_allow_html=True)

st.title("⚾ 일본 프로야구 대시보드")

# 날짜 선택을 상위 영역에 배치하여 모든 탭에서 동일하게 동작하도록 최적화
selected_date = st.date_input("📅 조회할 날짜를 선택하세요", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# ★ 2. 화면을 7개의 탭(메뉴)으로 깔끔하게 나누기
tab1, tab2, tab_ps, tab3, tab4, tab5, tab6 = st.tabs(["⚙️ 팀 설정", "🔥 경기 결과", "🍁 포스트시즌 (CS & 일본시리즈)", "🏃‍♂️ 선수 상세 기록", "🏟️ 구장 및 공식 사이트", "🏆 리그 순위표", "📰 주요 야구 뉴스"])

# --- [첫 번째 탭] 팀 설정 ---
with tab1:
    st.subheader("👑 나의 최애 팀을 설정하세요")
    team_input = st.text_input("팀 이름 입력 (예: 소프트뱅크, 오릭스, 요미우리)", st.session_state['my_team'])
    
    if st.button("저장하기"):
        st.session_state['my_team'] = team_input # 입력한 팀으로 기억 덮어쓰기!
        st.success(f"완료! 지금부터 '{team_input}'의 정보를 위주로 보여드릴게요.")
        
    current_team = st.session_state['my_team']
    team_id = get_team_id(current_team)
    
    if team_id:
        st.markdown(f"### 📈 {current_team} 최근 5경기 전적 및 트렌드")
        with st.spinner(f'{current_team}의 최근 전적을 불러오는 중...'):
            recent_games = fetch_recent_games(team_id)
            
        if not recent_games:
            st.info("최근 완료된 경기 정보가 없거나 일정을 불러올 수 없습니다.")
        else:
            # 최근 전적 요약 계산
            wins = sum(1 for g in recent_games if g['결과'] == "승리")
            losses = sum(1 for g in recent_games if g['결과'] == "패배")
            draws = sum(1 for g in recent_games if g['결과'] == "무승부")
            
            # 동그란 이모지 모양의 전적 라인
            trend_html = "<div style='display: flex; gap: 8px; margin-bottom: 20px; align-items: center;'>"
            for g in recent_games:
                if g['결과'] == "승리":
                    bg = "#10b981"
                    txt = "승"
                elif g['결과'] == "패배":
                    bg = "#ef4444"
                    txt = "패"
                else:
                    bg = "#6b7280"
                    txt = "무"
                trend_html += f"""<div style='
                    background-color: {bg};
                    color: white;
                    font-weight: 700;
                    font-size: 0.85rem;
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                '>{txt}</div>"""
            trend_html += f"<span style='margin-left: 12px; font-weight: 600; font-size: 1.1rem; color: #1f2937;'>({wins}승 {losses}패{f' {draws}무' if draws else ''})</span></div>"
            st.markdown(trend_html, unsafe_allow_html=True)
            
            # 상세 이력 DataFrame 출력
            df_recent = pd.DataFrame(recent_games)[['날짜', '상대팀', '결과', '스코어', '구장']]
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.warning("등록되지 않은 팀명입니다. 정확한 이름으로 입력해 주세요.")

# --- 크롤링 함수 (NPB 규정타석 타자 스크래핑) ---
def fetch_qualified_batters():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    batters = {}
    
    # 12개 구단 축약어 -> 한국어 매핑 및 공식 구단 컬러 설정
    team_abbrev_map = {
        "神": {"kr": "한신 타이거스", "team_jp": "阪神", "color": "#EAB308"},
        "広": {"kr": "히로시마 도요 카프", "team_jp": "広島", "color": "#EF4444"},
        "デ": {"kr": "요코하마 DeNA 베이스타스", "team_jp": "DeNA", "color": "#2563EB"},
        "巨": {"kr": "요미우리 자이언츠", "team_jp": "巨人", "color": "#F97316"},
        "ヤ": {"kr": "야쿠르트 스왈로스", "team_jp": "ヤクルト", "color": "#475569"},
        "中": {"kr": "주니치 드래곤즈", "team_jp": "中日", "color": "#3B82F6"},
        "ソ": {"kr": "소프트뱅크 호크스", "team_jp": "ソフトバンク", "color": "#FBBF24"},
        "日": {"kr": "니혼햄 파이터즈", "team_jp": "日本ハム", "color": "#06B6D4"},
        "ロ": {"kr": "지바 롯데 마린스", "team_jp": "ロッテ", "color": "#94A3B8"},
        "楽": {"kr": "라쿠텐 골든이글스", "team_jp": "楽天", "color": "#991B1B"},
        "西": {"kr": "세이부 라이온즈", "team_jp": "西武", "color": "#2563EB"},
        "オ": {"kr": "오릭스 버팔로즈", "team_jp": "オリックス", "color": "#1E293B"}
    }
    
    urls = [
        "https://npb.jp/bis/2026/stats/bat_c.html",
        "https://npb.jp/bis/2026/stats/bat_p.html"
    ]
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                continue
            html = res.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            if not table:
                continue
            rows = table.find_all('tr')
            for r in rows[1:]:
                cells = [c.text.strip().replace('\n', '').replace('\r', '').replace('\u3000', ' ') for c in r.find_all(['td', 'th'])]
                if len(cells) >= 24:
                    full_name_raw = cells[1] # 예: "佐藤 輝明(神)"
                    if '(' in full_name_raw and ')' in full_name_raw:
                        name, abbrev = full_name_raw.split('(')
                        abbrev = abbrev.replace(')', '')
                        name = name.strip()
                    else:
                        name = full_name_raw.strip()
                        abbrev = ""
                        
                    team_info = team_abbrev_map.get(abbrev, {"kr": "기타", "team_jp": abbrev, "color": "#9ca3af"})
                    
                    try:
                        avg = float(cells[2]) if cells[2] != '.' else 0.0
                    except ValueError:
                        avg = 0.0
                        
                    try:
                        hr = int(cells[10])
                    except ValueError:
                        hr = 0
                        
                    try:
                        sb = int(cells[13])
                    except ValueError:
                        sb = 0
                        
                    try:
                        slg = float(cells[22]) if cells[22] != '.' else 0.0
                    except ValueError:
                        slg = 0.0
                        
                    try:
                        obp = float(cells[23]) if cells[23] != '.' else 0.0
                    except ValueError:
                        obp = 0.0
                    
                    name_kr = translate_player_name(name)
                    key = f"{name_kr} ({name} / {team_info['kr']})"
                    batters[key] = {
                        "name": name_kr,
                        "타율": avg,
                        "홈런": hr,
                        "출루율": obp,
                        "장타율": slg,
                        "도루": sb,
                        "team": team_info["kr"],
                        "team_jp": team_info["team_jp"],
                        "color": team_info["color"]
                    }
        except Exception as e:
            print(f"[ERROR] Scrape NPB leaders failed: {e}")
            
    return batters

# --- 크롤링 함수 (날짜별 스케줄 및 결과 조회) ---
def fetch_games_by_date(date_str):
    url = "https://baseball.yahoo.co.jp/npb/schedule/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    params = {'date': date_str}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        game_items = soup.find_all('li', class_='bb-score__item')
        
        games = []
        for item in game_items:
            home_el = item.find(class_=lambda x: x and 'bb-score__homeLogo' in x)
            away_el = item.find(class_=lambda x: x and 'bb-score__awayLogo' in x)
            
            home_team = home_el.text.strip() if home_el else "알 수 없음"
            away_team = away_el.text.strip() if away_el else "알 수 없음"
            
            score_left_el = item.find('span', class_='bb-score__score--left')
            score_right_el = item.find('span', class_='bb-score__score--right')
            
            score_left = score_left_el.text.strip() if score_left_el else ""
            score_right = score_right_el.text.strip() if score_right_el else ""
            
            status_el = item.find(class_=lambda x: x and 'bb-score__status' in x)
            status_text = status_el.text.strip() if status_el else ""
            
            link_el = item.find('p', class_='bb-score__link')
            link_text = link_el.text.strip() if link_el else ""
            
            desc_el = item.find('p', class_='bb-score__description')
            desc_text = desc_el.text.strip() if desc_el else ""
            
            a_el = item.find('a', class_='bb-score__content')
            detail_link = ""
            if a_el and 'href' in a_el.attrs:
                detail_link = "https://baseball.yahoo.co.jp" + a_el['href']
                
            # 포스트시즌 / 클라이맥스 시리즈 / 일본시리즈 여부 확인
            sec = item.find_parent('section')
            title_el = sec.find(class_='bb-score__title') if sec else None
            series_raw = title_el.text.strip() if title_el else ""
            series_name = ""
            if "ファーストステージ" in series_raw:
                series_name = "🍁 CS 퍼스트 스테이지"
            elif "ファイナルステージ" in series_raw:
                series_name = "🔥 CS 파이널 스테이지"
            elif "クライマックス" in series_raw or "CS" in series_raw:
                series_name = "🍁 클라이맥스 시리즈"
            elif "日本シリーズ" in series_raw:
                series_name = "🏆 SMBC 일본시리즈"
            
            games.append({
                'home': home_team,
                'away': away_team,
                'score_home': score_left,
                'score_away': score_right,
                'status': status_text,
                'link_text': link_text,
                'venue': desc_text,
                'detail_url': detail_link,
                'series': series_name
            })
        return games
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return []

# --- 포스트시즌 실시간 경기 크롤링 함수 ---
def fetch_postseason_live_games():
    url = "https://baseball.yahoo.co.jp/npb/schedule/?kind=postseason"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        postseason_games = []
        for sec in soup.find_all('section', class_='bb-score'):
            t_el = sec.find(class_='bb-score__title')
            title_raw = t_el.text.strip() if t_el else ""
            
            # 한국어 라벨로 매핑
            if "セ・ファースト" in title_raw:
                stage_label = "🍁 센트럴 리그 CS 퍼스트"
            elif "パ・ファースト" in title_raw:
                stage_label = "🍁 퍼시픽 리그 CS 퍼스트"
            elif "セ・ファイナル" in title_raw:
                stage_label = "🔥 센트럴 리그 CS 파이널"
            elif "パ・ファイナル" in title_raw:
                stage_label = "🔥 퍼시픽 리그 CS 파이널"
            elif "日本シリーズ" in title_raw:
                stage_label = "🏆 SMBC 일본시리즈"
            else:
                stage_label = title_raw if title_raw else "🍁 포스트시즌"
                
            for it in sec.find_all('li', class_='bb-score__item'):
                home_el = it.find(class_=lambda x: x and 'homeLogo' in x)
                away_el = it.find(class_=lambda x: x and 'awayLogo' in x)
                sc_l = it.find('span', class_='bb-score__score--left')
                sc_r = it.find('span', class_='bb-score__score--right')
                st_el = it.find('p', class_='bb-score__link') or it.find(class_='bb-score__status')
                desc = it.find('p', class_='bb-score__description')
                a_tag = it.find('a', class_='bb-score__content')
                
                postseason_games.append({
                    'stage': stage_label,
                    'home': home_el.text.strip() if home_el else "미정",
                    'away': away_el.text.strip() if away_el else "미정",
                    'score_home': sc_l.text.strip() if sc_l else "",
                    'score_away': sc_r.text.strip() if sc_r else "",
                    'status': st_el.text.strip() if st_el else "경기 전",
                    'venue': desc.text.strip() if desc else "구장 미정",
                    'detail_url': ('https://baseball.yahoo.co.jp' + a_tag['href']) if a_tag and 'href' in a_tag.attrs else ""
                })
        return postseason_games
    except Exception as e:
        print(f"[ERROR] fetch_postseason_live_games failed: {e}")
        return []

# --- 포스트시즌 마스터 일정 데이터 (CS & 일본시리즈) ---
POSTSEASON_MASTER_SCHEDULE = [
    # CS 퍼스트 스테이지
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "센트럴 리그",
        "game_num": "1차전",
        "date": "2026-10-10",
        "date_display": "10월 10일 (토)",
        "time": "14:00",
        "home": "요미우리 자이언츠 (2위)",
        "away": "요코하마 DeNA (3위)",
        "venue": "도쿄 돔",
        "rules": "3전 2선승제 (전 경기 2위 구장)",
        "status": "경기 종료"
    },
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "퍼시픽 리그",
        "game_num": "1차전",
        "date": "2026-10-10",
        "date_display": "10월 10일 (토)",
        "time": "14:00",
        "home": "세이부 라이온즈 (2위)",
        "away": "니혼햄 파이터즈 (3위)",
        "venue": "벨루나 돔",
        "rules": "3전 2선승제 (전 경기 2위 구장)",
        "status": "경기 종료"
    },
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "센트럴 리그",
        "game_num": "2차전",
        "date": "2026-10-11",
        "date_display": "10월 11일 (일)",
        "time": "14:00",
        "home": "요미우리 자이언츠 (2위)",
        "away": "요코하마 DeNA (3위)",
        "venue": "도쿄 돔",
        "rules": "3전 2선승제",
        "status": "진행 중 / 종료"
    },
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "퍼시픽 리그",
        "game_num": "2차전",
        "date": "2026-10-11",
        "date_display": "10월 11일 (일)",
        "time": "14:00",
        "home": "세이부 라이온즈 (2위)",
        "away": "니혼햄 파이터즈 (3위)",
        "venue": "벨루나 돔",
        "rules": "3전 2선승제",
        "status": "진행 중 / 종료"
    },
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "센트럴 리그",
        "game_num": "3차전",
        "date": "2026-10-12",
        "date_display": "10월 12일 (월)",
        "time": "14:00",
        "home": "요미우리 자이언츠 (2위)",
        "away": "요코하마 DeNA (3위)",
        "venue": "도쿄 돔",
        "rules": "동률 시 2위 진출 (1승 1패 시 진행)",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 퍼스트 스테이지",
        "stage_code": "cs_first",
        "league": "퍼시픽 리그",
        "game_num": "3차전",
        "date": "2026-10-12",
        "date_display": "10월 12일 (월)",
        "time": "14:00",
        "home": "세이부 라이온즈 (2위)",
        "away": "니혼햄 파이터즈 (3위)",
        "venue": "벨루나 돔",
        "rules": "동률 시 2위 진출 (1승 1패 시 진행)",
        "status": "경기 예정 (필요시)"
    },
    # CS 파이널 스테이지
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "1차전",
        "date": "2026-10-14",
        "date_display": "10월 14일 (수)",
        "time": "18:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "6전 4선승제 (1위팀 1승 어드밴티지)",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "1차전",
        "date": "2026-10-14",
        "date_display": "10월 14일 (수)",
        "time": "18:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "6전 4선승제 (1위팀 1승 어드밴티지)",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "2차전",
        "date": "2026-10-15",
        "date_display": "10월 15일 (목)",
        "time": "18:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "전 경기 1위 홈구장 개최",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "2차전",
        "date": "2026-10-15",
        "date_display": "10월 15일 (목)",
        "time": "18:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "전 경기 1위 홈구장 개최",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "3차전",
        "date": "2026-10-16",
        "date_display": "10월 16일 (금)",
        "time": "18:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "전 경기 1위 홈구장 개최",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "3차전",
        "date": "2026-10-16",
        "date_display": "10월 16일 (금)",
        "time": "18:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "전 경기 1위 홈구장 개최",
        "status": "경기 예정"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "4차전",
        "date": "2026-10-17",
        "date_display": "10월 17일 (토)",
        "time": "14:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "4승 선착 시 조기 종료",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "4차전",
        "date": "2026-10-17",
        "date_display": "10월 17일 (토)",
        "time": "18:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "4승 선착 시 조기 종료",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "5차전",
        "date": "2026-10-18",
        "date_display": "10월 18일 (일)",
        "time": "14:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "4승 선착 시 조기 종료",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "5차전",
        "date": "2026-10-18",
        "date_display": "10월 18일 (일)",
        "time": "14:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "4승 선착 시 조기 종료",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "센트럴 리그",
        "game_num": "6차전",
        "date": "2026-10-19",
        "date_display": "10월 19일 (월)",
        "time": "18:00",
        "home": "한신 타이거스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "한신 고시엔 구장",
        "rules": "최종 6차전 (동률 시 1위 진출)",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "CS 파이널 스테이지",
        "stage_code": "cs_final",
        "league": "퍼시픽 리그",
        "game_num": "6차전",
        "date": "2026-10-19",
        "date_display": "10월 19일 (월)",
        "time": "18:00",
        "home": "소프트뱅크 호크스 (1위)",
        "away": "CS 퍼스트 스테이지 승자",
        "venue": "미즈호 PayPay 돔 후쿠오카",
        "rules": "최종 6차전 (동률 시 1위 진출)",
        "status": "경기 예정 (필요시)"
    },
    # SMBC 일본시리즈
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "1차전",
        "date": "2026-10-24",
        "date_display": "10월 24일 (토)",
        "time": "18:30",
        "home": "센트럴 리그 우승팀",
        "away": "퍼시픽 리그 우승팀",
        "venue": "센트럴 홈구장",
        "rules": "7전 4선승제 (1·2차전 센트럴 홈)",
        "status": "경기 예정"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "2차전",
        "date": "2026-10-25",
        "date_display": "10월 25일 (일)",
        "time": "18:30",
        "home": "센트럴 리그 우승팀",
        "away": "퍼시픽 리그 우승팀",
        "venue": "센트럴 홈구장",
        "rules": "7전 4선승제",
        "status": "경기 예정"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "3차전",
        "date": "2026-10-27",
        "date_display": "10월 27일 (화)",
        "time": "18:30",
        "home": "퍼시픽 리그 우승팀",
        "away": "센트럴 리그 우승팀",
        "venue": "퍼시픽 홈구장",
        "rules": "3·4·5차전 퍼시픽 홈 (10/26 이동일)",
        "status": "경기 예정"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "4차전",
        "date": "2026-10-28",
        "date_display": "10월 28일 (수)",
        "time": "18:30",
        "home": "퍼시픽 리그 우승팀",
        "away": "센트럴 리그 우승팀",
        "venue": "퍼시픽 홈구장",
        "rules": "7전 4선승제",
        "status": "경기 예정"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "5차전",
        "date": "2026-10-29",
        "date_display": "10월 29일 (목)",
        "time": "18:30",
        "home": "퍼시픽 리그 우승팀",
        "away": "센트럴 리그 우승팀",
        "venue": "퍼시픽 홈구장",
        "rules": "4승 선착 시 조기 종료",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "6차전",
        "date": "2026-10-31",
        "date_display": "10월 31일 (토)",
        "time": "18:30",
        "home": "센트럴 리그 우승팀",
        "away": "퍼시픽 리그 우승팀",
        "venue": "센트럴 홈구장",
        "rules": "6·7차전 센트럴 홈 (10/30 이동일)",
        "status": "경기 예정 (필요시)"
    },
    {
        "stage": "SMBC 일본시리즈",
        "stage_code": "japan_series",
        "league": "NPB 통합 챔피언십",
        "game_num": "7차전",
        "date": "2026-11-01",
        "date_display": "11월 01일 (일)",
        "time": "18:30",
        "home": "센트럴 리그 우승팀",
        "away": "퍼시픽 리그 우승팀",
        "venue": "센트럴 홈구장",
        "rules": "최종 7차전 챔피언 결정전",
        "status": "경기 예정 (필요시)"
    }
]

# --- 선수 상세 기록 크롤링 함수 ---
def fetch_game_player_stats(stats_url, target_team_jp):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(stats_url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 페이지 내 모든 팀 링크들을 조회하여 일본어 팀 이름에 해당하는 ID 추출
        team_ids = {}
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/npb/teams/' in href:
                parts = href.split('/npb/teams/')
                if len(parts) > 1:
                    team_id = parts[1].split('/')[0]
                    team_name = a.text.strip()
                    if team_name and team_id.isdigit():
                        team_ids[team_name] = team_id
                        
        team_id = None
        for team_name, tid in team_ids.items():
            if target_team_jp in team_name or team_name in target_team_jp:
                team_id = tid
                break
                
        if not team_id:
            return [], []
            
        # 2. 타자 성적 테이블 파싱
        batters = []
        batting_table = soup.find('table', class_=lambda x: x and f'bb-statsTable--npbTeam{team_id}' in x)
        if batting_table:
            rows = batting_table.find_all('tr')
            for r in rows:
                tds = r.find_all('td')
                if len(tds) >= 14:
                    pos = tds[0].text.strip()
                    name = tds[1].text.strip()
                    if not name:
                        continue
                    avg = tds[2].text.strip()
                    ab = tds[3].text.strip()
                    r_val = tds[4].text.strip()
                    h = tds[5].text.strip()
                    rbi = tds[6].text.strip()
                    so = tds[7].text.strip()
                    bb_val = tds[8].text.strip()
                    hbp_val = tds[9].text.strip()
                    hr_val = tds[13].text.strip()
                    
                    try:
                        bb_num = int(bb_val) if bb_val.isdigit() else 0
                        hbp_num = int(hbp_val) if hbp_val.isdigit() else 0
                        sasagu = str(bb_num + hbp_num)
                    except Exception:
                        sasagu = bb_val
                    
                    batters.append({
                        '포지션': pos,
                        '선수명': translate_player_name(name),
                        '시즌타율': avg,
                        '타수': ab,
                        '득점': r_val,
                        '안타': h,
                        '타점': rbi,
                        '삼진': so,
                        '사사구': sasagu,
                        '홈런': hr_val
                    })
                    
        # 3. 투수 성적 테이블 파싱
        pitchers = []
        pitching_table = soup.find('table', class_=lambda x: x and f'bb-scoreTable--npbTeam{team_id}' in x)
        if pitching_table:
            rows = pitching_table.find_all('tr')
            for r in rows:
                tds = r.find_all('td')
                if len(tds) >= 14:
                    wl = tds[0].text.strip()
                    name = tds[1].text.strip()
                    if not name:
                        continue
                    era = tds[2].text.strip()
                    ip = tds[3].text.strip()
                    np = tds[4].text.strip()
                    bf = tds[5].text.strip()
                    h_val = tds[6].text.strip()
                    hr_val = tds[7].text.strip()
                    so_val = tds[8].text.strip()
                    bb_val = tds[9].text.strip()
                    hbp_val = tds[10].text.strip()
                    r_val = tds[12].text.strip()
                    er_val = tds[13].text.strip()
                    
                    try:
                        bb_num = int(bb_val) if bb_val.isdigit() else 0
                        hbp_num = int(hbp_val) if hbp_val.isdigit() else 0
                        sasagu = str(bb_num + hbp_num)
                    except Exception:
                        sasagu = bb_val
                        
                    pitchers.append({
                        '결과': wl,
                        '선수명': translate_player_name(name),
                        '시즌방어율': era,
                        '이닝': ip,
                        '투구수': np,
                        '피안타': h_val,
                        '피홈런': hr_val,
                        '탈삼진': so_val,
                        '사사구': sasagu,
                        '실점': r_val,
                        '자책점': er_val
                    })
                    
        return batters, pitchers
    except Exception as e:
        st.error(f"선수 기록 파싱 중 오류 발생: {e}")
        return [], []

def render_game_card(game, is_fav=False):
    home_jp = game['home']
    away_jp = game['away']
    
    home_info = TEAM_INFO.get(home_jp, {"kr": home_jp, "color": "#9ca3af"})
    away_info = TEAM_INFO.get(away_jp, {"kr": away_jp, "color": "#9ca3af"})
    
    score_home = game['score_home']
    score_away = game['score_away']
    
    status_text = game['status']
    link_text = game['link_text']
    
    # 경기 상태 포맷팅
    status_class = "status-upcoming"
    status_kr = "경기 예정"
    if "試合終了" in link_text or "試合終了" in status_text:
        status_class = "status-finished"
        status_kr = "경기 종료"
    elif score_home or score_away:
        status_class = "status-live"
        status_kr = f"진행 중 ({link_text if link_text else '실시간'})"
    else:
        status_kr = f"경기 전 ({status_text})"
    
    # 스코어 컬러 강조
    score_home_class = ""
    score_away_class = ""
    if score_home and score_away:
        try:
            sh = int(score_home)
            sa = int(score_away)
            if sh > sa:
                score_home_class = "score-winner"
                score_away_class = "score-loser"
            elif sa > sh:
                score_away_class = "score-winner"
                score_home_class = "score-loser"
        except ValueError:
            pass
            
    card_class = "match-card-fav" if is_fav else "match-card"
    
    series_badge = ""
    if game.get('series'):
        series_badge = f'<span class="badge-series" style="margin-left: 6px;">{game["series"]}</span>'
    
    # HTML 문자열에서 마크다운 파서 오작동(코드 블록 취급)을 방지하기 위해 
    # 내부에 들여쓰기가 전혀 들어가지 않도록 문자열을 작성하고 textwrap.dedent를 수행
    html_content = f"""<div class="{card_class}">
<div class="match-header">
<div class="match-venue">📍 {game['venue']} {series_badge}</div>
<span class="match-status-badge {status_class}">{status_kr}</span>
</div>
<div class="match-teams-container">
<div class="team-row">
<div class="team-info">
<div class="team-color-indicator" style="background-color: {home_info['color']};"></div>
<span class="team-name-kr">{home_info['kr']}</span>
<span class="team-name-jp">{home_jp}</span>
</div>
<span class="team-score-val {score_home_class}">{score_home if score_home else "-"}</span>
</div>
<div class="team-row">
<div class="team-info">
<div class="team-color-indicator" style="background-color: {away_info['color']};"></div>
<span class="team-name-kr">{away_info['kr']}</span>
<span class="team-name-jp">{away_jp}</span>
</div>
<span class="team-score-val {score_away_class}">{score_away if score_away else "-"}</span>
</div>
</div>"""

    if game['detail_url']:
        html_content += f"""<div style="margin-top: 15px; text-align: right; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 10px;">
<a href="{game['detail_url']}" target="_blank" style="font-size: 0.8rem; color: #3b82f6; text-decoration: none; font-weight: 600;">상세 기록/분석 보기 ↗</a>
</div>"""
    
    html_content += "</div>"
    st.markdown(textwrap.dedent(html_content), unsafe_allow_html=True)

# --- [두 번째 탭] 경기 결과 ---
with tab2:
    st.subheader("🔥 야구 경기 결과 및 스케줄 조회")
    
    current_team = st.session_state['my_team']
    
    st.markdown(f"### 📅 {selected_date.strftime('%Y년 %m월 %d일')} 경기")
    
    with st.spinner('경기 데이터를 불러오는 중...'):
        games = fetch_games_by_date(date_str)
        
        if not games:
            st.info("선택하신 날짜에 예정된 경기가 없거나 데이터를 불러올 수 없습니다.")
        else:
            fav_japanese_name = get_japanese_team_name(current_team)
            
            fav_games = []
            other_games = []
            
            for game in games:
                if fav_japanese_name in game['home'] or fav_japanese_name in game['away']:
                    fav_games.append(game)
                else:
                    other_games.append(game)
            
            # 최애 팀 경기 우선 출력
            if fav_games:
                st.markdown(f"#### 🌟 나의 최애 팀 ({current_team}) 경기")
                for game in fav_games:
                    render_game_card(game, is_fav=True)
                st.markdown("---")
            else:
                st.warning(f"선택하신 날짜에 '{current_team}'의 경기가 없습니다.")
            
            # 다른 경기 결과 출력
            if other_games:
                st.markdown("#### ⚾ 다른 경기 전체 보기")
                
                # 2열 그리드로 깔끔하게 배열
                cols = st.columns(2)
                for idx, game in enumerate(other_games):
                    col_idx = idx % 2
                    with cols[col_idx]:
                        render_game_card(game, is_fav=False)

# --- [포스트시즌 탭] 🍁 클라이맥스 시리즈 & 일본시리즈 ---
with tab_ps:
    st.subheader("🍁 일본 프로야구 포스트시즌 (클라이맥스 시리즈 & 일본시리즈)")
    st.markdown("가을야구의 꽃! 센트럴 리그 & 퍼시픽 리그의 **클라이맥스 시리즈(CS)** 및 최강자를 가리는 **SMBC 일본시리즈** 일정과 실시간 경기 결과를 한눈에 확인하세요.")

    # 1. 포스트시즌 토너먼트 대진 브라켓 (Bracket)
    st.markdown("### 🏆 2026 포스트시즌 토너먼트 대진표")
    
    col_bracket_c, col_bracket_vs, col_bracket_p = st.columns([5, 2, 5])
    
    with col_bracket_c:
        st.markdown("""
        <div class="bracket-card" style="border-left: 5px solid #ef4444;">
            <div style="font-weight: 700; font-size: 1.05rem; color: #ef4444; margin-bottom: 8px;">🔴 센트럴 리그 (Central League)</div>
            <div style="background: rgba(239, 68, 68, 0.06); padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <div style="font-size: 0.8rem; color: #64748b;">[파이널 스테이지 직행 (1승 우대)]</div>
                <div style="font-weight: 700; font-size: 1rem;">👑 한신 타이거스 (정규 1위)</div>
            </div>
            <div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin: 4px 0;">▲ 파이널 스테이지 대결</div>
            <div style="background: rgba(0, 0, 0, 0.03); padding: 10px; border-radius: 8px;">
                <div style="font-size: 0.8rem; color: #64748b;">[퍼스트 스테이지 3전 2선승제 (도쿄 돔)]</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-weight: 600;">🥈 요미우리 자이언츠 (2위)</span>
                    <span style="color: #64748b; font-weight: 700;">VS</span>
                    <span style="font-weight: 600;">🥉 요코하마 DeNA (3위)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_bracket_vs:
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 150px; text-align: center;">
            <div style="font-size: 2rem;">⚾</div>
            <div style="font-weight: 800; font-size: 0.95rem; color: #b45309; margin-top: 4px;">SMBC<br>일본시리즈</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">7전 4선승제</div>
        </div>
        """, unsafe_allow_html=True)

    with col_bracket_p:
        st.markdown("""
        <div class="bracket-card" style="border-left: 5px solid #3b82f6;">
            <div style="font-weight: 700; font-size: 1.05rem; color: #3b82f6; margin-bottom: 8px;">🔵 퍼시픽 리그 (Pacific League)</div>
            <div style="background: rgba(59, 130, 246, 0.06); padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <div style="font-size: 0.8rem; color: #64748b;">[파이널 스테이지 직행 (1승 우대)]</div>
                <div style="font-weight: 700; font-size: 1rem;">👑 소프트뱅크 호크스 (정규 1위)</div>
            </div>
            <div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin: 4px 0;">▲ 파이널 스테이지 대결</div>
            <div style="background: rgba(0, 0, 0, 0.03); padding: 10px; border-radius: 8px;">
                <div style="font-size: 0.8rem; color: #64748b;">[퍼스트 스테이지 3전 2선승제 (벨루나 돔)]</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span style="font-weight: 600;">🥈 세이부 라이온즈 (2위)</span>
                    <span style="color: #64748b; font-weight: 700;">VS</span>
                    <span style="font-weight: 600;">🥉 니혼햄 파이터즈 (3위)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. 실시간 포스트시즌 경기 현황 (라이브 스코어보드)
    st.markdown("---")
    st.markdown("### 🔴 오늘 진행 중인 포스트시즌 경기")
    
    col_btn_l, col_btn_r = st.columns([8, 2])
    with col_btn_r:
        if st.button("🔄 스코어 새로고침", use_container_width=True):
            st.rerun()
        
    with st.spinner("야후 재팬에서 실시간 포스트시즌 경기 데이터를 조회하는 중..."):
        ps_live_games = fetch_postseason_live_games()
        
    if not ps_live_games:
        st.info("현재 실시간 진행 중이거나 오늘 예정된 포스트시즌 경기가 없습니다. 아래 전체 일정표를 확인하세요.")
    else:
        ps_cols = st.columns(min(len(ps_live_games), 2))
        for idx, g in enumerate(ps_live_games):
            col_target = ps_cols[idx % 2]
            with col_target:
                h_name = TEAM_INFO.get(g['home'], {}).get('kr', g['home'])
                a_name = TEAM_INFO.get(g['away'], {}).get('kr', g['away'])
                h_col = TEAM_INFO.get(g['home'], {}).get('color', '#3b82f6')
                a_col = TEAM_INFO.get(g['away'], {}).get('color', '#ef4444')
                
                st_txt = g['status']
                is_live = any(x in st_txt for x in ['回', '表', '裏', '進行'])
                badge_bg = "rgba(239, 68, 68, 0.15)" if is_live else "#f1f5f9"
                badge_color = "#ef4444" if is_live else "#475569"
                
                card_html = f"""<div class="match-card" style="border: 2px solid #f59e0b;">
<div class="match-header">
<div class="match-venue">📍 {g['venue']} <span class="badge-series">{g['stage']}</span></div>
<span class="match-status-badge" style="background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color};">{st_txt}</span>
</div>
<div class="match-teams-container">
<div class="team-row">
<div class="team-info">
<div class="team-color-indicator" style="background-color: {h_col};"></div>
<span class="team-name-kr">{h_name}</span>
<span class="team-name-jp">{g['home']}</span>
</div>
<span class="team-score-val" style="font-size: 1.6rem; font-weight: 800;">{g['score_home'] if g['score_home'] else '-'}</span>
</div>
<div class="team-row">
<div class="team-info">
<div class="team-color-indicator" style="background-color: {a_col};"></div>
<span class="team-name-kr">{a_name}</span>
<span class="team-name-jp">{g['away']}</span>
</div>
<span class="team-score-val" style="font-size: 1.6rem; font-weight: 800;">{g['score_away'] if g['score_away'] else '-'}</span>
</div>
</div>"""
                if g['detail_url']:
                    card_html += f"""<div style="margin-top: 15px; text-align: right; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 10px;">
<a href="{g['detail_url']}" target="_blank" style="font-size: 0.85rem; color: #2563eb; text-decoration: none; font-weight: 700;">상세 경기 중계 및 라인업 보기 ↗</a>
</div>"""
                card_html += "</div>"
                st.markdown(textwrap.dedent(card_html), unsafe_allow_html=True)

    # 3. 전체 포스트시즌 일정표 (CS & 일본시리즈)
    st.markdown("---")
    st.markdown("### 📅 포스트시즌 전체 일정 및 타임라인")
    
    stage_filter = st.radio(
        "조회할 시리즈를 선택하세요:",
        ["📌 전체 일정", "🍁 CS 퍼스트 스테이지", "🔥 CS 파이널 스테이지", "🏆 SMBC 일본시리즈"],
        horizontal=True
    )
    
    if stage_filter == "🍁 CS 퍼스트 스테이지":
        filtered_schedule = [s for s in POSTSEASON_MASTER_SCHEDULE if s['stage_code'] == 'cs_first']
    elif stage_filter == "🔥 CS 파이널 스테이지":
        filtered_schedule = [s for s in POSTSEASON_MASTER_SCHEDULE if s['stage_code'] == 'cs_final']
    elif stage_filter == "🏆 SMBC 일본시리즈":
        filtered_schedule = [s for s in POSTSEASON_MASTER_SCHEDULE if s['stage_code'] == 'japan_series']
    else:
        filtered_schedule = POSTSEASON_MASTER_SCHEDULE
        
    df_ps = pd.DataFrame([{
        "시리즈": item["stage"],
        "라운드": item["game_num"],
        "날짜": item["date_display"],
        "시간": item["time"],
        "대진 (홈 vs 원정)": f"{item['home']} vs {item['away']}",
        "구장": item["venue"],
        "규정 / 비고": item["rules"],
        "상태": item["status"]
    } for item in filtered_schedule])
    
    st.dataframe(df_ps, use_container_width=True, hide_index=True)
    
    # 4. 시리즈 진행 방식 및 룰 가이드
    with st.expander("📖 클라이맥스 시리즈 & 일본시리즈 진행 규정 안내"):
        st.markdown("""
        * **🍁 CS 퍼스트 스테이지 (3전 2선승제)**:
            - 센트럴 & 퍼시픽 2위 팀 홈구장에서 전 경기 진행 (3연전)
            - 1승 1패 1무 등 동률일 경우 **정규시즌 2위 팀이 파이널 스테이지로 진출**합니다.
        * **🔥 CS 파이널 스테이지 (6전 4선승제)**:
            - 센트럴 & 퍼시픽 1위 팀 홈구장에서 전 경기 진행 (6연전)
            - **정규시즌 1위 팀에게 1승 어드밴티지**가 주어집니다 (실제로는 먼저 3승을 거두면 진출).
            - 무승부로 인해 동률로 시리즈가 끝나도 **정규시즌 1위 팀이 진출**합니다.
        * **🏆 SMBC 일본시리즈 (7전 4선승제)**:
            - 센트럴 리그 챔피언 vs 퍼시픽 리그 챔피언 맞대결
            - 1·2차전과 6·7차전은 짝수 해 센트럴 리그 홈구장, 홀수 해 퍼시픽 리그 홈구장에서 개최됩니다.
            - 7차전까지 무승부 등으로 승부가 결정되지 않으면 8차전 연장전이 진행됩니다.
        """)

# --- [세 번째 탭] 선수 상세 기록 ---
with tab3:
    current_team = st.session_state['my_team']
    st.subheader(f"🏃‍♂️ {current_team} 선수 상세 기록")
    
    fav_japanese_name = get_japanese_team_name(current_team)
    
    st.markdown(f"### 📅 {selected_date.strftime('%Y년 %m월 %d일')} 경기 기록")
    
    with st.spinner('경기 데이터를 조회하는 중...'):
        games = fetch_games_by_date(date_str)
        
    fav_game = None
    for game in games:
        if fav_japanese_name in game['home'] or fav_japanese_name in game['away']:
            fav_game = game
            break
            
    if not fav_game:
        st.warning(f"선택하신 날짜에 '{current_team}'의 경기가 없습니다.")
    else:
        home_jp = fav_game['home']
        away_jp = fav_game['away']
        home_kr = TEAM_INFO.get(home_jp, {"kr": home_jp})['kr']
        away_kr = TEAM_INFO.get(away_jp, {"kr": away_jp})['kr']
        
        st.markdown(f"#### ⚾ {home_kr} vs {away_kr} (📍 {fav_game['venue']})")
        st.info(f"**진행 상태**: {fav_game['score_home'] if fav_game['score_home'] else '-'} : {fav_game['score_away'] if fav_game['score_away'] else '-'} ({fav_game['link_text'] if fav_game['link_text'] else fav_game['status']})")
        
        if not fav_game['detail_url']:
            st.warning("이 경기의 상세 기록 URL을 가져올 수 없습니다.")
        else:
            stats_url = fav_game['detail_url'].replace('/index', '/stats')
            
            with st.spinner(f'{current_team}의 선수 상세 기록을 불러오는 중...'):
                batters, pitchers = fetch_game_player_stats(stats_url, fav_japanese_name)
                
            if not batters and not pitchers:
                st.warning("선수 경기 기록 정보가 아직 등록되지 않았거나 조회할 수 없습니다. (경기 전이거나 실시간 업데이트 지연)")
            else:
                # 타자 기록 출력
                if batters:
                    st.markdown("#### 🏃‍♂️ 타자 성적")
                    df_batters = pd.DataFrame(batters)
                    st.dataframe(df_batters, use_container_width=True, hide_index=True)
                    
                # 투수 기록 출력
                if pitchers:
                    st.markdown("#### 🥎 투수 성적")
                    df_pitchers = pd.DataFrame(pitchers)
                    st.dataframe(df_pitchers, use_container_width=True, hide_index=True)

    # --- [선수 능력치 비교 시뮬레이터] ---
    st.markdown("---")
    st.subheader("📊 NPB 규정타석 타자 스탯 비교 시뮬레이터")
    st.markdown("NPB 공식 홈페이지에서 실시간 규정타석 타자 데이터를 가져와 비교합니다. 구단별 필터를 사용해 선수를 간편하게 선택하고 스탯을 비교해 보세요.")

    # Star players database as fallback
    PLAYER_DATABASE = {
        "무라카미 무네타카 (야쿠르트)": {
            "name": "무라카미 무네타카",
            "타율": 0.280,
            "홈런": 35,
            "출루율": 0.380,
            "장타율": 0.550,
            "도루": 5,
            "team": "야쿠르트 스왈로스",
            "color": "#475569"
        },
        "야나기타 유키 (소프트뱅크)": {
            "name": "야나기타 유키",
            "타율": 0.305,
            "홈런": 22,
            "출루율": 0.395,
            "장타율": 0.510,
            "도루": 10,
            "team": "소프트뱅크 호크스",
            "color": "#FBBF24"
        },
        "오카모토 카즈마 (요미우리)": {
            "name": "오카모토 카즈마",
            "타율": 0.278,
            "홈런": 34,
            "출루율": 0.365,
            "장타율": 0.540,
            "도루": 2,
            "team": "요미우리 자이언츠",
            "color": "#F97316"
        },
        "콘도 健介 (소프트뱅크)": {
            "name": "콘도 켄스케",
            "타율": 0.299,
            "홈런": 25,
            "출루율": 0.418,
            "장타율": 0.554,
            "도루": 9,
            "team": "소프트뱅크 호크스",
            "color": "#EAB308"
        },
        "아키야마 쇼고 (히로시마)": {
            "name": "아키야마 쇼고",
            "타율": 0.285,
            "홈런": 6,
            "출루율": 0.345,
            "장타율": 0.380,
            "도루": 8,
            "team": "히로시마 도요 카프",
            "color": "#EF4444"
        },
        "사토 테루아키 (한신)": {
            "name": "사토 테루아키",
            "타율": 0.353,
            "홈런": 15,
            "출루율": 0.435,
            "장타율": 0.670,
            "도루": 4,
            "team": "한신 타이거스",
            "color": "#EAB308"
        },
        "만나미 츄세이 (니혼햄)": {
            "name": "만나미 츄세이",
            "타율": 0.265,
            "홈런": 25,
            "출루율": 0.320,
            "장타율": 0.470,
            "도루": 4,
            "team": "니혼햄 파이터즈",
            "color": "#06B6D4"
        },
        "겐다 소스케 (세이부)": {
            "name": "겐다 소스케",
            "타율": 0.250,
            "홈런": 1,
            "출루율": 0.310,
            "장타율": 0.300,
            "도루": 15,
            "team": "세이부 라이온즈",
            "color": "#2563EB"
        }
    }

    # Fetch from NPB with cache and fallback
    @st.cache_data(ttl=3600)
    def get_cached_qualified_batters():
        try:
            res = fetch_qualified_batters()
            if res:
                return res
        except Exception:
            pass
        return {}

    all_batters = get_cached_qualified_batters()
    if not all_batters:
        all_batters = PLAYER_DATABASE

    # Unique list of teams in the database
    teams_list = sorted(list(set(player["team"] for player in all_batters.values())))
    teams_options = ["전체"] + teams_list

    # Filters and Dropdowns for Player 1 & Player 2
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        st.markdown("##### 👤 첫 번째 선수")
        p1_team_filter = st.selectbox("구단 필터 (선수 1)", options=teams_options, key="p1_team_filter")
        
        # Filter player list based on selected team
        if p1_team_filter == "전체":
            p1_options = list(all_batters.keys())
        else:
            p1_options = [k for k, v in all_batters.items() if v["team"] == p1_team_filter]
            
        if not p1_options: # Fallback if empty
            p1_options = list(all_batters.keys())
            
        player1_name = st.selectbox("선수 1 선택", options=p1_options, key="player1_select")

    with col_filter2:
        st.markdown("##### 👤 두 번째 선수")
        p2_team_filter = st.selectbox("구단 필터 (선수 2)", options=teams_options, key="p2_team_filter")
        
        # Filter player list based on selected team
        if p2_team_filter == "전체":
            p2_options = list(all_batters.keys())
        else:
            p2_options = [k for k, v in all_batters.items() if v["team"] == p2_team_filter]
            
        if not p2_options: # Fallback if empty
            p2_options = list(all_batters.keys())
            
        # Try to select the second option as default if available
        default_p2_idx = 1 if len(p2_options) > 1 else 0
        player2_name = st.selectbox("선수 2 선택", options=p2_options, index=default_p2_idx, key="player2_select")

    p1_data = all_batters[player1_name]
    p2_data = all_batters[player2_name]

    # Metrics limits for normalization
    METRIC_LIMITS = {
        "타율": {"min": 0.200, "max": 0.350, "format": "{:.3f}", "unit": ""},
        "홈런": {"min": 0.0, "max": 50.0, "format": "{:.0f}", "unit": "개"},
        "출루율": {"min": 0.250, "max": 0.450, "format": "{:.3f}", "unit": ""},
        "장타율": {"min": 0.300, "max": 0.650, "format": "{:.3f}", "unit": ""},
        "도루": {"min": 0.0, "max": 40.0, "format": "{:.0f}", "unit": "개"}
    }

    def normalize(val, limit):
        scaled = 100 * (val - limit["min"]) / (limit["max"] - limit["min"])
        return max(0.0, min(100.0, scaled))

    categories = list(METRIC_LIMITS.keys())
    categories_closed = categories + [categories[0]]
    
    p1_vals_norm = [normalize(p1_data[cat], METRIC_LIMITS[cat]) for cat in categories]
    p1_vals_norm_closed = p1_vals_norm + [p1_vals_norm[0]]
    
    p2_vals_norm = [normalize(p2_data[cat], METRIC_LIMITS[cat]) for cat in categories]
    p2_vals_norm_closed = p2_vals_norm + [p2_vals_norm[0]]

    # Formatted hovertext
    p1_hover = [f"{cat}: {METRIC_LIMITS[cat]['format'].format(p1_data[cat])}{METRIC_LIMITS[cat]['unit']}" for cat in categories]
    p1_hover_closed = p1_hover + [p1_hover[0]]
    
    p2_hover = [f"{cat}: {METRIC_LIMITS[cat]['format'].format(p2_data[cat])}{METRIC_LIMITS[cat]['unit']}" for cat in categories]
    p2_hover_closed = p2_hover + [p2_hover[0]]

    # Create Plotly Radar Chart
    fig = go.Figure()

    # Player 1 Trace
    fig.add_trace(go.Scatterpolar(
        r=p1_vals_norm_closed,
        theta=categories_closed,
        fill='toself',
        name=player1_name,
        hoverinfo='text',
        text=p1_hover_closed,
        line=dict(color=p1_data["color"], width=2),
        fillcolor=p1_data["color"],
        opacity=0.3
    ))

    # Player 2 Trace
    fig.add_trace(go.Scatterpolar(
        r=p2_vals_norm_closed,
        theta=categories_closed,
        fill='toself',
        name=player2_name,
        hoverinfo='text',
        text=p2_hover_closed,
        line=dict(color=p2_data["color"], width=2),
        fillcolor=p2_data["color"],
        opacity=0.3
    ))

    # Layout styling
    text_color = "#f8fafc" if st.session_state['dark_mode'] else "#0f172a"
    grid_color = "#334155" if st.session_state['dark_mode'] else "#cbd5e1"
    bg_color = "rgba(30, 41, 59, 0.5)" if st.session_state['dark_mode'] else "rgba(255, 255, 255, 0.5)"

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                gridcolor=grid_color,
                linecolor=grid_color
            ),
            angularaxis=dict(
                gridcolor=grid_color,
                linecolor=grid_color,
                tickfont=dict(size=12, color=text_color, family="Noto Sans KR, sans-serif")
            ),
            bgcolor=bg_color
        ),
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=text_color),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=text_color)
        ),
        margin=dict(t=30, b=40, l=40, r=40),
        height=450
    )

    # Use 2-column layout: Left contains stat table, Right contains the radar chart
    col_table, col_chart = st.columns([1, 1.2])

    with col_table:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        # Create comparison dataframe
        comparison_df = pd.DataFrame({
            "지표": categories,
            p1_data["name"]: [f"{METRIC_LIMITS[c]['format'].format(p1_data[c])}{METRIC_LIMITS[c]['unit']}" for c in categories],
            p2_data["name"]: [f"{METRIC_LIMITS[c]['format'].format(p2_data[c])}{METRIC_LIMITS[c]['unit']}" for c in categories],
        })
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Add team info cards
        st.markdown(f"""
        <div style="padding: 12px; border-radius: 8px; background-color: {p1_data['color']}22; border: 1px solid {p1_data['color']}; margin-top: 10px; color: {text_color};">
            <strong>{p1_data['name']}</strong>: {p1_data['team']}
        </div>
        <div style="padding: 12px; border-radius: 8px; background-color: {p2_data['color']}22; border: 1px solid {p2_data['color']}; margin-top: 10px; color: {text_color};">
            <strong>{p2_data['name']}</strong>: {p2_data['team']}
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        st.plotly_chart(fig, use_container_width=True)

# --- [네 번째 탭] 구장 및 공식 사이트 ---
with tab4:
    st.subheader("🏟️ 구단별 홈 구장 및 공식 웹사이트")
    
    # 세션 상태의 최애 팀을 기반으로 기본값 설정
    current_fav = st.session_state.get('my_team', "소프트뱅크")
    fav_jp = get_japanese_team_name(current_fav)
    
    default_idx = 0
    stadium_keys = list(TEAM_STADIUM_INFO.keys())
    if fav_jp in TEAM_STADIUM_INFO:
        default_idx = stadium_keys.index(fav_jp)
        
    selected_key = st.selectbox(
        "정보를 조회할 구단을 선택하세요",
        options=stadium_keys,
        index=default_idx,
        format_func=lambda x: f"{TEAM_STADIUM_INFO[x]['team_name_kr']} ({x})"
    )
    
    info = TEAM_STADIUM_INFO[selected_key]
    team_color = TEAM_INFO.get(selected_key, {"color": "#9ca3af"})["color"]
    
    # 2열 레이아웃: 왼쪽 정보 카드, 오른쪽 지도
    col_info, col_map = st.columns([1, 1.2])
    
    with col_info:
        card_html = f"""<div class="stadium-card" style="border-left: 6px solid {team_color};">
<h3 style="margin-top: 0; margin-bottom: 6px; font-size: 1.5rem; font-weight: 700;">{info['team_name_kr']}</h3>
<p style="font-size: 0.9rem; margin-top: 0; margin-bottom: 24px;">NPB 구단 코드: {selected_key}</p>
<div style="margin-bottom: 16px;">
<span style="font-weight: 600; display: block; margin-bottom: 4px; font-size: 0.85rem;">🏟️ 홈 구장</span>
<span style="font-size: 1.15rem; font-weight: 700; display: block;">{info['stadium_kr']}</span>
<span style="font-size: 0.9rem; display: block; margin-top: 2px;">{info['stadium_jp']}</span>
</div>
<div style="margin-bottom: 24px;">
<span style="font-weight: 600; display: block; margin-bottom: 4px; font-size: 0.85rem;">📍 구장 주소</span>
<span style="font-size: 0.95rem; line-height: 1.5; display: block;">{info['address']}</span>
</div>
<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
<a href="{info['website']}" target="_blank" style="
display: block;
background-color: {team_color};
color: white !important;
text-decoration: none;
padding: 10px 16px;
border-radius: 8px;
font-weight: 600;
font-size: 0.9rem;
text-align: center;
box-shadow: 0 2px 8px rgba(0,0,0,0.08);
transition: opacity 0.2s;
" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
🌐 구단 공식 홈페이지 방문 ↗
</a>
<a href="https://www.google.com/maps/search/?api=1&query={info['lat']},{info['lon']}" target="_blank" style="
display: block;
background-color: #f3f4f6;
color: #374151 !important;
text-decoration: none;
padding: 10px 16px;
border-radius: 8px;
font-weight: 600;
font-size: 0.9rem;
text-align: center;
border: 1px solid #d1d5db;
transition: background-color 0.2s;
" onmouseover="this.style.backgroundColor='#e5e7eb'" onmouseout="this.style.backgroundColor='#f3f4f6'">
🗺️ Google 지도에서 검색 ↗
</a>
</div>
</div>"""
        st.markdown(textwrap.dedent(card_html), unsafe_allow_html=True)
        
    with col_map:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        
        stadium_mapping = {
            "ソフトバンク": "PayPay Dome",
            "巨人": "Tokyo Dome",
            "阪神": "Koshien Stadium"
        }
        
        has_precision = selected_key in stadium_mapping
        
        if has_precision:
            stadium_name = stadium_mapping[selected_key]
            st.markdown(f"### 📐 {stadium_name} 실시간 정밀 측량 시뮬레이터")
            
            defaults = stadium_layouts.STADIUM_DEFAULTS[stadium_name]
            poly_coords = stadium_layouts.STADIUM_POLYGONS[stadium_name]
            
            # 펜스 및 홈플레이트 미세 조정 패널
            with st.expander("🛠️ 홈플레이트 위치 & 펜스 측정선 세부 조정", expanded=True):
                col_ctrl1, col_ctrl2 = st.columns(2)
                with col_ctrl1:
                    hp_lat = st.number_input("홈플레이트 위도 (Latitude)", value=defaults["home_plate"][0], format="%.6f", step=0.00001, key=f"hp_lat_{stadium_name}")
                    hp_lon = st.number_input("홈플레이트 경도 (Longitude)", value=defaults["home_plate"][1], format="%.6f", step=0.00001, key=f"hp_lon_{stadium_name}")
                    bearing = st.slider("구장 방향 각도 (CF Bearing, 도)", min_value=0.0, max_value=360.0, value=defaults["bearing"], step=0.1, key=f"bearing_{stadium_name}")
                with col_ctrl2:
                    left_m = st.slider("좌선 펜스 거리 (Left Pole, m)", min_value=80.0, max_value=150.0, value=defaults["left_m"], step=0.5, key=f"left_m_{stadium_name}")
                    l_center_m = st.slider("좌중간 펜스 거리 (Left-Center, m)", min_value=90.0, max_value=150.0, value=defaults["l_center_m"], step=0.5, key=f"l_center_{stadium_name}")
                    center_m = st.slider("중앙 펜스 거리 (Center, m)", min_value=100.0, max_value=150.0, value=defaults["center_m"], step=0.5, key=f"center_m_{stadium_name}")
                    r_center_m = st.slider("우중간 펜스 거리 (Right-Center, m)", min_value=90.0, max_value=150.0, value=defaults["r_center_m"], step=0.5, key=f"r_center_{stadium_name}")
                    right_m = st.slider("우선 펜스 거리 (Right Pole, m)", min_value=80.0, max_value=150.0, value=defaults["right_m"], step=0.5, key=f"right_m_{stadium_name}")

            home_plate = (hp_lat, hp_lon)
            
            # 건물 면적 계산
            building_area = stadium_layouts.calculate_polygon_area(poly_coords)
            building_area_py = building_area * 0.3025
            
            # 외야 펜스 점 계산
            outfield_pts = stadium_layouts.get_outfield_points(
                home_plate, bearing, left_m, l_center_m, center_m, r_center_m, right_m
            )
            
            # 경기장(Playing Field) 면적 계산
            playing_field_area = stadium_layouts.get_playing_field_area(home_plate, outfield_pts)
            playing_field_area_py = playing_field_area * 0.3025
            
            # 면적 측정 메트릭 표시
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric(
                    label="🏟️ 구장 전체 건물 면적 (OSM 실측)", 
                    value=f"{building_area:,.1f} ㎡",
                    help="OpenStreetMap의 건물 외곽선 폴리곤 좌표를 미터법 투영 후 산출한 실측 면적입니다."
                )
                st.caption(f"(약 {building_area_py:,.1f} 평)")
            with col_m2:
                st.metric(
                    label="⚾ 규격 기준 경기장 면적 (Playing Field)", 
                    value=f"{playing_field_area:,.1f} ㎡",
                    help="홈플레이트에서 파울 라인과 외야 펜스로 둘러싸인 플레이 영역의 총 면적입니다."
                )
                st.caption(f"(약 {playing_field_area_py:,.1f} 평)")

            # 지도 생성
            map_center = [defaults["center_coords"][0], defaults["center_coords"][1]]
            m = folium.Map(location=map_center, zoom_start=18, max_zoom=21, tiles="OpenStreetMap")
            
            # 1. 구장 건물 폴리곤
            folium.Polygon(
                locations=poly_coords,
                color="#2563eb" if not st.session_state['dark_mode'] else "#38bdf8",
                weight=3,
                fill=True,
                fill_color="#3b82f6" if not st.session_state['dark_mode'] else "#0284c7",
                fill_opacity=0.15,
                tooltip=f"<b>{stadium_name} 건물 외곽선</b><br>실측 면적: {building_area:,.1f}㎡ ({building_area_py:,.1f}평)"
            ).add_to(m)
            
            # 2. 경기장 다각형 영역
            folium.Polygon(
                locations=[home_plate] + [
                    outfield_pts["left"],
                    outfield_pts["l_center"],
                    outfield_pts["center"],
                    outfield_pts["r_center"],
                    outfield_pts["right"]
                ] + [home_plate],
                color="#10b981" if not st.session_state['dark_mode'] else "#34d399",
                weight=1,
                fill=True,
                fill_color="#10b981" if not st.session_state['dark_mode'] else "#059669",
                fill_opacity=0.12,
                tooltip=f"<b>경기장 면적 (Playing Field)</b><br>계산 면적: {playing_field_area:,.1f}㎡"
            ).add_to(m)
            
            # 3. 홈플레이트 마커
            folium.Marker(
                location=home_plate,
                popup="<b>홈플레이트 (Home Plate)</b><br>측량 중심점",
                tooltip="홈플레이트",
                icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
            ).add_to(m)
            
            # 4. 외야 펜스 궤적 (Arc)
            fence_coords = [
                outfield_pts["left"],
                outfield_pts["l_center"],
                outfield_pts["center"],
                outfield_pts["r_center"],
                outfield_pts["right"]
            ]
            folium.PolyLine(
                locations=fence_coords,
                color="#e11d48",
                weight=4,
                tooltip="외야 펜스 (Outfield Fence)"
            ).add_to(m)
            
            # 5. 파울 라인 (Foul Lines)
            folium.PolyLine(
                locations=[home_plate, outfield_pts["left"]],
                color="#4b5563" if not st.session_state['dark_mode'] else "#94a3b8",
                weight=3,
                dash_array="5, 5",
                tooltip=f"좌측 파울 라인 (Left Foul Line: {left_m}m)"
            ).add_to(m)
            
            folium.PolyLine(
                locations=[home_plate, outfield_pts["right"]],
                color="#4b5563" if not st.session_state['dark_mode'] else "#94a3b8",
                weight=3,
                dash_array="5, 5",
                tooltip=f"우측 파울 라인 (Right Foul Line: {right_m}m)"
            ).add_to(m)
            
            # 6. 정밀 측량 방사형선 및 라벨
            measurement_lines = [
                ("좌익선 (Left Line)", outfield_pts["left"], left_m, "#d97706"),
                ("좌중간 (Left-Center)", outfield_pts["l_center"], l_center_m, "#0891b2"),
                ("중견선 (Center Line)", outfield_pts["center"], center_m, "#dc2626"),
                ("우중간 (Right-Center)", outfield_pts["r_center"], r_center_m, "#0891b2"),
                ("우익선 (Right Line)", outfield_pts["right"], right_m, "#d97706")
            ]
            
            for label, pt, dist, color in measurement_lines:
                # 방사형 측정선 그리기
                folium.PolyLine(
                    locations=[home_plate, pt],
                    color=color,
                    weight=2,
                    dash_array="3, 3"
                ).add_to(m)
                
                # 외야 펜스 끝점에 거리 라벨 마커 추가
                folium.Marker(
                    location=pt,
                    tooltip=f"{label}: {dist:.1f}m",
                    icon=folium.DivIcon(
                        html=f"""<div style="
                            background-color: {color};
                            color: white;
                            font-size: 10px;
                            font-weight: 700;
                            padding: 2px 5px;
                            border-radius: 4px;
                            border: 1px solid white;
                            white-space: nowrap;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                        ">{dist:.1f}m</div>"""
                    )
                ).add_to(m)
            
            # Streamlit-Folium 렌더링
            st_folium(m, height=500, use_container_width=True)
            
        else:
            st.warning("⚠️ 이 구단은 기본 지도만 제공됩니다. 소프트뱅크(PayPay 돔), 요미우리(도쿄 돔), 한신(고시엔 구장) 중 하나를 선택하면 정밀 측량 시뮬레이터 기능을 사용할 수 있습니다!")
            map_data = pd.DataFrame([{
                'lat': info['lat'],
                'lon': info['lon']
            }])
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.map(map_data, zoom=14, use_container_width=True)

# --- [다섯 번째 탭] 리그 순위표 ---
with tab5:
    st.subheader("🏆 일본 프로야구 리그 순위표")
    
    with st.spinner('실시간 리그 순위를 불러오는 중...'):
        central_teams, pacific_teams = fetch_league_standings()
        
    if not central_teams or not pacific_teams:
        st.error("리그 순위를 불러올 수 없습니다. 일시적인 야후 스포츠 오류일 수 있습니다.")
    else:
        col_central, col_pacific = st.columns(2)
        
        with col_central:
            st.markdown("### 🔴 센트럴 리그 순위")
            df_central = pd.DataFrame(central_teams)
            st.dataframe(df_central, use_container_width=True, hide_index=True)
            
        with col_pacific:
            st.markdown("### 🔵 퍼시픽 리그 순위")
            df_pacific = pd.DataFrame(pacific_teams)
            st.dataframe(df_pacific, use_container_width=True, hide_index=True)
            
        st.caption("💡 **게임차 안내**: 일본 야후 스포츠 원본은 '바로 앞 팀과의 게임차'를 표시하지만, 본 대시보드에서는 한국 및 글로벌 야구 표준인 **'1위 팀 기준 승차(누적)'**로 자동 환산하여 일관되게 제공합니다. ('앞 팀 차' 열에서 원본 차이도 확인 가능)")

# --- [여섯 번째 탭] 주요 야구 뉴스 ---
with tab6:
    st.subheader("📰 오늘의 주요 야구 뉴스")
    
    with st.spinner('실시간 주요 야구 뉴스를 불러오는 중...'):
        news_items = fetch_npb_news()
        
    if not news_items:
        st.info("오늘 등록된 주요 야구 뉴스가 없거나 기사를 불러올 수 없습니다.")
    else:
        # 뉴스 항목 카드 형태로 출력
        for idx, item in enumerate(news_items):
            card_html = f"""<div class="news-card">
<span style="font-weight: 700; font-size: 1.05rem; display: block; margin-bottom: 8px;">{idx+1}. {item['title']}</span>
<div style="text-align: right;">
<a href="{item['url']}" target="_blank" style="
font-size: 0.85rem;
color: #2563eb !important;
text-decoration: none;
font-weight: 600;
">기사 읽기 ↗</a>
</div>
</div>"""
            st.markdown(textwrap.dedent(card_html), unsafe_allow_html=True)
