// ==========================================
// [담당: JS 로직 동료]
//
// !! 이 파일 맨 위 "API 계약"은 절대 바꾸지 마세요 !!
// app.py(David 담당)가 이 형식 그대로 주고받습니다.
// URL, method, body 키 이름, 응답 키 이름 중 하나라도 다르게 짜면
// merge 후 전부 401/400/404로 터집니다.
//
// ------------------------------------------
// [게시글 목록 조회]
//   GET /api/community/posts?sort=&target=&q=&page=
//     sort   : "newest" | "oldest"
//     target : "all" | "title" | "content" | "nickname"
//     q      : 검색어 (없으면 파라미터 자체를 안 보내도 됨)
//     page   : 1부터 시작하는 숫자
//   응답 (검색 결과 있을 때):
//     { result: "success", no_results: false, page: 1, total_pages: 3,
//       posts: [ { id, title, content, author_id, author_nickname,
//                  created_at, updated_at, comment_count } ] }
//   응답 (유사도 70% 이상 결과가 하나도 없을 때):
//     { result: "success", no_results: true, page: 1, total_pages: 0, posts: [] }
//     -> 이 경우 #empty-msg 를 보여줘야 함
//
// [게시글 작성]
//   POST /api/community/posts   body { title, content }
//     -> { result: "success", post: {...} } | { result: "fail", msg: "..." }
//     실패 조건: title 또는 content가 2글자 미만이면 400 + msg
//
// [게시글 수정] (본인 글만 가능, 아니면 403)
//   PUT /api/community/posts/<post_id>   body { title, content }
//     -> { result: "success" } | { result: "fail", msg: "..." }
//
// [게시글 삭제] (본인 글만 가능, 아니면 403)
//   DELETE /api/community/posts/<post_id>
//     -> { result: "success" } | { result: "fail", msg: "..." }
//
// [댓글 목록 조회]
//   GET /api/community/posts/<post_id>/comments
//     -> { result: "success", comments: [ { id, post_id, author_id,
//          author_nickname, content, created_at, updated_at } ] }
//
// [댓글 작성]
//   POST /api/community/posts/<post_id>/comments   body { content }
//     -> { result: "success", comment: {...} } | { result: "fail", msg: "..." }
//
// [댓글 수정] (댓글 작성자 본인만 가능 — 글쓴이라도 남의 댓글 수정 불가, 아니면 403)
//   PUT /api/community/comments/<comment_id>   body { content }
//     -> { result: "success" } | { result: "fail", msg: "..." }
//
// [댓글 삭제] (댓글 작성자 본인 OR 그 글의 작성자 — 둘 중 하나면 가능, 아니면 403)
//   DELETE /api/community/comments/<comment_id>
//     -> { result: "success" } | { result: "fail", msg: "..." }
//
// 공통: 인증은 서버가 쿠키로 처리하므로 fetch에 Authorization 헤더 안 붙여도 됨.
//       단, 쿠키 만료 시 서버가 401을 주니, 모든 fetch 공통 처리에서
//       "401이면 로그인 페이지로 보내기"를 반드시 넣을 것 (안 넣으면 이상한 에러로 보임).
// ==========================================

const MIN_LEN = 2;   // 검색어 / 제목 / 내용 최소 글자 수 (프론트에서도 막아야 서버 왕복 안 함)

// ------------------------------------------
// TODO 1. 공통 fetch 헬퍼 함수 만들기
//   이름은 자유 (예: apiFetch). 아래 조건을 반드시 만족해야 함:
//   - fetch 결과 status가 401이면: alert 띄우고 location.href = '/' 로 이동
//   - 응답 JSON을 파싱해서 result가 "fail"이거나 res.ok가 false면 에러 throw
//     (throw할 때 메시지는 서버가 준 msg를 그대로 써서 이유가 보이게 할 것 — 예전에
//      우리가 겪었던 "Bearer null" 사건처럼, 실패 이유를 숨기면 디버깅 지옥이 됨)
//   - 성공하면 파싱한 JSON을 return
// ------------------------------------------


// ==========================================
// [목록 화면] community.html 에서만 실행되는 부분
// 상세 화면(community_detail.html)에는 #post-list 요소가 없으므로
// 아래 블록 전체를 "#post-list가 있을 때만" 실행되게 감싸주세요.
// (안 그러면 상세 화면에서 null 참조 에러가 남)
// ==========================================

// TODO 2. 상태 변수 만들기
//   현재 정렬(sort), 검색 대상(target), 검색어(q), 현재 페이지(page)를
//   객체 하나로 묶어서 관리하면 편함. 초기값: newest / all / '' / 1

// TODO 3. "글쓰기" 버튼(#write-btn) 클릭 시 → #write-modal 의 hidden 클래스 제거
//   모달 안 입력창(#post-title-input, #post-content-input)은 비워서 시작

// TODO 4. 정렬 버튼(.sort-btn) 클릭 이벤트
//   - 클릭된 버튼에 active 클래스, 나머지는 제거
//   - 상태의 sort 값 갱신, page를 1로 리셋
//   - 목록 다시 불러오기

// TODO 5. 검색 버튼(#search-btn) 클릭 이벤트
//   - #search-input 값을 trim
//   - 입력했는데 MIN_LEN(2)글자 미만이면 alert로 안내하고 멈추기 (서버까지 보내지 말 것)
//   - #search-target 의 선택값도 같이 상태에 저장
//   - page를 1로 리셋하고 목록 다시 불러오기
//   (선택) input에서 Enter 키 눌러도 검색되게 하면 UX 좋음

