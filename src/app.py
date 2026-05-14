import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_manager import add_user, check_user, add_google_user, create_reset_token, reset_password
from oauth_manager import init_oauth
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800
)     

oauth_client = init_oauth(app)


@app.route('/', methods=['GET', 'POST'])
def test_search():
    user = session.get('user')
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email')

        if password != password_confirm:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('register.html')

        if add_user(username, password, email):
            flash('회원가입 성공!')
            return redirect(url_for('login'))
        else:
            flash('이미 존재하는 아이디 또는 이메일입니다.')
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


def send_reset_email(to_email, token):
    reset_url = f"http://localhost:5050/reset/{token}"

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": "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",
            "Content-Type": "application/json"
        },
        json={
            "sender": {"name": "Aether", "email": "hayul9888@gmail.com"},
            "to": [{"email": to_email}],
            "subject": "비밀번호 재설정",
            "textContent": f"아래 링크를 클릭하여 비밀번호를 재설정하세요:\n\n{reset_url}"
        }
    )
    print(response.status_code, response.text)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email')
        token = create_reset_token(email)
        if token:
            send_reset_email(email, token)
        flash('이메일이 존재하면 재설정 링크를 전송했습니다.')
        return redirect(url_for('forgot'))
    return render_template('forgot.html')


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    if request.method == 'POST':
        new_pw = request.form.get('password')
        confirm_pw = request.form.get('password_confirm')
        if new_pw != confirm_pw:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('reset.html', token=token)
        if reset_password(token, new_pw):
            flash('비밀번호가 변경되었습니다!')
            return redirect(url_for('login'))
        flash('링크가 만료되었습니다.')
        return redirect(url_for('forgot'))
    return render_template('reset.html', token=token)


if __name__ == '__main__':
    app.run("0.0.0.0", debug=True, port=5050)