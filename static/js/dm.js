// ==========================================
//  DM (쪽지) 화면 스크립트
//  dm.html(대화 목록) 과 dm_room.html(대화창) 이 같이 씁니다.
//  화면에 뭐가 있는지 보고 알아서 갈라집니다.
//
//  [API 계약] — app.py 와 이 형식 그대로 주고받습니다
//   GET  /api/dm/rooms
//        -> { result:"success", rooms:[ { partner_nickname, partner_class_name,
//             partner_mbti, last_content, last_created_at, unread } ] }
//   GET  /api/dm/messages?with=<닉네임>&after=<메시지id>
//        -> { result:"success", messages:[ { id, sender_id, sender_nickname,
//             content, created_at } ] }
//   POST /api/dm/messages   body { to:"<닉네임>", content:"..." }
//        -> { result:"success", msg:"..." }
//   GET  /api/dm/stream?with=<닉네임>&after=<메시지id>   (SSE)
//        -> data: { id, sender_id, sender_nickname, content, created_at }
//
//  인증은 서버가 쿠키로 처리하므로 fetch 에 Authorization 헤더를 붙이지 않습니다.
//  (community.js 와 같은 방식)
// ==========================================

const DM_POLL_INTERVAL = 2000;   // 스트림이 막혔을 때 폴백 폴링 주기(ms)


// ------------------------------------------
// 공통 helper
// community.js 의 apiFetch / hub.html 의 logout 과 같은 내용입니다.
// community.js 는 커뮤니티 화면 DOM 을 전제로 동작해서 여기서 불러올 수 없어
// 필요한 부분만 가져왔습니다.
// ------------------------------------------
async function apiFetch(url, options = {}) {
    const config = {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers },
    };

    const res = await fetch(url, config);

    if (res.status === 401) {
        alert("401 Error. 로그인 페이지로 이동합니다.");
        window.location.href = '/';
        throw new Error('로그인이 필요합니다.');
    }

    let data;
    try {
        data = await res.json();
    } catch (parseError) {
        if (!res.ok) throw new Error(`서버 에러가 발생했습니다. (상태 코드: ${res.status})`);
        throw new Error(`응답 데이터(JSON) 파싱에 실패했습니다. (상태 코드: ${res.status})`);
    }

    if (!res.ok || data?.result === 'fail') {
        throw new Error(data?.msg || ' 요청 처리 중 에러가 발생했습니다.');
    }

    return data;
}

// innerHTML 에 값을 넣기 전에 태그를 무력화합니다
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(isoString) {
    return new Date(isoString).toLocaleDateString('ko-KR');
}


// ==========================================
// 1) 대화 목록 화면 (dm.html)
// ==========================================
async function loadRoomList() {
    const listEl = document.getElementById('dm-room-list');
    if (!listEl) return;

    try {
        const data = await apiFetch('/api/dm/rooms');
        const rooms = data.rooms || [];

        if (rooms.length === 0) {
            listEl.innerHTML = `
                <div class="dm-empty">
                    <div class="dm-empty-icon">✉️</div>
                    <div class="dm-empty-text">
                        아직 주고받은 쪽지가 없습니다.<br>
                        커뮤니티나 결과 화면에서 다른 모험가에게 먼저 말을 걸어보세요!
                    </div>
                </div>
            `;
            return;
        }

        listEl.innerHTML = rooms.map(room => {
            const classText = room.partner_class_name
                ? `${escapeHtml(room.partner_class_name)} (${escapeHtml(room.partner_mbti)})`
                : '';
            const unreadBadge = room.unread > 0
                ? `<span class="dm-unread-badge">${room.unread}</span>`
                : '';

            return `
                <a class="dm-room-item" href="/dm/${encodeURIComponent(room.partner_nickname)}">
                    <div class="dm-room-avatar">🧙</div>
                    <div class="dm-room-main">
                        <div class="dm-room-top">
                            <span class="dm-room-nickname">${escapeHtml(room.partner_nickname)}</span>
                            <span class="dm-room-class">${classText}</span>
                        </div>
                        <div class="dm-room-preview">${escapeHtml(room.last_content)}</div>
                    </div>
                    <div class="dm-room-side">
                        <span class="dm-room-time">${formatDate(room.last_created_at)}</span>
                        ${unreadBadge}
                    </div>
                </a>
            `;
        }).join('');

    } catch (error) {
        console.error('쪽지함을 불러오지 못했습니다:', error);
        listEl.innerHTML = `
            <div class="dm-empty">
                <div class="dm-empty-icon">⚠️</div>
                <div class="dm-empty-text">쪽지함을 불러오지 못했습니다.<br>${escapeHtml(error.message)}</div>
            </div>
        `;
    }
}


