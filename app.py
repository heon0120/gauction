# [====================================================================]
# [====================================================================]
# [===                     STUDIO CSGNS                             ===]
# [===                              Made By STUIO CSGMS             ===]
# [===                                                              ===]
# [===              Require By Jea Yoon  Sin                        ===]
# [===                                                              ===]
# [===                                                              ===]
# [===         Copyright 2025 STUDIO CSGNS All Right Reserved       ===]
# [====================================================================]
# [====================================================================]
# import redis # 원래는 워커 늘려서 할려고 redis사용할려함

# 본소스코드는 공개용입니다. 실서비스는 약간달라요 이거 버전 낮은거 완전 초기버전
import json
import threading
import time
import csv
from flask import Flask, render_template, request, redirect, session, jsonify, send_file, url_for
import os
from datetime import datetime, timedelta
import secrets
from flask_session import Session

app = Flask(__name__)
app.secret_key = app.secret_key = secrets.token_hex(32)
DATA_DIR = 'data'
# ================== DB 대신 json 관리가 편하지만 안전하지 않은방법이긴 함 =================
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TEAMS_FILE = os.path.join(DATA_DIR, 'teams.json')
PLAYERS_FILE = os.path.join(DATA_DIR, 'players.json')
BID_LOG_FILE = os.path.join(DATA_DIR, 'bid_log.json')
BID_LOG_CSV = os.path.join(DATA_DIR, 'bid_log.csv')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== Auction State ==========
current_player = None
current_player_start_time = None
auction_lock = threading.Lock()
auction_interval = 30
auction_order = []
sold_players = []
unsold_players = []
auction_running = False
last_bid_times = {}
BID_COOLDOWN_SECONDS = 0.5

def auction_cycle():
    global current_player, current_player_start_time, auction_running
    while auction_running:
        with auction_lock:
            players = load_json(PLAYERS_FILE)
            remaining = [p for p in players if not p['is_sold']]
            if not remaining:
                current_player = None
                break
            current_player = remaining[0]
            current_player_start_time = time.time()
            auction_order.append(current_player['name'])

        time.sleep(auction_interval)

        with auction_lock:
            players = load_json(PLAYERS_FILE)
            for p in players:
                if p['id'] == current_player['id']:
                    if p.get('highest_bidder'):
                        p['is_sold'] = True
                        teams = load_json(TEAMS_FILE)
                        if p['name'] not in teams[p['highest_bidder']] and len(teams[p['highest_bidder']]) < 5:
                            teams[p['highest_bidder']].append(p['name'])
                            users = load_json(USERS_FILE)
                            for user in users:
                                if user['username'] == p['highest_bidder']:
                                    user['points'] -= p['current_bid']
                                    break
                            save_json(TEAMS_FILE, teams)
                            save_json(USERS_FILE, users)
                            sold_players.append(p['name'])
                    else:
                        unsold_players.append(p['name'])
                    break
            save_json(PLAYERS_FILE, players)
            current_player = None
            current_player_start_time = None
    auction_running = False

# ========== Routes ==========

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    token = request.form.get('token', '').strip()
    if not token:
        return "Token이 비어있습니다.", 400

    users = load_json(USERS_FILE)
    for user in users:
        if user.get('token') == token:
            session['username'] = user['username']
            session.permanent = True
            if user['username'] == 'admin':
                return redirect('/admin')
            elif user['username'] == 'spectator':
                return redirect('/spectator')
            return redirect('/auction')
    return "유효하지 않은 토큰입니다.", 401


@app.route('/spectator')
def spectator_page():
    if 'username' not in session or session['username'] != 'spectator':
        return redirect('/')
    return render_template('spectator.html', username='spectator', auction_interval=auction_interval)


@app.route('/auction')
def auction():
    if 'username' not in session:
        return redirect('/')
    
    username = session['username']
    
    if username == 'admin':
        return redirect('/admin')
    
    # spectator 사용자는 별도 페이지로 리디렉션
    if username.startswith('spectator'):
        return redirect('/spectator')
    
    return render_template('auction.html', username=username, auction_interval=auction_interval)


@app.route('/admin')
def admin_page():
    username = session.get('username')
    if username != 'admin':
        return redirect(url_for('index'))

    players = load_json(PLAYERS_FILE)
    users = load_json(USERS_FILE)
    teams = load_json(TEAMS_FILE)

    return render_template('admin.html',
                           players=players,
                           users=users,
                           teams=teams,
                           current_player=current_player,
                           auction_running=auction_running)


@app.route('/start_auction', methods=['POST'])
def start_auction():
    global auction_running
    if 'username' not in session or session['username'] != 'admin':
        return "Unauthorized", 403
    if not auction_running:
        auction_thread = threading.Thread(target=auction_cycle)
        auction_thread.daemon = True
        auction_running = True
        auction_thread.start()
        return "Auction started"
    return "이미 경매는 시작되어있습니다."

@app.route('/stop_auction', methods=['POST'])
def stop_auction():
    global auction_running, server_message
    if 'username' not in session or session['username'] != 'admin':
        return "Unauthorized", 403
    auction_running = False
    server_message = "경매가 종료되었습니다."
    return "경매가 종료되었습니다."

