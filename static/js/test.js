// -----------------------------------  아래 수정한부분 ----------------------------------------
// TODO: [이정욱] 12개의 질문-답변 세트 Array 객체 구축 
const questions = [
    // =========================
    // E / I
    // =========================
    {
        id: 1,
        axis: "EI",
        q: '레이드 입장 직전, 파티장이 "마이크 가능하신 분?"이라고 묻는다.',
        btnA: {
            text: "일단 켠다. 어차피 같이 할 거면 얘기하면서 하는 게 편하다.",
            type: "E"
        },
        btnB: {
            text: "듣는 건 괜찮은데 말은 꼭 필요할 때만 하고 싶다.",
            type: "I"
        }
    },
    {
        id: 2,
        axis: "EI",
        q: '길드 채팅에서 갑자기 "심심한 사람 던전 ㄱ?"가 올라왔다.',
        btnA: {
            text: "누가 가는지, 무슨 던전인지 보고 결정한다.",
            type: "I"
        },
        btnB: {
            text: '무슨 던전인지 몰라도 일단 "ㄱㄱ"부터 친다.',
            type: "E"
        }
    },
    {
        id: 3,
        axis: "EI",
        q: "공팟에 들어왔는데 다들 조용하다. 출발도 안 하고 있다.",
        btnA: {
            text: '"출발할까요?" 하고 먼저 말을 꺼낸다.',
            type: "E"
        },
        btnB: {
            text: "파티장이 진행할 때까지 기다린다.",
            type: "I"
        }
    },

    // =========================
    // S / N
    // =========================
    {
        id: 4,
        axis: "SN",
        q: "보스가 처음 보는 패턴을 사용했다.",
        btnA: {
            text: '"이 패턴 다음에 뭔가 오겠는데?" 전체 패턴 구조부터 예상한다.',
            type: "N"
        },
        btnB: {
            text: "바닥, 모션, 공격 범위를 보고 피하는 법부터 찾는다.",
            type: "S"
        }
    },
    {
        id: 5,
        axis: "SN",
        q: "공략 사이트에 '현재 1티어 빌드'가 올라왔다.",
        btnA: {
            text: "검증된 빌드니까 일단 써보고 성능을 확인한다.",
            type: "S"
        },
        btnB: {
            text: "그걸 보면서 내 방식으로 바꿀 수 있는 조합부터 생각한다.",
            type: "N"
        }
    },
    {
        id: 6,
        axis: "SN",
        q: "처음 보는 퍼즐 던전에 들어왔다.",
        btnA: {
            text: "주변 오브젝트를 하나씩 직접 조사하면서 규칙을 찾는다.",
            type: "S"
        },
        btnB: {
            text: "장치들의 배치를 보고 제작자가 의도한 규칙부터 추측한다.",
            type: "N"
        }
    },

    // =========================
    // T / F
    // =========================
    {
        id: 7,
        axis: "TF",
        q: "레이드에서 한 명 때문에 세 번째 전멸했다.",
        btnA: {
            text: '분위기 터지면 진짜 끝이다. 일단 "ㄱㅊ 다시 해봐요"부터 친다.',
            type: "F"
        },
        btnB: {
            text: "누구 때문인지보다 정확히 어느 패턴에서 문제가 생겼는지부터 확인한다.",
            type: "T"
        }
    },
    {
        id: 8,
        axis: "TF",
        q: "친구가 자기 캐릭터 딜이 너무 안 나온다며 세팅을 봐달라고 한다.",
        btnA: {
            text: "스탯, 장비, 스킬트리를 확인해서 어디가 문제인지 찾아준다.",
            type: "T"
        },
        btnB: {
            text: "어떤 플레이를 좋아하는지 물어보고 거기에 맞는 세팅을 찾아준다.",
            type: "F"
        }
    },
    {
        id: 9,
        axis: "TF",
        q: "친구가 성능은 별로지만 정말 좋아하는 직업을 하고 있다.",
        btnA: {
            text: "하고 싶은 걸 하는 게 게임이지. 그 직업을 살릴 방법을 같이 찾아본다.",
            type: "F"
        },
        btnB: {
            text: "성능 때문에 계속 힘들어한다면 더 좋은 직업으로 바꾸는 것도 권한다.",
            type: "T"
        }
    },

    // =========================
    // J / P
    // =========================
    {
        id: 10,
        axis: "JP",
        q: "내일 신규 레이드가 열린다.",
        btnA: {
            text: "공략 영상, 준비물, 세팅 정도는 미리 확인한다.",
            type: "J"
        },
        btnB: {
            text: "첫날인데 헤딩하는 맛이지. 일단 들어가서 맞아본다.",
            type: "P"
        }
    },
    {
        id: 11,
        axis: "JP",
        q: "퀘스트를 하다가 지도에 표시되지 않은 수상한 동굴을 발견했다.",
        btnA: {
            text: "저걸 어떻게 그냥 지나가? 바로 들어간다.",
            type: "P"
        },
        btnB: {
            text: "지금 하던 퀘스트부터 끝내고 나중에 돌아온다.",
            type: "J"
        }
    },
    {
        id: 12,
        axis: "JP",
        q: "인벤토리가 거의 꽉 찼다.",
        btnA: {
            text: "마을에서 필요 없는 아이템을 정리하고 다시 출발한다.",
            type: "J"
        },
        btnB: {
            text: "아직 몇 칸 남았다. 진짜 꽉 차면 그때 생각한다.",
            type: "P"
        }
    }
];