// TODO 6. 게시글 목록 그리는 함수 만들기 (예: renderPosts(posts))
//   #post-list 를 비우고, posts 배열을 순회하며 한 줄씩 요소를 만들어 추가
//   각 줄은 클릭하면 `/community/{post.id}` 로 이동해야 함
//     (a 태그로 만들어서 href="/community/" + post.id 하는 게 제일 간단)
//   보여줄 정보: title, author_nickname, comment_count, created_at(날짜만 보기 좋게 포맷)

// TODO 7. 페이지네이션 그리는 함수 만들기 (예: renderPagination(page, totalPages))
//   #pagination 을 비우고, 1부터 totalPages까지 버튼 생성
//   현재 page와 같은 버튼엔 active 클래스
//   버튼 클릭 시: 상태의 page 갱신 후 목록 다시 불러오기

// TODO 8. 목록 불러오는 함수 만들기 (예: loadPosts())
//   - 현재 상태값들로 쿼리스트링 만들어서 GET /api/community/posts 호출
//     (q가 빈 문자열이면 쿼리에 아예 안 넣는 게 깔끔)
//   - 응답의 no_results가 true면: #post-list 비우고 #pagination 비우고
//     #empty-msg 의 hidden 클래스 제거
//   - 아니면: #empty-msg에 hidden 클래스 추가하고, renderPosts + renderPagination 호출
//   - 페이지 처음 로드될 때 한 번 자동으로 호출되어야 함 (스크립트 맨 아래에서 실행)

// TODO 9. 모달 "등록/저장"(#modal-submit-btn) 클릭 이벤트
//   - #post-title-input, #post-content-input 값을 trim
//   - 둘 중 하나라도 MIN_LEN 미만이면 #modal-error 에 안내 문구 넣고 hidden 제거, 멈추기
//   - 통과하면 POST /api/community/posts 호출 (title, content)
//   - 성공하면 모달 닫고(hidden 클래스 다시 추가) 목록 새로고침(loadPosts 재호출)
//   - 실패하면 #modal-error 에 서버가 준 msg 표시

// TODO 10. 모달 "취소"(#modal-cancel-btn) 클릭 시 → 모달 닫기


// ==========================================
// [상세 화면] community_detail.html 에서만 실행되는 부분
// 이 화면엔 아래 전역 변수가 이미 선언되어 있음 (community_detail.html 참고):
//   POST_ID, POST_AUTHOR_ID, VIEWER_ID, POST_TITLE, POST_CONTENT, POST_CREATED_AT
// #comment-list 요소가 있을 때만 이 블록이 실행되게 감싸주세요.
// ==========================================

// TODO 11. "수정"(#edit-post-btn) 버튼 — is_author일 때만 화면에 존재함
//   클릭 시 #write-modal 열고, 입력창에 POST_TITLE / POST_CONTENT 로 미리 채워넣기
//   "저장" 눌렀을 때는 (목록 화면과 다르게) POST가 아니라
//   PUT /api/community/posts/{POST_ID} 로 보내야 함 — 여기서 모드 구분이 필요함
//   (힌트: "지금 모달이 새글쓰기 모드인지 수정 모드인지"를 기억하는 변수 하나 두면 편함)

// TODO 12. "삭제"(#delete-post-btn) 버튼
//   confirm()으로 한 번 물어보고, 확인되면 DELETE /api/community/posts/{POST_ID}
//   성공하면 location.href = '/community' 로 목록으로 돌려보내기

// TODO 13. 댓글 목록 그리는 함수 만들기 (예: renderComments(comments))
//   #comment-count 에 comments.length 넣기
//   #comment-list 비우고 각 댓글마다 한 줄씩 그리기: 작성자 닉네임 + 내용 + [수정][삭제]
//
//   *** 권한 규칙 (반드시 이 조건대로) ***
//     - "수정" 버튼: comment.author_id === VIEWER_ID 일 때만 클릭 가능
//                    (글쓴이라도 남의 댓글은 수정 못 함 — 버튼을 비활성 스타일로 표시)
//     - "삭제" 버튼: comment.author_id === VIEWER_ID
//                    OR POST_AUTHOR_ID === VIEWER_ID  일 때 클릭 가능
//   권한 없는 버튼은 클릭이 안 되게 이벤트 자체를 안 붙이거나 disabled 클래스 처리할 것
//   (CSS의 .comment-actions span.disabled 참고 — 흐리게 표시)

// TODO 14. 댓글 불러오는 함수 (예: loadComments())
//   GET /api/community/posts/{POST_ID}/comments 호출 → renderComments 호출
//   페이지 로드 시 자동 실행되어야 함

// TODO 15. 댓글 등록(#comment-submit-btn) 클릭 이벤트
//   - #comment-input 값 trim, 비어있으면 alert 후 멈추기
//   - POST /api/community/posts/{POST_ID}/comments 호출 (content)
//   - 성공하면 입력창 비우고 loadComments() 다시 호출 (전체 다시 그리기)

// TODO 16. 댓글 "수정" 클릭 시
//   prompt() 등으로 새 내용 입력받아서
//   PUT /api/community/comments/{comment.id} 호출 → 성공하면 loadComments() 재호출

// TODO 17. 댓글 "삭제" 클릭 시
//   confirm() 확인 후 DELETE /api/community/comments/{comment.id}
//   → 성공하면 loadComments() 재호출
