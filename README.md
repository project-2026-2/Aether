# 프로젝트 이름 의미
본 프로젝트는 그리스 신화에서 공기와 바람의 신인 Aether에서 이름을 따왔습니다. Aether는 모든 생명체가 숨쉬는 공기를 상징하며, 이 프로젝트는 사용자들이 파일을 자유롭게 관리할 수 있는 공간을 제공하는 것을 목표로 합니다.
# 프로젝트 설명
- 본 프로젝트는 Google Drive를 대체할 수 있는 웹 기반 파일 관리 시스템입니다.
- 사용자는 파일을 업로드, 다운로드, 삭제할 수 있으며, 폴더를 생성하여 파일을 조직할 수 있습니다.
- MongoDB를 사용하여 파일 메타데이터를 저장하고, Flask 프레임워크를 사용하여 백엔드를 구축하였습니다.
- 프론트엔드는 Bootstrap을 사용하여 반응형 디자인을 구현하였습니다.

## 프로젝트 구조
```Text
Aether/
├── node_modules/
├── .venv/                     # Python 가상환경 디렉토리
├── src/                       # 소스 코드 디렉토리
│   ├── static/                # 정적 리소스 (CSS, JS)
│   │   ├── bootstrap.bundle.min.js
│   │   ├── bootstrap.min.css
│   │   ├── script.js
│   │   └── style.css
│   ├── templates/             # HTML 템플릿
│   │   ├── forgot.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── reset.html
│   ├── app.py                 # 메인 애플리케이션 실행 파일
│   ├── db_manager.py          # 데이터베이스 관리 모듈
│   └── oauth_manager.py       # OAuth 인증 관리 모듈
├── .env                       # 환경 변수 설정
├── .gitignore                 # Git 제외 설정
├── package.json               # Node.js 의존성 관리
├── pyproject.toml             # Python 프로젝트 설정
├── README.md                  # 프로젝트 문서
└── uv.lock                    # Python 의존성 잠금 파일
```

## 시작하기
`docker run -d --name mongodb -p 27017:27017 -v ~/mongodb_data:/data/db mongo` 명령어로 MongoDB 컨테이너를 실행합니다.  
`uv sync` 명령어로 프로젝트의 의존성을 설치합니다.  
`npm install bootstrap` 명령어로 부트스트랩을 설치합니다.  
`python -m venv venv` 명령어로 가상환경을 생성합니다.    
`source venv/bin/activate` 명령어로 가상환경을 활성화합니다  
`python ./src/app.py` 명령어로 서버를 실행합니다.