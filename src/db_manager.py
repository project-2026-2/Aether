import os
import secrets
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri, connect=False, serverSelectionTimeoutMS=5000)
db = client['yuris_life']
users_col = db['users']

def init_db():
    root_user = users_col.find_one({'username': 'root'})
    if not root_user:
        hashed_pw = generate_password_hash('kimchies')
        users_col.insert_one({
            'username': 'root',
            'password': hashed_pw,
            'login_type': 'root',
            'created_at': datetime.now()
        })

init_db()

def add_user(username, password, email):
    """일반 회원가입 - 이메일 추가"""
    if users_col.find_one({'username': username}):
        return False
    if users_col.find_one({'email': email}):
        return False

    users_col.insert_one({
        'username': username,
        'password': generate_password_hash(password),
        'email': email,
        'login_type': 'local',
        'created_at': datetime.now()
    })
    return True

def check_user(username, password):
    user = users_col.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        return user
    return None

def add_google_user(username, email):
    user = users_col.find_one({'email': email})
    if not user:
        user_data = {
            'username': username,
            'email': email,
            'password': 'google_authenticated',
            'login_type': 'google',
            'created_at': datetime.now()
        }
        users_col.insert_one(user_data)
        return user_data
    return user

def create_reset_token(email):
    """비밀번호 재설정 토큰 생성"""
    user = users_col.find_one({'email': email})
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    users_col.update_one(
        {'email': email},
        {'$set': {
            'reset_token': token,
            'reset_token_expires': datetime.now() + timedelta(hours=1)
        }}
    )
    return token

def reset_password(token, new_password):
    """토큰으로 비밀번호 변경"""
    user = users_col.find_one({
        'reset_token': token,
        'reset_token_expires': {'$gt': datetime.now()}
    })
    if not user:
        return False
    users_col.update_one(
        {'reset_token': token},
        {'$set': {'password': generate_password_hash(new_password)},
         '$unset': {'reset_token': '', 'reset_token_expires': ''}}
    )
    return True