// ==========================================
// app.py 계약 기준
//   POST /api/submit  (JWT 필요)
//     body   {answers: ["I","N","T","J"]}     ← 서버가 "".join(answers) 로 합침
//     header Authorization: Bearer <토큰>
// ==========================================

const TOKEN_KEY = 'JWT_TOKEN';   // auth.js 와 같은 키

// [이정욱] 상태 저장 변수
let currentQ = 0;
let scores = { E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 };

// 이전 버튼 구현을 위한 답변 기록: 몇 번째 문제에서 어떤 type을 골랐는지 순서대로 쌓아둔다.
// prevQuestion()에서 이 기록을 되짚어 점수를 되돌리는 데 쓴다 (없으면 "뒤로 가기"만 되고
// 점수는 이미 반영된 채로 남아 중복 집계되는 버그가 생긴다).
let answerHistory = [];

// ------------------------------------------
// 화면에 현재 질문 그리기 (진행도 포함, 이전 버튼 활성/비활성 포함)
// ------------------------------------------
function renderQuestion() {
    const question = questions[currentQ];

    document.getElementById('question-text').textContent = question.q;
    document.getElementById('btn-a').textContent = question.btnA.text;
    document.getElementById('btn-b').textContent = question.btnB.text;

    document.getElementById('q-num').textContent = currentQ + 1;
    const percent = ((currentQ + 1) / questions.length) * 100;
    document.getElementById('progress-bar-fill').style.width = percent.toFixed(2) + '%';

    // 1번 문제에서는 더 되돌아갈 곳이 없으니 이전 버튼을 비활성화한다
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) prevBtn.disabled = (currentQ === 0);
}

// ------------------------------------------
// [이정욱] 버튼 클릭 시 점수 누적 및 다음 문제로 화면 갱신
// ------------------------------------------
function nextQuestion(selectedType) {
    // 1. 선택한 mbti type 점수 +1
    scores[selectedType]++;

    // 2. 나중에 이전 버튼으로 되돌릴 수 있도록 이번 선택을 기록해둔다
    answerHistory.push(selectedType);

    // 3. currentQ + 1
    currentQ++;

    // 4. 12문항을 다 풀었으면 서버로 전송
    if (currentQ >= questions.length) {
        submitResult();
        return;
    }

    // 5. 아니라면 다음 질문으로 화면 갱신
    renderQuestion();
}

// ------------------------------------------
// [이정욱] 이전 버튼 클릭 시: 직전 답변의 점수를 되돌리고 한 문제 전으로 이동
// ------------------------------------------
function prevQuestion() {
    if (currentQ === 0) return;   // 1번 문제에서는 더 갈 곳이 없다

    const lastType = answerHistory.pop();   // 방금까지 답변으로 기록됐던 type
    scores[lastType]--;                     // 그 점수를 되돌린다 (중복 집계 방지)
    currentQ--;

    renderQuestion();
}

// ------------------------------------------
// 축별 승자를 모아 answers 배열 만들기
// 축마다 문항이 3개(홀수)라 동점이 나오지 않는다
// ------------------------------------------
function buildAnswers() {
    return [
        scores.E > scores.I ? 'E' : 'I',
        scores.S > scores.N ? 'S' : 'N',
        scores.T > scores.F ? 'T' : 'F',
        scores.J > scores.P ? 'J' : 'P'
    ];
}

// ------------------------------------------
// 결과를 '/api/submit' 으로 전송 (헤더에 JWT 포함)
// ------------------------------------------
async function submitResult() {
    const answers = buildAnswers();

    console.log('점수:', scores);
    console.log('MBTI:', answers.join(''));

    // 토큰이 있으면 헤더로 보내고, 없으면 서버가 쿠키로 인증한다
    const token = localStorage.getItem(TOKEN_KEY);
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    try {
        const res = await fetch('/api/submit', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ answers: answers })
        });

        if (res.status === 401) {
            alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
            window.location.href = '/';
            return;
        }

        const data = await res.json().catch(() => ({}));
        if (data.result !== 'success') {
            throw new Error(data.msg || ('HTTP ' + res.status));
        }

        window.location.href = '/result';
    } catch (err) {
        console.error('결과 저장 실패:', err);
        alert('결과 저장에 실패했습니다. ' + err.message);
    }
}

// ------------------------------------------
// 로그아웃 (test.html 의 버튼이 호출)
// localStorage 토큰과 서버가 심은 쿠키를 함께 정리
// ------------------------------------------
async function logout() {
    localStorage.removeItem(TOKEN_KEY);
    try {
        await fetch('/api/logout', { method: 'POST' });
    } catch (err) {
        console.error('로그아웃 요청 실패:', err);
    }
    window.location.href = '/';
}

