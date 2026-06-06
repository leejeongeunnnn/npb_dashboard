import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import textwrap
import pandas as pd

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
            for r in rows:
                tds = r.find_all('td')
                if len(tds) >= 8:
                    rank = tds[0].text.strip()
                    name = tds[1].find('a').text.strip() if tds[1].find('a') else tds[1].text.strip()
                    games = tds[2].text.strip()
                    wins = tds[3].text.strip()
                    losses = tds[4].text.strip()
                    draws = tds[5].text.strip()
                    pct = tds[6].text.strip()
                    diff = tds[7].text.strip()
                    
                    teams.append({
                        '순위': rank,
                        '팀명': TEAM_INFO.get(name, {"kr": name})["kr"],
                        '경기': games,
                        '승': wins,
                        '패': losses,
                        '무': draws,
                        '승률': pct,
                        '게임차': diff
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

# ★ 2. 화면을 6개의 탭(메뉴)으로 깔끔하게 나누기
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["⚙️ 팀 설정", "🔥 경기 결과", "🏃‍♂️ 선수 상세 기록", "🏟️ 구장 및 공식 사이트", "🏆 리그 순위표", "📰 주요 야구 뉴스"])

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
            
            games.append({
                'home': home_team,
                'away': away_team,
                'score_home': score_left,
                'score_away': score_right,
                'status': status_text,
                'link_text': link_text,
                'venue': desc_text,
                'detail_url': detail_link
            })
        return games
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return []

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
                        '선수명': name,
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
                        '선수명': name,
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
    
    # HTML 문자열에서 마크다운 파서 오작동(코드 블록 취급)을 방지하기 위해 
    # 내부에 들여쓰기가 전혀 들어가지 않도록 문자열을 작성하고 textwrap.dedent를 수행
    html_content = f"""<div class="{card_class}">
<div class="match-header">
<div class="match-venue">📍 {game['venue']}</div>
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
