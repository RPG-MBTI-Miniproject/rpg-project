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