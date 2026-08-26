from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from pymongo import MongoClient
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity,
                                set_access_cookies, unset_jwt_cookies)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from rapidfuzz import fuzz 

import os
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

SIMILARITY_THRESHOLD = 70   # 이 밑으로는 검색 결과에서 제외(함수 community_list)

MIN_QUERY_LEN = 2


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


# ==========================================
# 화면 렌더링 라우터 — 커뮤니티
# ==========================================
@app.route('/home')
@jwt_required()
def hub():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id
    test_done = bool(user_info and user_info.get('mbti'))
    return render_template('hub.html', nickname=nickname, test_done=test_done)


@app.route('/community')
@jwt_required()
def community():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id
    return render_template('community.html', nickname=nickname, current_user_id=user_id)


@app.route('/community/<post_id>')
@jwt_required()
def community_detail(post_id):
    viewer_id = get_jwt_identity()

    try:
        oid = ObjectId(post_id)
    except InvalidId:
        return redirect(url_for('community'))   # URL을 잘못 쳤으면 그냥 목록으로

    post = db.posts.find_one({"_id": oid})
    if not post:
        return redirect(url_for('community'))   # 삭제된 글이면 그냥 목록으로

    # 글쓴이의 result.html 캐릭터 카드를 여기서 보여줘야 하므로,
    # "지금 보는 사람(viewer_id)"이 아니라 "글쓴이(post['author_id'])"의 MBTI를 조회한다
    author_info = db.users.find_one({"id": post['author_id']})
    author_mbti = author_info.get('mbti') if author_info else None
    my_class = MBTI_MAP.get(author_mbti)

    character = None
    if my_class:
        character = {
            "my_class": my_class,
            "best_match": MBTI_MAP.get(my_class.get('best_match')),
            "worst_match": MBTI_MAP.get(my_class.get('worst_match')),
        }
    # character가 None이면 템플릿에서 "아직 테스트를 안 한 모험가입니다" 문구가 대신 뜬다

    post_data = {
        "id": str(post["_id"]),
        "title": post["title"],
        "content": post["content"],
        "author_id": post["author_id"],
        "author_nickname": post["author_nickname"],
        "created_at": post["created_at"].isoformat(),
    }

    return render_template(
        'community_detail.html',
        post=post_data,
        character=character,
        viewer_id=viewer_id,
        is_author=(viewer_id == post['author_id']),
    )

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

@app.route('/api/community/posts', methods=['GET'])
@jwt_required()
def api_community_list():
    sort = request.args.get('sort', 'newest')
    target = request.args.get('target', 'all')
    if target not in ('all', 'title', 'content', 'nickname'):
        target = 'all'
    query = (request.args.get('q') or '').strip()

    if query and len(query) < MIN_QUERY_LEN:

        return jsonify({"result": "fail", "msg": "검색어는 2글자 이상 입력해주세요."}), 400

    all_posts = list(db.posts.find({}))

    if query:
        def score_of(post):
            fields = []
            if target in ('title', 'all'):
                fields.append(post['title'])
            if target in ('content', 'all'):
                fields.append(post['content'])
            if target in ('nickname', 'all'):
                fields.append(post['author_nickname'])
            # '모두'는 여러 필드 중 가장 잘 맞는 것 하나를 대표값으로 쓴다
            return max(fuzz.partial_ratio(query, f) for f in fields)

        scored = [(score_of(p), p) for p in all_posts]
        scored = [(s, p) for s, p in scored if s >= SIMILARITY_THRESHOLD]

        if not scored:
            # 예외 처리: 70% 이상인 게 하나도 없음
            return jsonify({"result": "success", "posts": [], "no_results": True})
        # 1) 먼저 날짜 기준으로 정렬 (2순위가 될 기준)
        scored.sort(key=lambda sp: sp[1]['created_at'], reverse=(sort != 'oldest'))
        # 2) 그다음 유사도 점수로 정렬 (1순위가 될 기준) — 안정 정렬이라 점수가 같은 것끼리는 위에서 정한 날짜순서가 유지됨
        scored.sort(key=lambda sp: sp[0], reverse=True)
        matched_posts = [p for _, p in scored]
    else:
        matched_posts = all_posts
        matched_posts.sort(key=lambda p: p['created_at'], reverse=(sort != 'oldest'))

    result = []
    for p in matched_posts:
        comment_count = db.comments.count_documents({"post_id": p["_id"]})
        result.append({
            "id": str(p["_id"]),
            "title": p["title"],
            "content": p["content"],
            "author_id": p["author_id"],
            "author_nickname": p["author_nickname"],
            "created_at": p["created_at"].isoformat(),
            "comment_count": comment_count,
        })
    return jsonify({"result": "success", "posts": result, "no_results": False})

@app.route('/api/community/posts', methods=['POST'])
@jwt_required()
def api_community_create():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    now = datetime.now(timezone.utc)


    if len(title) < MIN_QUERY_LEN or len(content) < MIN_QUERY_LEN :

        return jsonify({"result": "fail", "msg": "제목 및 본문을 2글자 이상 작성해주세요."}), 400

    db.posts.insert_one({
        "title": title,
        "content": content,
        "author_id": user_id,          # 권한 체크용 (고유값)
        "author_nickname": nickname,   # 화면 표시용
        "created_at": now,             # 정렬용
    })
    return jsonify({"result": "success", "msg": "게시물 등록이 완료되었습니다."})

