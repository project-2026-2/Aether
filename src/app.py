import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_manager import add_user, check_user, add_google_user
from ani_search import search_anime
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


# @app.route('/')
# def home():
#     return render_template('index.html')


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
            session['login_type'] = user.get('login_type', 'local')  # root 타입 저장
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
    # anime_list = None
    # if request.method == 'POST':
    #     query = request.form.get('search_query')
    #     if query:
    #         result = search_anime(query)
    #         if result and 'data' in result:
    #             anime_list = result['data']['Page']['media']
    return render_template('test.html', user=user)


if __name__ == '__main__':
    app.run("0.0.0.0",debug=True, port=5000)