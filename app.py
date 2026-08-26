from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from dotenv import load_dotenv
from pymongo import MongoClient
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity,
                                set_access_cookies, unset_jwt_cookies, verify_jwt_in_request)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from rapidfuzz import fuzz

import os
import json
import time


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
# 설정하지 않으면 flask-jwt-extended 기본값이 15분이라, 쪽지창을 잠깐 열어두기만 해도
# 전송이 401로 실패하고 로그인 화면으로 튕긴다. 시연 도중 끊기지 않도록 1일로 늘린다.
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['JWT_COOKIE_SECURE'] = os.getenv('JWT_COOKIE_SECURE', 'False') == 'True'        # HTTPS 붙이면 True로
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # 미니 프로젝트 범위에서는 비활성

client = MongoClient(MONGO_URL)             # PyMongo로 MongoDB에 연결 객체 생성
db = client['rpg_project']                  # 그 중에서 rpg_project DB 선택
jwt = JWTManager(app)

SIMILARITY_THRESHOLD = 70   # 이 밑으로는 검색 결과에서 제외(함수 community_list)

MIN_QUERY_LEN = 2

# ==========================================
# DM 설정
# 웹소켓 라이브러리를 새로 깔지 않고 Flask 내장 기능(SSE)만으로 실시간을 만든다.
#  - 서버는 아무 상태도 들고 있지 않는다. 메시지는 전부 MongoDB(dm_messages)에만 쌓인다.
#  - 스트림은 "DB를 다시 확인해라"는 신호만 흘려보내는 역할이다.
#  - 스레드를 영원히 붙잡지 않도록 일정 시간이 지나면 스스로 끊는다.
#    (브라우저의 EventSource가 알아서 재연결하므로 사용자는 끊긴 걸 모른다)
# ==========================================
DM_STREAM_INTERVAL = 1      # 스트림이 DB를 다시 확인하는 주기(초)
DM_STREAM_TICKS = 300       # 1초 x 300 = 약 5분 뒤 스스로 종료 -> 재연결
DM_MAX_CONTENT_LEN = 1000   # 메시지 한 통 최대 길이
PARTY_MEMBER_LIMIT = 50     # 파티원 찾기 팝업에 한 번에 보여줄 최대 인원

# room_id + _id 조합으로 "이 대화방의 N번 이후 메시지"를 자주 조회하므로 인덱스를 걸어둔다
db.dm_messages.create_index([("room_id", 1), ("_id", 1)])


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
    # 허브 DM 카드에 "안 읽은 쪽지 N" 배지를 띄우기 위한 값
    dm_unread = db.dm_messages.count_documents({"receiver_id": user_id, "read": False})
    return render_template('hub.html', nickname=nickname, test_done=test_done, dm_unread=dm_unread)


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

# ==========================================
# DM 공용 헬퍼
# ==========================================
def _dm_room_id(id_a, id_b):
    """두 사람의 users.id를 정렬해서 붙인다.
    A->B 와 B->A 가 같은 방을 가리키도록 만들기 위한 것이다.
    (정렬을 안 하면 "aaa|bbb" 와 "bbb|aaa" 가 다른 방이 되어 대화가 둘로 쪼개진다)"""
    return "|".join(sorted([id_a, id_b]))


def _dm_to_dict(m):
    """DM 문서를 화면에 넘길 형태로 변환. api_comment_list와 같은 규칙을 따른다."""
    return {
        "id": str(m["_id"]),                    # ObjectId는 그대로 jsonify 못 하니 문자열로
        "sender_id": m["sender_id"],
        "sender_nickname": m["sender_nickname"],
        "content": m["content"],
        "created_at": m["created_at"].isoformat(),
    }


def _find_partner(nickname):
    """닉네임으로 상대를 찾는다. 없으면 None.
    URL에는 닉네임을 쓰고 DB에는 users.id를 저장하는 것이
    /result/<nickname>, /api/compatibility 와 동일한 이 프로젝트의 관습이다."""
    if not nickname:
        return None
    return db.users.find_one({"nickname": nickname.strip()})


def _viewer_id_or_none():
    """로그인했으면 users.id를, 아니면 None을 돌려준다.
    /result/<nickname> 처럼 비로그인도 볼 수 있는 화면에서
    DM 버튼을 보여줄지 말지 판단하는 데 쓴다."""
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        # 토큰이 만료됐거나 깨졌어도 공개 화면은 그냥 보여줘야 하므로 삼킨다
        return None


# ==========================================
# 화면 렌더링 라우터 — DM
# ==========================================
@app.route('/dm')
@jwt_required()
def dm_list():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id
    return render_template('dm.html', nickname=nickname)


