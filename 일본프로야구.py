import requests
from bs4 import BeautifulSoup
import asyncio
import os
import json
import datetime
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ★ 1. BotFather에게 받은 진짜 토큰 ★
BOT_TOKEN = "8614528998:AAH5__fE-y4CPeOW76Kri4kFALa8WRwN8pM"

SUBSCRIBERS_FILE = "subscribers.json"
FAVORITE_TEAMS_FILE = "favorite_teams.json"

# 각 팀의 한국어 명칭 및 정보
TEAM_INFO = {
    "巨人": {"kr": "요미우리 자이언츠"},
    "阪神": {"kr": "한신 타이거스"},
    "中日": {"kr": "주니치 드래곤즈"},
    "DeNA": {"kr": "요코하마 DeNA 베이스타스"},
    "ヤクルト": {"kr": "야쿠르트 스왈로스"},
    "広島": {"kr": "히로시마 도요 카프"},
    "ソフトバンク": {"kr": "소프트뱅크 호크스"},
    "オリックス": {"kr": "오릭스 버팔로즈"},
    "ロッテ": {"kr": "지바 롯데 마린스"},
    "楽天": {"kr": "라쿠텐 골든이글스"},
    "西武": {"kr": "세이부 라이온즈"},
    "日本ハム": {"kr": "니혼햄 파이터즈"}
}

# 입력한 한글 팀명 -> 표준 명칭 매핑
TEAM_MAPPING = {
    "소프트뱅크": "소프트뱅크 호크스",
    "소프트뱅크 호크스": "소프트뱅크 호크스",
    "오릭스": "오릭스 버팔로즈",
    "오릭스 버팔로즈": "오릭스 버팔로즈",
    "롯데": "지바 롯데 마린스",
    "지바롯데": "지바 롯데 마린스",
    "지바 롯데": "지바 롯데 마린스",
    "지바 롯데 마린스": "지바 롯데 마린스",
    "라쿠텐": "라쿠텐 골든이글스",
    "라쿠텐 골든이글스": "라쿠텐 골든이글스",
    "세이부": "세이부 라이온즈",
    "세이부 라이온즈": "세이부 라이온즈",
    "니혼햄": "니혼햄 파이터즈",
    "니혼햄 파이터즈": "니혼햄 파이터즈",
    "요미우리": "요미우리 자이언츠",
    "자이언츠": "요미우리 자이언츠",
    "요미우리 자이언츠": "요미우리 자이언츠",
    "한신": "한신 타이거스",
    "한신 타이거스": "한신 타이거스",
    "주니치": "주니치 드래곤즈",
    "주니치 드래곤즈": "주니치 드래곤즈",
    "요코하마": "요코하마 DeNA 베이스타스",
    "데나": "요코하마 DeNA 베이스타스",
    "요코하마 DeNA 베이스타스": "요코하마 DeNA 베이스타스",
    "야쿠르트": "야쿠르트 스왈로스",
    "야쿠르트 스왈로스": "야쿠르트 스왈로스",
    "히로시마": "히로시마 도요 카프",
    "히로시마 도요 카프": "히로시마 도요 카프"
}

