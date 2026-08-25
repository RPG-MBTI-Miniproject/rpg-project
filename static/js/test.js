// TODO: [이정욱] 12개의 질문-답변 세트 Array 객체 구축
const questions = [
    {
        q: "던전 보스방 문 앞에 도착했다. 당신의 행동은?",
        btnA: { text: "문에 함정이 없는지부터 꼼꼼하게 살핀다", type: "S" },
        btnB: { text: "일단 발로 차서 문을 열고 돌진한다", type: "N" }
    },
    // ... 총 12개 질문 채우기 (E/I, S/N, T/F, J/P 각각 3개씩)
];

// TODO: [이정욱] 상태 저장 변수
let currentQ = 0;
let scores = { E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 };

// TODO: [이정욱] 버튼 클릭 시 점수 누적 및 다음 문제로 화면 갱신하는 함수 작성
function nextQuestion(selectedType) {
    // 1. 선택한 type 점수 +1
    // 2. currentQ + 1
    // 3. 만약 currentQ가 12에 도달했다면 최종 결과 배열을 '/api/submit'으로 AJAX POST (이때 헤더에 JWT 포함!)
    // 4. 아니라면 DOM 조작을 통해 질문 텍스트와 버튼 텍스트 갈아끼우기 (SPA 로직)
}

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

// TODO: [이정욱] 상태 저장 변수
let currentQ = 0;
let scores = { E: 0, I: 0, S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 };

// TODO: [이정욱] 버튼 클릭 시 점수 누적 및 다음 문제로 화면 갱신하는 함수 작성
function nextQuestion(selectedType) {        
    // 1. 선택한 mbti type 점수 +1
    scores[selectedType]++;

    // 2. currentQ + 1
    currentQ++;

    // 3. 만약 currentQ가 12에 도달했다면 최종 결과 배열을 '/api/submit'으로 AJAX POST (이때 헤더에 JWT 포함!)
    if (currentQ >= questions.length) {

        let mbti = "";

        mbti += scores.E > scores.I ? "E" : "I";
        mbti += scores.S > scores.N ? "S" : "N";
        mbti += scores.T > scores.F ? "T" : "F";
        mbti += scores.J > scores.P ? "J" : "P";

        const resultClass = class_stats.find(
            item => item.mbti === mbti
        );

        console.log("점수:", scores);
        console.log("MBTI:", mbti);
        console.log("클래스:", resultClass);

        // localStorage에서 JWT 가져오기
        const token = localStorage.getItem("JWT_TOKEN");

        // 결과를 서버로 전송
        $.ajax({
            type: "POST",
            url: "/api/submit",

            headers: {
                "Authorization": "Bearer " + token
            },

            contentType: "application/json",

            data: JSON.stringify({
                mbti: mbti,
                class_name: resultClass.class_name,
                stats: resultClass.stats,
                scores: scores
            }),

            // 결과 저장 분기
            success: function (response) {
                console.log("결과 저장 성공:", response);

                // 결과 페이지로 이동
                window.location.href = "/result";
            },

            error: function (xhr) {
                console.log("결과 저장 실패:", xhr.responseText);
                alert("결과 저장에 실패했습니다.");
            }
        });

        return;
    }

    // 4. 다음 질문 객체 가져오기
    const question = questions[currentQ];

    // 5. 화면 변경
    $("#question-text").text(question.q);
    $("#btn-a").text(question.btnA.text);
    $("#btn-b").text(question.btnB.text);
}