// TODO: [이정욱] 로그인 폼 제출 이벤트 제어 및 AJAX POST 요청
document.getElementById('login-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    // 1. ID/PW 값 가져오기
    // 2. fetch() 또는 $.ajax()를 사용해 '/api/login'으로 전송
    // 3. 성공 시 서버에서 받은 JWT를 localStorage에 저장
    // 4. 저장 직후 window.location.href = "/test" 로 이동
});

// TODO: [이정욱] 회원가입 폼 제출 이벤트 제어 및 AJAX POST 요청
document.getElementById('signup-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    // 1. 입력된 값들 가져오기 (비밀번호 확인 체크)
    // 2. '/api/signup'으로 전송
    // 3. 성공 시 alert 띄우고 '/'(로그인 창)으로 이동
});