server_message = ""

@app.route('/server_message')
def get_server_message():
    global server_message
    return jsonify({'message': server_message})

@app.route('/clear_message', methods=['POST'])
def clear_message_route():
    global server_message
    server_message = ""
    return '', 204

@app.route('/pause_auction', methods=['POST'])
def pause_auction():
    global auction_running
    if 'username' not in session or session['username'] != 'admin':
        return "Unauthorized", 403
    auction_running = False
    return "경매가 일시 중지되었습니다."


@app.route('/auction_status')
def auction_status():
    return jsonify({'running': auction_running})

@app.route('/current_player')
def get_current_player():
    with auction_lock:
        if not current_player or current_player_start_time is None:
            return jsonify({'status': 'waiting'})
        elapsed = time.time() - current_player_start_time
        remaining_time = max(0, int(auction_interval - elapsed))
        return jsonify({
            'id': current_player['id'],
            'name': current_player['name'],
            'current_bid': current_player['current_bid'],
            'highest_bidder': current_player.get('highest_bidder', None),
            'remaining_time': remaining_time
        })

@app.route('/all_players')
def all_players():
    return jsonify(load_json(PLAYERS_FILE))


@app.route('/bid', methods=['POST'])
def bid():
    if 'username' not in session:
        return "로그인 되지 않았습니다.", 403

    username = session['username']
    if username.startswith("spectator"):
        return "관전자는 입찰할 수 없습니다.", 403

    amount_str = request.form.get('amount')
    if not amount_str or not amount_str.isdigit():
        return "입찰 금액이 유효하지 않습니다.", 400

    amount = int(amount_str)
    if amount <= 0:
        return "입찰 금액은 0보다 커야 합니다.", 400

    # 0.5초 쿨타임 체크
    now = time.time()
    last_time = last_bid_times.get(username, 0)
    if now - last_time < BID_COOLDOWN_SECONDS:
        return f"{BID_COOLDOWN_SECONDS}초 이내에는 중복 입찰이 불가능합니다.", 429
    last_bid_times[username] = now

    with auction_lock:
        if not current_player or current_player.get('is_sold'):
            return "경매가 시작되지 않았거나 경매중인 선수가 아닙니다.", 400

        teams = load_json(TEAMS_FILE)
        users = load_json(USERS_FILE)
        user = next((u for u in users if u['username'] == username), None)
        if not user:
            return "사용자가 존재하지 않습니다.", 400

        if user['points'] < amount:
            return "포인트가 부족합니다.", 400
        if len(teams.get(username, [])) >= 5:
            return "팀은 최대 5명까지 구성할 수 있습니다.", 400

        players = load_json(PLAYERS_FILE)
        for p in players:
            if p['id'] == current_player['id']:
                if amount == p['current_bid']:
                    return "동일 금액으로는 입찰할 수 없습니다.", 400
                if amount < p['current_bid']:
                    return "입찰 금액이 현재가보다 낮습니다.", 400
                if p.get('highest_bidder') == username:
                    return "이미 최고 입찰자입니다.", 400

                # 입찰 적용
                p['current_bid'] = amount
                p['highest_bidder'] = username
                save_json(PLAYERS_FILE, players)
                current_player['current_bid'] = amount
                current_player['highest_bidder'] = username
                log_bid(username, p['name'], amount)
                return "입찰 완료!", 200

    return "서버 오류 발생", 500


def log_bid(username, player_name, amount):
    log = load_json(BID_LOG_FILE)
    log.append({
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "user": username,
        "player": player_name,
        "amount": amount
    })
    save_json(BID_LOG_FILE, log)

@app.route('/export_bids')
def export_bids():
    log = load_json(BID_LOG_FILE)
    with open(BID_LOG_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "user", "player", "amount"])
        writer.writeheader()
        for entry in log:
            writer.writerow(entry)
    return send_file(BID_LOG_CSV, as_attachment=True)

@app.route('/team_status')
def team_status():
    teams = load_json(TEAMS_FILE)
    users = load_json(USERS_FILE)
    players = load_json(PLAYERS_FILE)
    result = {}
    for captain, members in teams.items():
        total_points = sum(p['current_bid'] for p in players if p['name'] in members)
        result[captain] = {
            'members': members,
            'points_used': total_points,
            'points_left': next((u['points'] for u in users if u['username'] == captain), 0)
        }
    return jsonify(result)
@app.route('/rule')
def rule():
    return render_template("rules.html")
@app.route('/auction_order')
def get_auction_order():
    return jsonify({
        'auction_order': auction_order,
        'sold_players': sold_players,
        'unsold_players': unsold_players
    })

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.errorhandler(400)
def error_400(e):
    return render_template("error/400.html"), 400

@app.errorhandler(401)
def error_401(e):
    return render_template("error/401.html"), 401

@app.errorhandler(403)
def error_403(e):
    return render_template("error/403.html"), 403

@app.errorhandler(404)
def error_404(e):
    return render_template("error/404.html"), 404

@app.errorhandler(500)
def error_500(e):
    return render_template("error/500.html"), 500

# ========== Run App ==========

if __name__ == '__main__':
    app.run(debug=True)