// ------------------------------------------
// 친구 닉네임 검색 → 궁합 조회 0827 00:28 add (ljw)
// ------------------------------------------
async function searchFriendCompatibility() {

    // 1. 친구 닉네임 입력창 가져오기
    const friendInput =
        document.getElementById('search-friend-result');

    if (!friendInput) return;

    const nickname = friendInput.value.trim();

    // 2. 빈 값 검사
    if (!nickname) {
        alert('친구의 닉네임을 입력해주세요.');
        friendInput.focus();
        return;
    }

    try {
        // 3. 서버에 친구 궁합 요청
        const res = await fetch(
            `/api/compatibility?nickname=${encodeURIComponent(nickname)}`
        );

        // 로그인 만료
        if (res.status === 401) {
            alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
            location.href = '/';
            return;
        }

        const data = await res.json().catch(() => ({}));

        // 서버에서 실패 응답
        if (!res.ok || data.result !== 'success') {
            throw new Error(
                data.msg ||
                `궁합 정보를 불러오지 못했습니다. (HTTP ${res.status})`
            );
        }
        // 4. 친구 닉네임
        document.getElementById(
            'target-friend-name'
        ).textContent = data.friend.nickname;

        // ==================================
        // 내가 보는 친구
        // ==================================

        document.getElementById(
            'friend-class-name'
        ).textContent = data.friend.class_name;

        document.getElementById(
            'friend-mbti-text'
        ).textContent = `(${data.friend.mbti})`;

        document.getElementById(
            'me-to-friend-emoji'
        ).textContent =
            data.compatibility.me_to_friend.emoji;

        document.getElementById(
            'me-to-friend-tag'
        ).textContent =
            data.compatibility.me_to_friend.tag;

        document.getElementById(
            'me-to-friend-desc'
        ).textContent =
            data.compatibility.me_to_friend.description;


        // ==================================
        // 친구가 보는 나
        // ==================================

        document.getElementById(
            'my-class-name'
        ).textContent = data.me.class_name;

        document.getElementById(
            'my-mbti-text'
        ).textContent = `(${data.me.mbti})`;

        document.getElementById(
            'friend-to-me-emoji'
        ).textContent =
            data.compatibility.friend_to_me.emoji;

        document.getElementById(
            'friend-to-me-tag'
        ).textContent =
            data.compatibility.friend_to_me.tag;

        document.getElementById(
            'friend-to-me-desc'
        ).textContent =
            data.compatibility.friend_to_me.description;


        // 5. 숨겨져 있던 궁합 결과 화면 표시
        const resultSection =
            document.getElementById('friend-synergy-section');

        if (resultSection) {
            resultSection.style.display = 'block';
        }

    } catch (error) {
        console.error('친구 궁합 조회 실패:', error);

        alert(`궁합 조회 실패: ${error.message}`);
    }
}

// ------------------------------------------
// 페이지 로드 시작 처리
// ------------------------------------------
// 0827 00:39 ljw 추가: 결과 화면에는 a,b 버튼이 없으므로 이벤트 연결 아래와 같이 수정
document.addEventListener('DOMContentLoaded', () => {

    const btnA = document.getElementById('btn-a');
    const btnB = document.getElementById('btn-b');

    // test.html일 때만 실행
    if (btnA && btnB) {

        btnA.addEventListener('click', () => {
            nextQuestion(
                questions[currentQ].btnA.type
            );
        });

        btnB.addEventListener('click', () => {
            nextQuestion(
                questions[currentQ].btnB.type
            );
        });

        document.getElementById('prev-btn')
            ?.addEventListener('click', prevQuestion);

        renderQuestion();
    }

    const friendSearchBtn =
        document.getElementById('search-friend-btn');

    if (friendSearchBtn) {

        const friendSearchForm =
            friendSearchBtn.closest('form');

        friendSearchForm?.addEventListener(
            'submit',
            async (e) => {

                e.preventDefault();

                await searchFriendCompatibility();
            }
        );
    }
});
// 0827 00:39 ljw 주석 처리 : 결과 화면에는 a,b 버튼이 없으므로 이벤트 연결 수정
// document.addEventListener('DOMContentLoaded', () => {
//     // 로그인 여부는 서버가 /test 의 @jwt_required() 로 이미 막는다.
//     // 여기서 localStorage 만 보고 튕기면, 쿠키는 살아있는데 localStorage 만
//     // 비워진 사용자가 로그인 상태로 로그인 화면에 갇힌다.
//     document.getElementById('btn-a')
//         .addEventListener('click', () => nextQuestion(questions[currentQ].btnA.type));
//     document.getElementById('btn-b')
//         .addEventListener('click', () => nextQuestion(questions[currentQ].btnB.type));

//     document.getElementById('prev-btn')
//         ?.addEventListener('click', prevQuestion);

//     renderQuestion();   // 1번 문제를 화면에 그린다
// });