@app.route('/dm/<nickname>')
@jwt_required()
def dm_room(nickname):
    user_id = get_jwt_identity()

    partner = _find_partner(nickname)
    if not partner:
        return redirect(url_for('dm_list'))         # 없는 닉네임이면 그냥 목록으로

    if partner['id'] == user_id:
        return redirect(url_for('dm_list'))         # 자기 자신과의 대화방은 만들지 않는다

    partner_class = MBTI_MAP.get(partner.get('mbti'))   # 아직 테스트 안 했으면 None

    return render_template(
        'dm_room.html',
        viewer_id=user_id,                          # 말풍선을 좌/우 어느 쪽에 그릴지 판단용
        partner_nickname=partner.get('nickname'),
        partner_class_name=(partner_class['class_name'] if partner_class else None),
        partner_mbti=(partner_class['mbti'] if partner_class else None),
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
        can_dm=True,                # 로그인한 본인 화면이므로 DM 버튼을 보여준다
    )

@app.route('/result/<nickname>')
def result_public(nickname):
    user_info = db.users.find_one({"nickname": nickname})
    if not user_info:
        return redirect(url_for('home'))

    user_mbti = user_info.get('mbti')
    my_class = MBTI_MAP.get(user_mbti)
    if not my_class:
        return redirect(url_for('home'))   # 아직 테스트 안 한 유저면 그냥 로그인 화면으로

    # 이 라우트는 공유 링크라 로그인 없이도 열린다.
    # 비로그인 방문자에게 DM 버튼을 보여주면 눌러도 로그인 화면으로 튕기므로 아예 숨긴다.
    viewer_id = _viewer_id_or_none()

    return render_template(
        'result.html',
        my_class=my_class,
        nickname=user_info.get('nickname'),
        best_match=MBTI_MAP.get(my_class['best_match']),
        worst_match=MBTI_MAP.get(my_class['worst_match']),
        can_dm=bool(viewer_id),
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

    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)   # 0 이하로 들어와도 1페이지로 보정

    page_size = 15   # 한 페이지에 보여줄 게시글 수

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
            return max(fuzz.partial_ratio(query, f) for f in fields)

        scored = [(score_of(p), p) for p in all_posts]
        scored = [(s, p) for s, p in scored if s >= SIMILARITY_THRESHOLD]

        if not scored:
            return jsonify({"result": "success", "posts": [], "no_results": True, "page": 1, "total_pages": 0})

        scored.sort(key=lambda sp: sp[1]['created_at'], reverse=(sort != 'oldest'))
        scored.sort(key=lambda sp: sp[0], reverse=True)
        matched_posts = [p for _, p in scored]
    else:
        matched_posts = all_posts
        matched_posts.sort(key=lambda p: p['created_at'], reverse=(sort != 'oldest'))

    # 전체 목록 중 이번 page에 해당하는 구간만 잘라내는 부분 (기존엔 없었음)
    total_count = len(matched_posts)
    total_pages = max((total_count + page_size - 1) // page_size, 1)   # 올림 나눗셈
    page = min(page, total_pages)   # 존재하지 않는 뒷페이지 요청 방어

    start = (page - 1) * page_size
    page_posts = matched_posts[start:start + page_size]

    result = []
    for p in page_posts:
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
    return jsonify({"result": "success", "posts": result, "no_results": False, "page": page, "total_pages": total_pages})

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

@app.route('/api/compatibility', methods=['GET'])
@jwt_required()
def api_compatibility():
    friend_nickname = (request.args.get('nickname') or '').strip()
    if not friend_nickname:
        return jsonify({"result": "fail", "msg": "닉네임을 입력해주세요."}), 400

    user_id = get_jwt_identity()
    me_info = db.users.find_one({"id": user_id})
    me_mbti = me_info.get('mbti') if me_info else None
    if not me_mbti:
        return jsonify({"result": "fail", "msg": "먼저 성향 테스트를 진행해주세요."}), 400

    friend_info = db.users.find_one({"nickname": friend_nickname})
    if not friend_info:
        return jsonify({"result": "fail", "msg": "해당 닉네임의 모험가를 찾을 수 없습니다."}), 404

    friend_mbti = friend_info.get('mbti')
    if not friend_mbti:
        return jsonify({"result": "fail", "msg": "그 모험가는 아직 테스트를 진행하지 않았습니다."}), 404

    me_class = MBTI_MAP.get(me_mbti)
    friend_class = MBTI_MAP.get(friend_mbti)

    def relation_of(viewer_class, other_mbti, other_class_name):
        if viewer_class.get('best_match') == other_mbti:
            return {"emoji": "💚", "tag": "duo", "description": f"{other_class_name}와(과)는 환상의 듀오예요! 함께라면 어떤 던전도 든든합니다."}
        if viewer_class.get('worst_match') == other_mbti:
            return {"emoji": "💔", "tag": "brain", "description": f"{other_class_name}와(과)는 충돌 주의! 서로 다른 플레이 스타일을 이해하는 노력이 필요해요."}
        return {"emoji": "🙂", "tag": "neutral", "description": f"{other_class_name}와(과)는 무난한 케미예요. 특별히 잘 맞거나 안 맞는 조합은 아니에요."}

    return jsonify({
        "result": "success",
        "friend": {
            "nickname": friend_info.get('nickname'),
            "class_name": friend_class['class_name'],
            "mbti": friend_class['mbti'],
        },
        "me": {
            "class_name": me_class['class_name'],
            "mbti": me_class['mbti'],
        },
        "compatibility": {
            "me_to_friend": relation_of(me_class, friend_mbti, friend_class['class_name']),
            "friend_to_me": relation_of(friend_class, me_mbti, me_class['class_name']),
        },
    })

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

    if post['author_id'] != user_id:
        return jsonify({"result": "fail", "msg": "해당 게시물의 작성자가 아닙니다."}), 403

    db.posts.delete_one({"_id": oid})
    db.comments.delete_many({"post_id": oid})   # 글이 사라지면 딸린 댓글도 같이 정리 (안 하면 고아 댓글이 남음)

    return jsonify({"result": "success", "msg": "게시물이 삭제되었습니다."})


# ==========================================
# API 라우터 — DM
# 메시지는 전부 dm_messages 컬렉션에만 쌓인다. 서버 메모리에 들고 있는 것은 없다.
# ==========================================

# ------------------------------------------
# 대화 목록 (내가 주고받은 상대들)
# ------------------------------------------
@app.route('/api/dm/rooms', methods=['GET'])
@jwt_required()
def api_dm_rooms():
    user_id = get_jwt_identity()

    # 최신순으로 훑으면서 방마다 "처음 만난 것 = 마지막 메시지"로 잡는다.
    # 게시글 목록(api_community_list)도 파이썬에서 집계하는 방식이라 스타일을 맞췄다.
    messages = db.dm_messages.find(
        {"$or": [{"sender_id": user_id}, {"receiver_id": user_id}]}
    ).sort("_id", -1)

    rooms = {}
    for m in messages:
        room_id = m["room_id"]

        if room_id not in rooms:
            # 상대가 누구인지: 내가 보낸 쪽이면 receiver, 받은 쪽이면 sender
            if m["sender_id"] == user_id:
                partner_id, partner_nickname = m["receiver_id"], m["receiver_nickname"]
            else:
                partner_id, partner_nickname = m["sender_id"], m["sender_nickname"]

            partner_info = db.users.find_one({"id": partner_id})
            partner_class = MBTI_MAP.get(partner_info.get('mbti')) if partner_info else None

            rooms[room_id] = {
                "partner_nickname": partner_nickname,
                "partner_class_name": (partner_class['class_name'] if partner_class else None),
                "partner_mbti": (partner_class['mbti'] if partner_class else None),
                "last_content": m["content"],
                "last_created_at": m["created_at"].isoformat(),
                "unread": 0,
            }

        # 안 읽은 것은 "내가 받은 것" 중 read가 False인 것만 센다
        if m["receiver_id"] == user_id and not m.get("read"):
            rooms[room_id]["unread"] += 1

    return jsonify({"result": "success", "rooms": list(rooms.values())})


# ------------------------------------------
# 메시지 조회 (대화창 첫 로딩 + 스트림이 막혔을 때의 폴백 폴링)
#   after 를 주면 그 이후에 생긴 것만 돌려준다
# ------------------------------------------
@app.route('/api/dm/messages', methods=['GET'])
@jwt_required()
def api_dm_message_list():
    user_id = get_jwt_identity()

    partner = _find_partner(request.args.get('with'))
    if not partner:
        return jsonify({"result": "fail", "msg": "해당 닉네임의 모험가를 찾을 수 없습니다."}), 404
    if partner['id'] == user_id:
        return jsonify({"result": "fail", "msg": "자기 자신에게는 쪽지를 보낼 수 없습니다."}), 400

    query = {"room_id": _dm_room_id(user_id, partner['id'])}

    after = request.args.get('after')
    if after:
        try:
            query["_id"] = {"$gt": ObjectId(after)}
        except InvalidId:
            return jsonify({"result": "fail", "msg": "잘못된 메시지 id 입니다."}), 400

    messages = list(db.dm_messages.find(query).sort("_id", 1))

    # 화면에 띄운 순간 "읽음"으로 처리한다 (내가 받은 것만)
    db.dm_messages.update_many(
        {"room_id": query["room_id"], "receiver_id": user_id, "read": False},
        {"$set": {"read": True}}
    )

    return jsonify({"result": "success", "messages": [_dm_to_dict(m) for m in messages]})


# ------------------------------------------
# 메시지 전송
# ------------------------------------------
@app.route('/api/dm/messages', methods=['POST'])
@jwt_required()
def api_dm_message_create():
    user_id = get_jwt_identity()
    user_info = db.users.find_one({"id": user_id})
    nickname = (user_info.get('nickname') if user_info else None) or user_id

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()

    partner = _find_partner(data.get('to'))
    if not partner:
        return jsonify({"result": "fail", "msg": "해당 닉네임의 모험가를 찾을 수 없습니다."}), 404
    if partner['id'] == user_id:
        return jsonify({"result": "fail", "msg": "자기 자신에게는 쪽지를 보낼 수 없습니다."}), 400

    if not content:
        return jsonify({"result": "fail", "msg": "내용을 입력해주세요."}), 400
    if len(content) > DM_MAX_CONTENT_LEN:
        return jsonify({"result": "fail", "msg": f"쪽지는 {DM_MAX_CONTENT_LEN}자까지 보낼 수 있습니다."}), 400

    db.dm_messages.insert_one({
        "room_id": _dm_room_id(user_id, partner['id']),   # 양방향이 같은 방을 보도록
        "sender_id": user_id,                             # 권한 체크용 (고유값)
        "sender_nickname": nickname,                      # 화면 표시용
        "receiver_id": partner['id'],
        "receiver_nickname": partner.get('nickname'),
        "content": content,
        "created_at": datetime.now(timezone.utc),         # 정렬용
        "read": False,
    })
    return jsonify({"result": "success", "msg": "쪽지를 보냈습니다."})


# ------------------------------------------
# 실시간 스트림 (SSE)
#   웹소켓 라이브러리 없이 Flask 내장 Response 만으로 서버->브라우저 push를 만든다.
#   EventSource는 헤더를 못 붙이지만 같은 주소면 쿠키를 자동으로 보내고,
#   JWT_TOKEN_LOCATION에 'cookies'가 있어서 @jwt_required()가 그대로 통한다.
# ------------------------------------------
@app.route('/api/dm/stream', methods=['GET'])
@jwt_required()
def api_dm_stream():
    user_id = get_jwt_identity()

    partner = _find_partner(request.args.get('with'))
    if not partner:
        return jsonify({"result": "fail", "msg": "해당 닉네임의 모험가를 찾을 수 없습니다."}), 404
    if partner['id'] == user_id:
        return jsonify({"result": "fail", "msg": "자기 자신에게는 쪽지를 보낼 수 없습니다."}), 400

    room_id = _dm_room_id(user_id, partner['id'])

    after = request.args.get('after')
    if after:
        try:
            after = ObjectId(after)
        except InvalidId:
            return jsonify({"result": "fail", "msg": "잘못된 메시지 id 입니다."}), 400

    def event_stream(last_id):
        # 정해진 횟수만 돌고 스스로 끝낸다. 안 그러면 이 연결이 스레드를 영원히 붙잡는다.
        # 끊겨도 브라우저의 EventSource가 알아서 다시 연결하므로 사용자는 모른다.
        for _ in range(DM_STREAM_TICKS):
            query = {"room_id": room_id}
            if last_id:
                query["_id"] = {"$gt": last_id}

            new_messages = list(db.dm_messages.find(query).sort("_id", 1))

            if new_messages:
                for m in new_messages:
                    last_id = m["_id"]
                    yield "data: " + json.dumps(_dm_to_dict(m), ensure_ascii=False) + "\n\n"
            else:
                # 주석 줄. 끊긴 연결을 감지하고 중간 프록시가 타임아웃으로 끊는 것도 막아준다
                yield ": keep-alive\n\n"

            time.sleep(DM_STREAM_INTERVAL)

    return Response(
        event_stream(after),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',   # nginx가 이 응답만 버퍼링하지 않게 한다 (EC2 설정 불필요)
        },
    )


# ------------------------------------------
# 파티원 찾기 — 같은 MBTI(직업)를 가진 유저 목록
# ------------------------------------------
@app.route('/api/party/members', methods=['GET'])
@jwt_required()
def api_party_members():
    user_id = get_jwt_identity()

    mbti = (request.args.get('mbti') or '').strip().upper()
    if mbti not in MBTI_MAP:
        return jsonify({"result": "fail", "msg": "알 수 없는 유형입니다: " + mbti}), 400

    # 나 자신은 목록에서 뺀다 (자기 자신에게 DM 보낼 일은 없으므로)
    users = db.users.find({"mbti": mbti, "id": {"$ne": user_id}}).limit(PARTY_MEMBER_LIMIT)

    members = [{"nickname": u.get('nickname')} for u in users if u.get('nickname')]

    return jsonify({
        "result": "success",
        "mbti": mbti,
        "class_name": MBTI_MAP[mbti]['class_name'],
        "members": members,
    })


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
