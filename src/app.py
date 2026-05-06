import os
import time
import threading
from collections import deque
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db_manager import add_user, check_user, add_google_user, get_all_users, get_recent_searches
from oauth_manager import init_oauth
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# 프록시(클라우드플레어 등) 환경 대응
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 세션 설정 보안 및 안정성 강화
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800  # 30분 유지
)

oauth_client = init_oauth(app)

# ── 트래픽 카운터 ──────────────────────────────────────────
# 1초 슬라이딩 윈도우로 req/s 계산
_request_timestamps = deque()  # 최근 요청 시각(unix time)
_request_count_total = 0       # 서버 시작 이후 누적 요청 수
_lock = threading.Lock()

@app.before_request
def _count_request():
    global _request_count_total
    now = time.time()
    with _lock:
        _request_timestamps.append(now)
        # 1초보다 오래된 기록 제거
        while _request_timestamps and _request_timestamps[0] < now - 1:
            _request_timestamps.popleft()
        _request_count_total += 1
# ────────────────────────────────────────────────────────────


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if password != password_confirm:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('register.html')

        if add_user(username, password):
            flash('회원가입 성공!')
            return redirect(url_for('login'))
        else:
            flash('이미 존재하는 이름입니다.')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = check_user(username, password)

        if user:
            session.clear()
            session['user'] = user['username']
            session['login_type'] = user.get('login_type', 'local')
            flash('login_success')
            return redirect(url_for('test_search'))
        flash('정보가 올바르지 않습니다.')
    return render_template('login.html')


@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return oauth_client.google.authorize_redirect(redirect_uri)


@app.route('/auth/google')
def google_auth():
    try:
        token = oauth_client.google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            user = add_google_user(user_info['name'], user_info['email'])
            if user:
                session.clear()
                session['user'] = user['username']
                session['login_type'] = user.get('login_type', 'google')
                session.modified = True
                flash('login_success')
                return redirect(url_for('test_search'))

    except Exception as e:
        print(f"Auth Error: {e}")
        flash("로그인 실패")
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('logged_out_success')
    return redirect(url_for('test_search'))


@app.route('/', methods=['GET', 'POST'])
def test_search():
    user = session.get('user')
    return render_template('index.html', user=user)


# ── Dashboard (root 전용) ──────────────────────────────────
@app.route('/dashboard')
def dashboard():
    # root 계정만 접근 허용
    if session.get('login_type') != 'root':
        flash('접근 권한이 없습니다. root 계정으로 로그인하세요.')
        return redirect(url_for('login'))

    users = get_all_users()
    recent_searches = get_recent_searches(limit=8)

    return render_template(
        'dashboard.html',
        users=users,
        recent_searches=recent_searches,
        request_count=_request_count_total,
    )


# ── 실시간 서버 stats API ──────────────────────────────────
@app.route('/api/stats')
def api_stats():
    if session.get('login_type') != 'root':
        return jsonify({'error': 'forbidden'}), 403

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_count()
        mem = psutil.virtual_memory()
        ram = round(mem.percent, 1)
        ram_used_gb = round(mem.used / 1024**3, 2)
        ram_total_gb = round(mem.total / 1024**3, 2)
    except ImportError:
        cpu = 0.0
        cpu_cores = '?'
        ram = 0.0
        ram_used_gb = 0
        ram_total_gb = 0

    with _lock:
        rps = len(_request_timestamps)

    return jsonify(
        cpu=cpu,
        cpu_cores=cpu_cores,
        ram=ram,
        ram_used_gb=ram_used_gb,
        ram_total_gb=ram_total_gb,
        rps=rps,
        request_count=_request_count_total,
    )
# ────────────────────────────────────────────────────────────


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True, port=5000)