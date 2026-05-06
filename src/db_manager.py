import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# MongoDB 연결 설정
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri, connect=False, serverSelectionTimeoutMS=5000)
db = client['yuris_life']
users_col = db['users']

def init_db():
    """DB 초기화: root 계정이 없으면 생성"""
    root_user = users_col.find_one({'username': 'root'})
    if not root_user:
        hashed_pw = generate_password_hash('kimchies')
        user_data = {
            'username': 'root',
            'password': hashed_pw,
            'login_type': 'root', # 요청하신 로그인 타입
            'created_at': datetime.now()
        }
        users_col.insert_one(user_data)
        print("✅ [DB] root 계정이 생성되었습니다. (PW: kimchies)")
    else:
        print("ℹ️ [DB] root 계정이 이미 존재합니다.")

# 파일이 실행될 때 초기화 함수 호출
init_db()

def add_user(username, password):
    """일반 회원가입 (local)"""
    if users_col.find_one({'username': username}):
        return False

    hashed_pw = generate_password_hash(password)
    user_data = {
        'username': username,
        'password': hashed_pw,
        'login_type': 'local',
        'created_at': datetime.now()
    }

    try:
        users_col.insert_one(user_data)
        return True
    except Exception as e:
        print(f"DB Insert Error: {e}")
        return False

def check_user(username, password):
    """로그인 확인"""
    user = users_col.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        return user
    return None

def get_all_users():
    """전체 사용자 목록 반환"""
    return list(users_col.find({}, {'password': 0}))

def get_recent_searches(limit=8):
    """최근 검색 기록 반환"""
    searches_col = db['search_logs']
    results = searches_col.find().sort('time', -1).limit(limit)
    return [{'query': r['query'], 'user': r['user'], 'time': r['time'].strftime('%m/%d %H:%M')} for r in results]

def add_google_user(username, email):
    """구글 로그인 사용자 저장 및 조회"""
    user = users_col.find_one({'email': email})

    if not user:
        user_data = {
            'username': username,
            'email': email,
            'password': 'google_authenticated',
            'login_type': 'google',
            'created_at': datetime.now()
        }
        try:
            users_col.insert_one(user_data)
            return user_data
        except Exception as e:
            print(f"DB Insert Error: {e}")
            return None
    return user