// ==========================================
// 2) 대화창 (dm_room.html)
// ==========================================
function initChatRoom() {
    const listEl = document.getElementById('dm-message-list');
    if (!listEl) return;

    const inputEl = document.getElementById('dm-input');
    const sendBtn = document.getElementById('dm-send-btn');
    const statusEl = document.getElementById('dm-status');

    let lastId = null;          // 마지막으로 받은 메시지 id (증분 조회 커서)
    let lastDateLabel = null;   // 날짜 구분선을 중복해서 넣지 않기 위한 값
    let source = null;          // EventSource
    let pollTimer = null;       // 폴백 폴링 타이머

    // ---- 화면 그리기 ----
    function setStatus(text, offline) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.classList.toggle('offline', !!offline);
    }

    function isScrolledToBottom() {
        // 사용자가 위로 올려 예전 대화를 보는 중이면 강제로 내리지 않는다
        return listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight < 80;
    }

    function appendMessage(message) {
        // 같은 메시지가 스트림과 폴링으로 두 번 들어오는 것을 막는다
        if (listEl.querySelector(`[data-message-id="${message.id}"]`)) return;

        const dateLabel = formatDate(message.created_at);
        if (dateLabel !== lastDateLabel) {
            const divider = document.createElement('div');
            divider.className = 'dm-date-divider';
            divider.textContent = dateLabel;
            listEl.appendChild(divider);
            lastDateLabel = dateLabel;
        }

        const isMine = message.sender_id === DM_VIEWER_ID;

        const row = document.createElement('div');
        row.className = `dm-message-row ${isMine ? 'mine' : 'theirs'}`;
        row.dataset.messageId = message.id;
        row.innerHTML = `
            <div class="dm-bubble">${escapeHtml(message.content)}</div>
            <span class="dm-message-time">${formatTime(message.created_at)}</span>
        `;

        const shouldScroll = isScrolledToBottom();
        listEl.appendChild(row);
        if (shouldScroll || isMine) {
            listEl.scrollTop = listEl.scrollHeight;
        }
    }

    function appendMessages(messages) {
        messages.forEach(message => {
            appendMessage(message);
            lastId = message.id;
        });
    }

    // ---- 서버에서 가져오기 ----
    async function fetchMessages() {
        const params = new URLSearchParams({ with: DM_PARTNER_NICKNAME });
        if (lastId) params.set('after', lastId);

        const data = await apiFetch(`/api/dm/messages?${params.toString()}`);
        appendMessages(data.messages || []);
    }

    // ---- 폴백: 스트림이 안 되면 주기적으로 직접 물어본다 ----
    function startPolling() {
        if (pollTimer) return;
        setStatus('연결 재시도', true);
        pollTimer = setInterval(async () => {
            try {
                await fetchMessages();
            } catch (error) {
                console.error('쪽지를 불러오지 못했습니다:', error);
            }
        }, DM_POLL_INTERVAL);
    }

    function stopPolling() {
        if (!pollTimer) return;
        clearInterval(pollTimer);
        pollTimer = null;
    }

    // ---- 실시간: SSE 구독 ----
    // 서버가 약 5분 뒤 스스로 스트림을 닫는데, EventSource 가 알아서 다시 연결합니다.
    // 그래서 onerror 가 떠도 바로 폴링으로 갈아타지 않고 잠깐 기다려 봅니다.
    function connectStream() {
        if (typeof EventSource === 'undefined') {
            startPolling();
            return;
        }

        const params = new URLSearchParams({ with: DM_PARTNER_NICKNAME });
        if (lastId) params.set('after', lastId);

        source = new EventSource(`/api/dm/stream?${params.toString()}`);

        source.onopen = () => {
            stopPolling();
            setStatus('실시간', false);
        };

        source.onmessage = (event) => {
            stopPolling();
            setStatus('실시간', false);
            try {
                const message = JSON.parse(event.data);
                appendMessage(message);
                lastId = message.id;
            } catch (error) {
                console.error('쪽지 데이터 해석에 실패했습니다:', error);
            }
        };

        source.onerror = () => {
            // 재연결 중이면 브라우저가 알아서 살려낸다. 그동안만 폴링으로 버틴다.
            startPolling();

            // 아예 닫혔다면(서버가 401 등을 준 경우) 스트림은 포기하고 폴링만 쓴다
            if (source && source.readyState === EventSource.CLOSED) {
                source = null;
            }
        };
    }

    // ---- 보내기 ----
    async function sendMessage() {
        const content = inputEl.value.trim();
        if (!content) {
            alert("내용을 입력해 주세요!");
            return;
        }

        sendBtn.disabled = true;
        try {
            await apiFetch('/api/dm/messages', {
                method: 'POST',
                body: JSON.stringify({ to: DM_PARTNER_NICKNAME, content: content }),
            });

            inputEl.value = '';
            // 내가 보낸 것도 스트림을 통해 돌아오지만, 바로 보이도록 한 번 당겨온다
            await fetchMessages();
        } catch (error) {
            console.error('쪽지 전송에 실패했습니다:', error);
            alert(`쪽지를 보내지 못했습니다: ${error.message}`);
        } finally {
            sendBtn.disabled = false;
            inputEl.focus();
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.isComposing) {   // 한글 조합 중 Enter 는 무시
            event.preventDefault();
            sendMessage();
        }
    });

    // 화면을 떠날 때 연결을 정리한다 (서버 스레드를 붙잡고 있지 않도록)
    window.addEventListener('beforeunload', () => {
        if (source) source.close();
        stopPolling();
    });

    // ---- 시작: 기록을 먼저 받고 나서 실시간 연결 ----
    (async () => {
        try {
            await fetchMessages();
        } catch (error) {
            console.error('쪽지를 불러오지 못했습니다:', error);
            alert(`쪽지를 불러오지 못했습니다: ${error.message}`);
        }
        listEl.scrollTop = listEl.scrollHeight;
        connectStream();
        inputEl.focus();
    })();
}


document.addEventListener('DOMContentLoaded', () => {
    loadRoomList();   // dm.html 이면 동작, 아니면 조용히 빠짐
    initChatRoom();   // dm_room.html 이면 동작, 아니면 조용히 빠짐
});
