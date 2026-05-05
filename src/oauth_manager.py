import os
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# .env 로드
load_dotenv()

oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)

    # 환경 변수에서 설정값 읽기
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    return oauth