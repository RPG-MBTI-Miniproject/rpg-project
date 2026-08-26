// ==========================================
// app.py 계약 기준
//   POST /api/login   body {id, password}
//                     -> {result:"success", access_token:"..."} | {result:"fail", msg:"..."}
//   POST /api/signup  body {id, password, nickname}
//                     -> {result:"success", msg:"..."}          | {result:"fail", msg:"..."}
// ==========================================

const TOKEN_KEY = 'JWT_TOKEN';   // test.js / result.html 과 동일한 키를 써야 함

// ------------------------------------------
// [이정욱] 로그인 폼 제출 이벤트 제어 및 AJAX POST 요청
// ------------------------------------------
const loginForm = document.getElementById('login-form');

loginForm?.addEventListener('submit', async function (e) {
    e.preventDefault();

    // 1. ID/PW 값 가져오기
    const id = loginForm.querySelector('input[name="username"]').value.trim();
    const password = loginForm.querySelector('input[name="password"]').value;

    if (!id || !password) {
        alert('아이디와 비밀번호를 모두 입력해주세요.');
        return;
    }

    try {
        // 2. '/api/login'으로 전송 — app.py는 키 이름을 'id'로 받는다
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, password: password })
        });
        const data = await res.json();

        if (data.result === 'success') {
            // 3. 서버에서 받은 JWT를 localStorage에 저장 (API 호출용)
            //    SSR 페이지(/result)용 쿠키는 서버가 직접 심어준다
            localStorage.setItem(TOKEN_KEY, data.access_token);
            // 4. 저장 직후 허브(메뉴) 화면으로 이동
            window.location.href = '/home';
        } else {
            alert(data.msg || '아이디 또는 비밀번호가 올바르지 않습니다.');
        }
    } catch (err) {
        console.error('로그인 요청 실패:', err);
        alert('서버와 통신할 수 없습니다.');
    }
});

// ------------------------------------------
// [이정욱] 회원가입 폼 제출 이벤트 제어 및 AJAX POST 요청
// ------------------------------------------
const signupForm = document.getElementById('signup-form');

signupForm?.addEventListener('submit', async function (e) {
    e.preventDefault();

    // 1. 입력된 값들 가져오기
    const id = signupForm.querySelector('input[name="username"]').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const nickname = document.getElementById('nickname').value.trim();
    const errorBox = document.getElementById('error-message');

    const showError = (msg) => {
        if (errorBox) {
            errorBox.textContent = msg;
            errorBox.classList.remove('hidden');
        } else {
            alert(msg);
        }
    };

    if (!id || !password || !nickname) {
        showError('모든 항목을 입력해주세요.');
        return;
    }
    // 비밀번호 확인 체크
    if (password !== confirmPassword) {
        showError('비밀번호가 서로 일치하지 않습니다.');
        return;
    }

    try {
        // 2. '/api/signup'으로 전송
        const res = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, password: password, nickname: nickname })
        });
        const data = await res.json();

        // 3. 성공 시 alert 띄우고 로그인 화면으로 이동
        if (data.result === 'success') {
            alert(data.msg);
            window.location.href = '/';
        } else {
            showError(data.msg || '가입에 실패했습니다.');
        }
    } catch (err) {
        console.error('회원가입 요청 실패:', err);
        showError('서버와 통신할 수 없습니다.');
    }
});
