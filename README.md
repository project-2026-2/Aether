# 시작하기
`docker run -d --name mongodb -p 27017:27017 -v ~/mongodb_data:/data/db mongo` 명령어로 MongoDB 컨테이너를 실행합니다.  
`uv sync` 명령어로 프로젝트의 의존성을 설치합니다.  
`npm install bootstrap` 명령어로 부트스트랩을 설치합니다.  
`python -m venv venv` 명령어로 가상환경을 생성합니다.    
`source venv/bin/activate` 명령어로 가상환경을 활성화합니다  
`python ./src/app.py` 명령어로 서버를 실행합니다.