@app.route('/api/community/posts/<post_id>', methods=['PUT'])
@jwt_required()
def api_community_update(post_id):
    try:
        oid = ObjectId(post_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 게시글 id 입니다."}), 400

    post = db.posts.find_one({"_id": oid})

    if not post:
        return jsonify({"result": "fail", "msg": "해당되는 게시물이 없습니다."}), 404

    author_id = post['author_id']
    user_id = get_jwt_identity()

    if user_id != author_id:
        return jsonify({"result": "fail", "msg": "해당 게시물의 작성자가 아닙니다."}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()

    if len(title) < MIN_QUERY_LEN or len(content) < MIN_QUERY_LEN :

        return jsonify({"result": "fail", "msg": "제목 및 본문을 2글자 이상 작성해주세요."}), 400

    db.posts.update_one(
        {"_id": oid},
        {"$set":{
        "title": title,
        "content": content,
        }}
    )
    return jsonify({"result": "success", "msg": "게시물 수정이 완료되었습니다."})

# ------------------------------------------
# 댓글 작성
# ------------------------------------------
@app.route('/api/community/posts/<post_id>/comments', methods=['POST'])
@jwt_required()
def api_comment_create(post_id):
    try:
        oid = ObjectId(post_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 게시글 id 입니다."}), 400

    post = db.posts.find_one({"_id": oid})
    if not post:
        return jsonify({"result": "fail", "msg": "해당되는 게시물이 없습니다."}), 404

    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({"result": "fail", "msg": "댓글 내용을 입력해주세요."}), 400

    db.comments.insert_one({
        "post_id": oid,                # 어떤 글에 달린 댓글인지 (delete_many 정리할 때 이 필드로 찾았었죠)
        "content": content,
        "author_id": user_id,
        "author_nickname": nickname,
        "created_at": datetime.now(timezone.utc),
    })
    return jsonify({"result": "success", "msg": "댓글이 등록되었습니다."})


# ------------------------------------------
# 댓글 목록 조회
# ------------------------------------------
@app.route('/api/community/posts/<post_id>/comments', methods=['GET'])
@jwt_required()
def api_comment_list(post_id):
    try:
        oid = ObjectId(post_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 게시글 id 입니다."}), 400

    comments = db.comments.find({"post_id": oid}).sort("created_at", 1)   # 오래된 순 = 대화 순서대로

    result = []
    for c in comments:
        result.append({
            "id": str(c["_id"]),          # ObjectId는 그대로 jsonify 못 하니 문자열로 변환
            "author_id": c["author_id"],
            "author_nickname": c["author_nickname"],
            "content": c["content"],
            "created_at": c["created_at"].isoformat(),
        })

    return jsonify({"result": "success", "comments": result})


# ------------------------------------------
# 댓글 수정 (댓글 작성자 본인만 — 글쓴이라도 남의 댓글은 수정 불가)
# ------------------------------------------
@app.route('/api/community/comments/<comment_id>', methods=['PUT'])
@jwt_required()
def api_comment_update(comment_id):
    try:
        oid = ObjectId(comment_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 댓글 id 입니다."}), 400

    comment = db.comments.find_one({"_id": oid})
    if not comment:
        return jsonify({"result": "fail", "msg": "해당되는 댓글이 없습니다."}), 404

    if comment['author_id'] != get_jwt_identity():
        return jsonify({"result": "fail", "msg": "본인 댓글만 수정할 수 있습니다."}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({"result": "fail", "msg": "댓글 내용을 입력해주세요."}), 400

    db.comments.update_one(
        {"_id": oid},
        {"$set": {"content": content}}
    )
    return jsonify({"result": "success", "msg": "댓글이 수정되었습니다."})


# ------------------------------------------
# 댓글 삭제 (댓글 작성자 본인 OR 그 글의 작성자 — 둘 중 하나면 가능)
# ------------------------------------------
@app.route('/api/community/comments/<comment_id>', methods=['DELETE'])
@jwt_required()
def api_comment_delete(comment_id):
    try:
        oid = ObjectId(comment_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 댓글 id 입니다."}), 400

    comment = db.comments.find_one({"_id": oid})
    if not comment:
        return jsonify({"result": "fail", "msg": "해당되는 댓글이 없습니다."}), 404

    user_id = get_jwt_identity()
    post = db.posts.find_one({"_id": comment['post_id']})

    is_comment_author = (comment['author_id'] == user_id)
    is_post_author = bool(post and post['author_id'] == user_id)

    if not (is_comment_author or is_post_author):
        return jsonify({"result": "fail", "msg": "삭제 권한이 없습니다."}), 403

    db.comments.delete_one({"_id": oid})
    return jsonify({"result": "success", "msg": "댓글이 삭제되었습니다."})

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

@app.route('/api/community/posts/<post_id>', methods=['DELETE'])
@jwt_required()
def api_community_delete(post_id):
    try:
        oid = ObjectId(post_id)
    except InvalidId:
        return jsonify({"result": "fail", "msg": "잘못된 게시글 id 입니다."}), 400

    post = db.posts.find_one({"_id": oid})

    if not post:
        return jsonify({"result": "fail", "msg": "해당되는 게시물이 없습니다."}), 404

    user_id = get_jwt_identity()

    if post['author_id'] != user_id():
        return jsonify({"result": "fail", "msg": "해당 게시물의 작성자가 아닙니다."}), 403

    db.posts.delete_one({"_id": oid})
    db.comments.delete_many({"post_id": oid})   # 글이 사라지면 딸린 댓글도 같이 정리 (안 하면 고아 댓글이 남음)

    return jsonify({"result": "success", "msg": "게시물이 삭제되었습니다."})


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
