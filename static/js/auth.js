// TODO: [이정욱] 로그인 폼 제출 이벤트 제어 및 AJAX POST 요청
document.getElementById('login-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    // 1. ID/PW 값 가져오기
    let userId = document.getElementById('userid').value;
    let userPw = document.getElementById('password').value;

    // 2. fetch() 또는 $.ajax()를 사용해 '/api/login'으로 전송
    $.ajax({
        type: "POST",
        url: "/api/login",
        
        contentType: 'application/json',

        data: JSON.stringify({ userId, userPw })                
    })
    .done(function(response) { 
        // 3. 성공 시 서버에서 받은 JWT를 localStorage에 저장                
        localStorage.setItem('JWT_TOKEN', response.token);
        // 4. 저장 직후 window.location.href = "/test" 로 이동
        window.location.href = "/test";
    })        
});

// TODO: [이정욱] 회원가입 폼 제출 이벤트 제어 및 AJAX POST 요청
document.getElementById('signup-form')?.addEventListener('submit', function(e) {
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

    if (!id || !password || !nickname || !confirmPassword) { // 이정욱 (0826 10:28)  confirmPassword 조건 추가 
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