# 최애 팀 로드 및 저장
def load_favorite_teams():
    if os.path.exists(FAVORITE_TEAMS_FILE):
        try:
            with open(FAVORITE_TEAMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_favorite_teams(favs):
    try:
        with open(FAVORITE_TEAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(favs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to save favorite teams: {e}")

SENT_ALERTS_FILE = "sent_alerts.json"

def load_sent_alerts():
    if os.path.exists(SENT_ALERTS_FILE):
        try:
            with open(SENT_ALERTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_sent_alerts(alerts):
    try:
        with open(SENT_ALERTS_FILE, "w") as f:
            json.dump(alerts[-100:], f)
    except Exception as e:
        print(f"[ERROR] Save sent alerts failed: {e}")

def translate_team(jp_name):
    return TEAM_INFO.get(jp_name, {}).get("kr", jp_name)

# 구독자 파일 로드 및 저장
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_subscribers(subs):
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(list(subs), f)
    except Exception as e:
        print(f"[ERROR] Failed to save subscribers: {e}")

# 야후 재팬 실시간 경기 데이터 크롤링 함수 (선발/기록 정보 추가 추출)
def fetch_today_games_raw():
    url = "https://baseball.yahoo.co.jp/npb/schedule/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        game_items = soup.find_all('li', class_='bb-score__item')
        
        games = {}
        for item in game_items:
            home_el = item.find(class_=lambda x: x and 'bb-score__homeLogo' in x)
            away_el = item.find(class_=lambda x: x and 'bb-score__awayLogo' in x)
            if not home_el or not away_el:
                continue
            home_team = home_el.text.strip()
            away_team = away_el.text.strip()
            
            score_left_el = item.find('span', class_='bb-score__score--left')
            score_right_el = item.find('span', class_='bb-score__score--right')
            score_home = score_left_el.text.strip() if score_left_el else ""
            score_away = score_right_el.text.strip() if score_right_el else ""
            
            status_el = item.find(class_=lambda x: x and 'bb-score__status' in x)
            status_text = status_el.text.strip() if status_el else ""
            
            link_el = item.find('p', class_='bb-score__link')
            link_text = link_el.text.strip() if link_el else ""
            
            desc_el = item.find('p', class_='bb-score__description')
            desc_text = desc_el.text.strip() if desc_el else ""
            
            p_home_el = item.find('div', class_='bb-score__playerHome')
            p_away_el = item.find('div', class_='bb-score__playerAway')
            p_home = p_home_el.text.strip() if p_home_el else ""
            p_away = p_away_el.text.strip() if p_away_el else ""
            
            game_key = f"{away_team}_vs_{home_team}"
            games[game_key] = {
                'home': home_team,
                'away': away_team,
                'score_home': score_home,
                'score_away': score_away,
                'status': status_text,
                'link_text': link_text,
                'venue': desc_text,
                'pitcher_home': p_home,
                'pitcher_away': p_away
            }
        return games
    except Exception as e:
        print(f"[ERROR] Fetch games failed: {e}")
        return {}

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
                        'rank': rank,
                        'name': name,
                        'games': games,
                        'wins': wins,
                        'losses': losses,
                        'draws': draws,
                        'pct': pct,
                        'diff': diff
                    })
            return teams
            
        central_teams = parse_table(tables[0])
        pacific_teams = parse_table(tables[1])
        return central_teams, pacific_teams
    except Exception as e:
        print(f"[ERROR] Fetch standings failed: {e}")
        return None, None

# 백그라운드 실시간 경기 상태/득점 모니터링 태스크
async def score_monitor_loop(app: Application):
    previous_games = {}
    print("[SYSTEM] Background score monitor loop started.")
    
    await asyncio.sleep(5)
    
    while True:
        try:
            current_games = fetch_today_games_raw()
            if current_games:
                # 1. 경기 시작 10분 전 알림 감시 (이전 데이터의 유무와 상관없이 동작)
                for key, current in current_games.items():
                    home_kr = translate_team(current['home'])
                    away_kr = translate_team(current['away'])
                    
                    # 경기 예정 상태이고 시작 시간이 status에 적혀있을 때
                    time_match = re.match(r"^(\d{1,2}):(\d{2})$", current['status'].strip())
                    if time_match and current['score_home'] == "" and current['score_away'] == "":
                        game_hour = int(time_match.group(1))
                        game_minute = int(time_match.group(2))
                        
                        now = datetime.datetime.now()
                        game_time = datetime.datetime.combine(now.date(), datetime.time(game_hour, game_minute))
                        time_diff = (game_time - now).total_seconds() / 60.0
                        
                        # 0분 ~ 10.5분 전 사이일 때 알림 발송
                        if 0 <= time_diff <= 10.5:
                            subscribers = load_subscribers()
                            favs = load_favorite_teams()
                            sent_alerts = load_sent_alerts()
                            
                            for chat_id in subscribers:
                                user_fav = favs.get(str(chat_id))
                                if user_fav and (user_fav in home_kr or user_fav in away_kr):
                                    alert_key = f"{now.strftime('%Y-%m-%d')}_{chat_id}_{key}_pregame"
                                    if alert_key not in sent_alerts:
                                        pitcher_home_info = current['pitcher_home'] if current['pitcher_home'] else "기록 없음"
                                        pitcher_away_info = current['pitcher_away'] if current['pitcher_away'] else "기록 없음"
                                        
                                        pregame_msg = (
                                            f"⏰ [경기 시작 10분 전 알림 - Playball Soon! ⚾]\n"
                                            f"나의 최애 팀 **{user_fav}**의 경기가 곧 시작합니다!\n\n"
                                            f"🔥 {away_kr} vs {home_kr}\n"
                                            f"📅 시작 시간: {current['status']}\n"
                                            f"🏟️ 구장: {current['venue']}\n"
                                            f"👉 예고 선발:\n"
                                            f"   - [원정] {pitcher_away_info}\n"
                                            f"   - [홈] {pitcher_home_info}\n"
                                        )
                                        try:
                                            await app.bot.send_message(chat_id=chat_id, text=pregame_msg)
                                            sent_alerts.append(alert_key)
                                            save_sent_alerts(sent_alerts)
                                        except Exception as send_err:
                                            print(f"[ERROR] Pregame warning send failed (chat_id: {chat_id}): {send_err}")
                
                # 2. 실시간 경기 결과 및 득점 알림 감시 (이전 데이터와 비교)
                if previous_games:
                    for key, current in current_games.items():
                        if key in previous_games:
                            prev = previous_games[key]
                            
                            home_kr = translate_team(current['home'])
                            away_kr = translate_team(current['away'])
                            
                            # 경기 시작 및 종료 여부 정의
                            is_prev_started = prev['score_home'] != "" or prev['score_away'] != ""
                            is_curr_started = current['score_home'] != "" or current['score_away'] != ""
                            
                            is_prev_finished = "試合終了" in prev['link_text'] or "試合終了" in prev['status']
                            is_curr_finished = "試合終了" in current['link_text'] or "試合終了" in current['status']
                            
                            notification_msg = ""
                            event_type = "" # 'playball', 'gameover', 'score_changed'
                            home_scored = False
                            away_scored = False
                            
                            # 1. 경기 개시 알림 (플레이볼)
                            if not is_prev_started and is_curr_started:
                                event_type = "playball"
                                notification_msg = (
                                    f"🚨 [경기 개시 알림 - Playball! ⚾]\n"
                                    f"📍 {current['venue']}에서 경기가 시작되었습니다!\n\n"
                                    f"🔥 {away_kr} vs {home_kr}\n"
                                    f"👉 선발 투수:\n"
                                    f"   - [원정] {current['pitcher_away'] if current['pitcher_away'] else '기록 없음'}\n"
                                    f"   - [홈] {current['pitcher_home'] if current['pitcher_home'] else '기록 없음'}\n"
                                )
                            
                            # 2. 경기 종료 알림 (최종 스코어 및 결과 기록)
                            elif not is_prev_finished and is_curr_finished:
                                event_type = "gameover"
                                notification_msg = (
                                    f"🏁 [경기 종료 알림 - Game Over ⚾]\n"
                                    f"📍 {current['venue']} 경기 결과가 등록되었습니다.\n\n"
                                    f"🔥 {away_kr} {current['score_away']} : {current['score_home']} {home_kr}\n"
                                    f"👉 최종 결과 기록:\n"
                                    f"   - [원정] {current['pitcher_away'] if current['pitcher_away'] else '-'}\n"
                                    f"   - [홈] {current['pitcher_home'] if current['pitcher_home'] else '-'}\n"
                                )
                            
                            # 3. 실시간 득점 변동 알림
                            elif is_curr_started and not is_curr_finished:
                                score_changed = current['score_home'] != prev['score_home'] or current['score_away'] != prev['score_away']
                                if score_changed and current['score_home'] and current['score_away']:
                                    event_type = "score_changed"
                                    status_kr = current['link_text'] if current['link_text'] else "진행 중"
                                    
                                    home_prev = int(prev['score_home']) if prev['score_home'].isdigit() else 0
                                    home_curr = int(current['score_home']) if current['score_home'].isdigit() else 0
                                    away_prev = int(prev['score_away']) if prev['score_away'].isdigit() else 0
                                    away_curr = int(current['score_away']) if current['score_away'].isdigit() else 0
                                    
                                    home_scored = home_curr > home_prev
                                    away_scored = away_curr > away_prev
                                    
                                    notification_msg = (
                                        f"🔔 [실시간 득점 상황 알림]\n"
                                        f"📍 {current['venue']} ({status_kr})\n\n"
                                        f"🔥 {away_kr} {current['score_away']} : {current['score_home']} {home_kr}\n"
                                        f"(이전 스코어: {prev['score_away'] if prev['score_away'] else '0'} : {prev['score_home'] if prev['score_home'] else '0'})\n"
                                    )
                            
                            # 알림 전송 대상이 있을 경우 모든 구독자에게 메시지 방송
                            if notification_msg:
                                subscribers = load_subscribers()
                                favs = load_favorite_teams()
                                print(f"[BROADCAST] Sending alert to {len(subscribers)} subscribers...")
                                for chat_id in subscribers:
                                    user_fav = favs.get(str(chat_id))
                                    is_fav_game = user_fav and (user_fav in home_kr or user_fav in away_kr)
                                    
                                    customized_msg = notification_msg
                                    if is_fav_game:
                                        if event_type == "score_changed":
                                            fav_scored = (home_scored and user_fav in home_kr) or (away_scored and user_fav in away_kr)
                                            opponent_scored = (home_scored and user_fav in away_kr) or (away_scored and user_fav in home_kr)
                                            
                                            if fav_scored:
                                                customized_msg = (
                                                    f"🎉 [득점!] 나의 최애 팀 {user_fav}이(가) 점수를 추가했습니다! ⚾🔥\n\n"
                                                    f"📍 {current['venue']} ({status_kr})\n"
                                                    f"🔥 {away_kr} {current['score_away']} : {current['score_home']} {home_kr}\n"
                                                    f"(이전 스코어: {prev['score_away'] if prev['score_away'] else '0'} : {prev['score_home'] if prev['score_home'] else '0'})\n"
                                                )
                                            elif opponent_scored:
                                                customized_msg = (
                                                    f"😭 [실점] 나의 최애 팀 {user_fav}이(가) 실점했습니다. 힘을 내길 바랍니다! ⚾\n\n"
                                                    f"📍 {current['venue']} ({status_kr})\n"
                                                    f"🔥 {away_kr} {current['score_away']} : {current['score_home']} {home_kr}\n"
                                                    f"(이전 스코어: {prev['score_away'] if prev['score_away'] else '0'} : {prev['score_home'] if prev['score_home'] else '0'})\n"
                                                )
                                            else:
                                                customized_msg = f"⭐ [나의 최애 팀 경기 소식 - {user_fav}] ⭐\n{notification_msg}"
                                        else:
                                            # playball or gameover
                                            customized_msg = f"⭐ [나의 최애 팀 경기 소식 - {user_fav}] ⭐\n{notification_msg}"
                                        
                                    try:
                                        await app.bot.send_message(chat_id=chat_id, text=customized_msg)
                                    except Exception as send_err:
                                        print(f"[ERROR] Send failed (chat_id: {chat_id}): {send_err}")
                                        
                previous_games = current_games
                
        except Exception as monitor_err:
            print(f"[ERROR] Monitor loop error: {monitor_err}")
            
        await asyncio.sleep(30)

# 봇 초기 설정 후 백그라운드 태스크 예약
async def post_init(application: Application) -> None:
    asyncio.create_task(score_monitor_loop(application))

# --- 텔레그램 명령어 설정 ---

# /start 명령어 (진입 시 자동 구독)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    subscribers.add(chat_id)
    save_subscribers(subscribers)
    
    welcome_msg = (
        "안녕! 일본 야구 실시간 알리미 봇이야 ⚾️\n"
        "시작과 함께 실시간 알림 자동 구독이 완료되었어! 🔔\n\n"
        "사용 가능한 명령어:\n"
        "/score - 실시간 전체 야구 점수 가져오기 ⚾\n"
        "/ranking - 리그 팀 순위표 조회 🏆\n"
        "/fav <팀이름> - 최애 팀 설정 (예: /fav 소프트뱅크) ⭐\n"
        "/myteam - 설정된 최애 팀의 오늘 경기 및 순위 조회 🔍\n"
        "/subscribe - 실시간 알림(득점, 시작/종료) 구독 신청 🔔\n"
        "/unsubscribe - 실시간 알림 구독 해제 🔕"
    )
    await update.message.reply_text(welcome_msg)

# /subscribe 명령어
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    if chat_id in subscribers:
        await update.message.reply_text("이미 실시간 알림을 구독 중입니다! 🔔")
    else:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text("실시간 알림(경기 시작, 득점 변동, 경기 종료) 구독이 등록되었습니다! 🔔⚾️")

# /unsubscribe 명령어
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text("실시간 알림 구독이 해제되었습니다. 🔕")
    else:
        await update.message.reply_text("현재 구독 상태가 아닙니다. /subscribe 를 입력해 구독할 수 있습니다.")

# /score 명령어
async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    favs = load_favorite_teams()
    user_fav = favs.get(str(chat_id))

    await update.message.reply_text("야후 재팬에서 실시간 점수를 가져오는 중... 🏃‍♂️💨")
    
    games = fetch_today_games_raw()
    if not games:
        await update.message.reply_text("오늘 예정된 경기가 없거나 데이터를 가져올 수 없습니다. 🥲")
        return
        
    result_text = "⚾️ [실시간] 일본 프로야구 경기 결과 ⚾️\n\n"
    for key, game in games.items():
        home_kr = translate_team(game['home'])
        away_kr = translate_team(game['away'])
        
        status_kr = "경기 예정"
        if "試合終了" in game['link_text'] or "試合終了" in game['status']:
            status_kr = "경기 종료"
        elif game['score_home'] or game['score_away']:
            status_kr = f"진행 중 ({game['link_text'] if game['link_text'] else '실시간'})"
        else:
            status_kr = f"경기 전 ({game['status']})"
            
        score_disp = f"{game['score_away']} : {game['score_home']}" if (game['score_home'] or game['score_away']) else "- vs -"
        
        is_fav_game = user_fav and (user_fav in home_kr or user_fav in away_kr)
        fav_prefix = "⭐ [나의 최애팀 경기]\n" if is_fav_game else ""

        result_text += (
            f"{fav_prefix}"
            f"📍 {game['venue']} [{status_kr}]\n"
            f"🔥 {away_kr} {score_disp} {home_kr}\n\n"
        )
        
    await update.message.reply_text(result_text)

# /ranking 명령어
async def ranking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    favs = load_favorite_teams()
    user_fav = favs.get(str(chat_id))

    await update.message.reply_text("야후 재팬에서 리그 순위표를 가져오는 중... 🏆")
    
    central, pacific = fetch_league_standings()
    if not central or not pacific:
        await update.message.reply_text("순위표 데이터를 가져올 수 없습니다. 🥲")
        return
        
    msg = "🏆 **일본 프로야구 리그 순위표** 🏆\n\n"
    
    msg += "🔴 **센트럴 리그**\n"
    for t in central:
        name_kr = translate_team(t['name'])
        is_fav = user_fav and (user_fav in name_kr or name_kr in user_fav)
        fav_marker = " ⭐" if is_fav else ""
        msg += f"{t['rank']}위: {name_kr}{fav_marker} ({t['wins']}승 {t['losses']}패 {t['draws']}무, 승률 {t['pct']}, 승차 {t['diff']})\n"
        
    msg += "\n🔵 **퍼시픽 리그**\n"
    for t in pacific:
        name_kr = translate_team(t['name'])
        is_fav = user_fav and (user_fav in name_kr or name_kr in user_fav)
        fav_marker = " ⭐" if is_fav else ""
        msg += f"{t['rank']}위: {name_kr}{fav_marker} ({t['wins']}승 {t['losses']}패 {t['draws']}무, 승률 {t['pct']}, 승차 {t['diff']})\n"
        
    await update.message.reply_text(msg)
# /fav 명령어 (최애 팀 설정)
async def fav_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        help_msg = (
            "⭐ **나의 최애 팀 설정**\n\n"
            "사용법: `/fav <팀이름>` (예: `/fav 소프트뱅크`, `/fav 요미우리`)\n\n"
            "**전체 팀 목록**:\n"
            "요미우리, 한신, 주니치, 요코하마, 야쿠르트, 히로시마\n"
            "소프트뱅크, 오릭스, 지바 롯데, 라쿠텐, 세이부, 니혼햄"
        )
        await update.message.reply_text(help_msg)
        return
        
    team_arg = " ".join(context.args).strip()
    matched_team = None
    for k, v in TEAM_MAPPING.items():
        if team_arg == k or team_arg.replace(" ", "") == k.replace(" ", ""):
            matched_team = v
            break
            
    if not matched_team:
        for k, v in TEAM_MAPPING.items():
            if team_arg in k or k in team_arg:
                matched_team = v
                break
                
    if matched_team:
        favs = load_favorite_teams()
        favs[str(chat_id)] = matched_team
        save_favorite_teams(favs)
        await update.message.reply_text(f"완료! 최애 팀이 **'{matched_team}'**으로 설정되었습니다. ⭐⚾")
    else:
        await update.message.reply_text("알 수 없는 팀 이름입니다. 정확한 팀 이름을 입력해 주세요! (예: /fav 소프트뱅크)")

# /myteam 명령어 (최애 팀 오늘 정보 조회)
async def myteam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    favs = load_favorite_teams()
    user_fav = favs.get(str(chat_id))
    
    if not user_fav:
        await update.message.reply_text(
            "아직 최애 팀을 설정하지 않았어! 🥲\n"
            "/fav <팀이름> 명령어로 최애 팀을 설정해줘.\n"
            "예: `/fav 소프트뱅크`"
        )
        return
        
    await update.message.reply_text(f"🔍 나의 최애 팀 **'{user_fav}'**의 오늘 경기 및 순위 정보를 조회 중... 🏃‍♂️💨")
    
    # 1. 경기 정보 찾기
    games = fetch_today_games_raw()
    fav_game_msg = "오늘 예정되거나 진행 중인 경기가 없습니다. 📅"
    
    if games:
        for key, game in games.items():
            home_kr = translate_team(game['home'])
            away_kr = translate_team(game['away'])
            if user_fav in home_kr or user_fav in away_kr:
                status_kr = "경기 예정"
                if "試合終了" in game['link_text'] or "試合終了" in game['status']:
                    status_kr = "경기 종료"
                elif game['score_home'] or game['score_away']:
                    status_kr = f"진행 중 ({game['link_text'] if game['link_text'] else '실시간'})"
                else:
                    status_kr = f"경기 전 ({game['status']})"
                    
                score_disp = f"{game['score_away']} : {game['score_home']}" if (game['score_home'] or game['score_away']) else "- vs -"
                
                fav_game_msg = (
                    f"📍 {game['venue']} [{status_kr}]\n"
                    f"🔥 {away_kr} {score_disp} {home_kr}\n"
                )
                if game['pitcher_away'] or game['pitcher_home']:
                    fav_game_msg += (
                        f"👉 선발/결과 기록:\n"
                        f"   - [원정] {game['pitcher_away'] if game['pitcher_away'] else '-'}\n"
                        f"   - [홈] {game['pitcher_home'] if game['pitcher_home'] else '-'}\n"
                    )
                break
                
    # 2. 순위 정보 찾기
    central, pacific = fetch_league_standings()
    rank_msg = ""
    if central and pacific:
        for t in central + pacific:
            name_kr = translate_team(t['name'])
            if user_fav in name_kr or name_kr in user_fav:
                league_name = "센트럴 리그" if t in central else "퍼시픽 리그"
                rank_msg = f"🏆 **순위**: {league_name} {t['rank']}위 ({t['wins']}승 {t['losses']}패 {t['draws']}무, 승률 {t['pct']}, 게임차 {t['diff']})"
                break
                
    msg = (
        f"⭐ **나의 최애 팀: {user_fav}** ⭐\n\n"
        f"📅 **오늘 경기 상황**:\n{fav_game_msg}\n"
        f"{rank_msg}"
    )
    await update.message.reply_text(msg)

# ★ 봇 실행 메인 엔진 ★
def main():
    print("[SYSTEM] Bot started successfully. Ready for commands.")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(CommandHandler("ranking", ranking_command))
    app.add_handler(CommandHandler("fav", fav_command))
    app.add_handler(CommandHandler("myteam", myteam_command))

    app.run_polling()

if __name__ == '__main__':
    main()
