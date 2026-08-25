from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity,
                                set_access_cookies, unset_jwt_cookies)
from werkzeug.security import generate_password_hash, check_password_hash
import json


load_dotenv()
app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # app.py가 있는 폴더의 절대경로

# ==========================================
# 환경변수 검사
# 값이 없으면 에러 없이 엉뚱하게 동작하므로(예: MongoClient(None) -> localhost)
# 서버가 켜지는 순간 바로 알려준다
# ==========================================
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
MONGO_URL = os.getenv('MONGO_URL')

if not JWT_SECRET_KEY:
    raise RuntimeError("환경변수 JWT_SECRET_KEY 가 없습니다. .env 파일을 확인하세요 (.env.example 참고).")
if not MONGO_URL:
    raise RuntimeError("환경변수 MONGO_URL 이 없습니다. .env 파일을 확인하세요 (.env.example 참고).")

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

# API는 헤더(Authorization)로, 주소창으로 여는 SSR 페이지(/test, /result)는 쿠키로 인증
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_SECURE'] = False        # HTTPS 붙이면 True로
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # 미니 프로젝트 범위에서는 비활성

client = MongoClient(MONGO_URL)             # PyMongo로 MongoDB에 연결 객체 생성
db = client['rpg_project']                  # 그 중에서 rpg_project DB 선택
jwt = JWTManager(app)

# ==========================================
# 직업 데이터는 바뀌지 않는 고정 데이터라 시작할 때 한 번만 읽는다
# (요청마다 파일을 여는 것은 낭비)
# ==========================================
with open(os.path.join(BASE_DIR, 'data', 'mbti_data.json'), 'r', encoding='utf-8') as f:
    MBTI_LIST = json.load(f)                        # 16개의 직업 딕셔너리가 담긴 리스트

MBTI_MAP = {job['mbti']: job for job in MBTI_LIST}  # "INTJ" -> 직업 dict (반복문 대신 바로 조회)


# ==========================================
# 인증 실패 처리
#  - 화면(HTML) 요청이면 로그인 페이지로 보내고
#  - API 요청이면 JSON 401을 그대로 돌려준다
# 이게 없으면 /result 에 토큰 없이 들어왔을 때 날것의 JSON 401이 화면에 뜬다
# ==========================================
def _auth_failed(msg):
    if request.path.startswith('/api/'):
        return jsonify({"result": "fail", "msg": msg}), 401
    return redirect(url_for('home'))

@jwt.unauthorized_loader
def _handle_no_token(reason):
    return _auth_failed("로그인이 필요합니다.")

@jwt.invalid_token_loader
def _handle_invalid_token(reason):
    return _auth_failed("유효하지 않은 토큰입니다.")

@jwt.expired_token_loader
def _handle_expired_token(jwt_header, jwt_payload):
    return _auth_failed("로그인이 만료되었습니다.")


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
@jwt_required()
def test():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id
    return render_template('test.html', nickname=nickname)

@app.route('/result')
@jwt_required()
def result():
    user_id = get_jwt_identity()                # 접속한 유저 정보 찾기
    user_info = db.users.find_one({"id": user_id})
    user_mbti = user_info.get('mbti') if user_info else None

    my_class = MBTI_MAP.get(user_mbti)
    if not my_class:                            # 아직 테스트를 안 했거나 값이 이상하면 테스트 화면으로
        return redirect(url_for('test'))

    # 궁합 상대는 "ENFP" 같은 코드로만 저장돼 있어서, 직업 정보를 찾아 함께 넘겨준다
    return render_template(
        'result.html',
        my_class=my_class,
        nickname=(user_info.get('nickname') or user_id),
        best_match=MBTI_MAP.get(my_class['best_match']),
        worst_match=MBTI_MAP.get(my_class['worst_match']),
    )


# ==========================================
# API 라우터 (AJAX 통신용)
# 응답 형식을 통일: {"result": "success" | "fail", "msg": "...", ...}
# ==========================================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}      # 본문이 비었거나 JSON이 아니어도 500이 나지 않게
    user_id = (data.get('id') or '').strip()
    user_pw = data.get('password') or ''

    if not user_id or not user_pw:
        return jsonify({"result": "fail", "msg": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    user = db.users.find_one({"id": user_id})
    if user and check_password_hash(user['password'], user_pw):
        # 로그인 성공 -> JWT 토큰 발급
        access_token = create_access_token(identity=user_id)
        response = jsonify({"result": "success", "access_token": access_token})
        set_access_cookies(response, access_token)  # SSR 페이지(/test, /result)용으로 쿠키에도 저장
        return response

    # 로그인 실패 처리 (아이디가 없는지 비밀번호가 틀렸는지는 알려주지 않는다)
    return jsonify({"result": "fail", "msg": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json(silent=True) or {}
    user_id = (data.get('id') or '').strip()
    user_pw = data.get('password') or ''
    nickname = (data.get('nickname') or '').strip()     # 친구 궁합에서 상대를 찾는 키

    if not user_id or not user_pw or not nickname:
        return jsonify({"result": "fail", "msg": "모든 항목을 입력해주세요."}), 400

    # 중복 확인
    if db.users.find_one({"id": user_id}):
        return jsonify({"result": "fail", "msg": "이미 사용 중인 아이디입니다."}), 409
    if db.users.find_one({"nickname": nickname}):
        return jsonify({"result": "fail", "msg": "이미 사용 중인 닉네임입니다."}), 409

    # 패스워드 해싱 후 MongoDB에 유저 저장
    db.users.insert_one({
        "id": user_id,
        "password": generate_password_hash(user_pw),
        "nickname": nickname,
    })
    return jsonify({"result": "success", "msg": "가입을 환영합니다"})


@app.route('/api/submit', methods=['POST'])
@jwt_required()
def api_submit():
    user_id = get_jwt_identity()                # 출입증(토큰)에서 유저 아이디 꺼내기
    data = request.get_json(silent=True) or {}
    answers = data.get('answers')               # 예: ["I", "N", "T", "J"]

    # 검증 없이 join 하면 "XXYY" 같은 값이 그대로 DB에 저장된다
    if not isinstance(answers, list) or len(answers) != 4:
        return jsonify({"result": "fail", "msg": "answers는 4개짜리 배열이어야 합니다."}), 400

    mbti_result = "".join(str(a) for a in answers).upper()   # 배열을 문자열로 합치기
    if mbti_result not in MBTI_MAP:
        return jsonify({"result": "fail", "msg": "알 수 없는 유형입니다: " + mbti_result}), 400

    # db에 있는 유저 정보에 mbti 결과 업데이트
    db.users.update_one({"id": user_id}, {"$set": {"mbti": mbti_result}})
    return jsonify({"result": "success", "mbti": mbti_result})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    # 쿠키에 심어둔 토큰 제거 (localStorage 토큰은 JS가 지움)
    response = jsonify({"result": "success"})
    unset_jwt_cookies(response)
    return response


if __name__ == '__main__':
    # 배포(EC2)에서는 .env 에 FLASK_DEBUG=0 을 넣어 디버그 화면 노출을 막는다
    debug_mode = os.getenv('FLASK_DEBUG', '1') == '1'
    app.run('0.0.0.0', port=5000, debug=debug_mode)
