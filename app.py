from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# TODO: [영준] 백엔드 코어 (DB 연동 및 JWT 설정)
# 1. PyMongo를 이용한 MongoDB 연결 객체 생성
# 2. flask_jwt_extended를 이용한 JWTManager 초기화

# ==========================================
# 화면 렌더링 라우터 (HTML 서빙)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/result')
def result():
    # TODO: [최현욱] Jinja2 렌더링 테스트를 위해 가짜 데이터 넘겨보기
    # TODO: [영준] DB에서 결과 데이터 조회 후 템플릿으로 전달 (MBTI 계산 로직 포함)
    return render_template('result.html', my_class=mock_data)

# ==========================================
# API 라우터 (AJAX 통신용)
# ==========================================
@app.route('/api/login', methods=['POST'])
def api_login():
    # TODO: [영준] 아이디/비밀번호 확인 후 JWT 토큰 발급 로직 작성
    pass

@app.route('/api/signup', methods=['POST'])
def api_signup():
    # TODO: [영준] 중복 확인 및 패스워드 해싱 후 MongoDB에 유저 저장
    pass

@app.route('/api/submit', methods=['POST'])
# TODO: [영준] @jwt_required() 데코레이터 추가하여 인증된 유저만 접근 가능하게 설정
def api_submit():
    # TODO: [영준] 클라이언트(test.js)에서 넘어온 MBTI 결과 배열을 바탕으로 최종 MBTI 도출 및 DB 저장
    pass

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)