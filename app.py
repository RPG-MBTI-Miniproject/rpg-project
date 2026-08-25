from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
import json 


load_dotenv()
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
client = MongoClient(os.getenv('MONGO_URL')) #PyMongo로 MongoDB에 연결 객체 생성
db = client['rpg_project']                  #그 중에서 rpg_project DB 선택
jwt = JWTManager(app)

# TODO: [영준] 백엔드 코어 (DB 연동 및 JWT 설정) **완료**
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
@jwt_required()
def result():
    # TODO: [최현욱] Jinja2 렌더링 테스트를 위해 가짜 데이터 넘겨보기
    # TODO: [영준] DB에서 결과 데이터 조회 후 템플릿으로 전달 (MBTI 계산 로직 포함)
    user_id = get_jwt_identity()    #접속한 유저 정보 찾기
    user_info = db.users.find_one({"id": user_id})
    user_mbti = user_info['mbti']

    with open('mbti_data.json', 'r', encoding='utf-8') as f:    # json 파일 읽어오기
        mbti_list = json.load(f) # 16개의 직업 딕셔너리가 담긴 리스트

    for job in mbti_list:
        if job['mbti'] == user_mbti:
            return render_template('result.html', my_class=job)




# ==========================================
# API 라우터 (AJAX 통신용)
# ==========================================
@app.route('/api/login', methods=['POST'])

def api_login():
    # TODO: [영준] 아이디/비밀번호 확인 후 JWT 토큰 발급 로직 작성   **완료**
    data = request.get_json()
    user_id, user_pw = data['id'], data['password']
    user = db.users.find_one({"id": user_id})
    if user and user['password'] == user_pw:
        #로그인 성공 -> JWT 토큰 발급 로직
        access_token = create_access_token(identity=user_id)
        return jsonify({"result": "success", "access_token": access_token})

    else:
        #로그인 실패 처리 로직
         return jsonify({"result": "fail"})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    # TODO: [영준] 중복 확인 및 패스워드 해싱 후 MongoDB에 유저 저장     **완료**
    data = request.get_json()
    user_id, user_pw = data['id'], data['password']
    existing_user = db.users.find_one({"id": user_id})
    if existing_user :   #이 아이디를 사용하는 사람이 있다면 딕셔너리가 들어감
        return jsonify({"result": "이미 사용 중인 아이디입니다."})
    else :
        hashed_pw = generate_password_hash(user_pw)
        db.users.insert_one({"id": user_id, "password": hashed_pw})
        return jsonify({"result": "가입을 환영합니다"})

@app.route('/api/submit', methods=['POST'])
@jwt_required()
# TODO: [영준] @jwt_required() 데코레이터 추가하여 인증된 유저만 접근 가능하게 설정
def api_submit():
    # TODO: [영준] 클라이언트(test.js)에서 넘어온 MBTI 결과 배열을 바탕으로 최종 MBTI 도출 및 DB 저장
    user_id = get_jwt_identity()    # 출입증(토큰)에서 유저 아이디 꺼내기
    data = request.get_json()       # 프론트엔드에서 보낸 데이터 받아오기
    answers = data['answers']       
    mbti_result = "".join(answers)  # 배열을 문자열로 합치기
    db.users.update_one({"id": user_id}, {"$set": {"mbti": mbti_result}})   #db에 있는 유저 정보에 mbti 결과 업데이트

    return jsonify({"result": "mbti 결과 업데이트"})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)