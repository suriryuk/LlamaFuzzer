// WebSocket 연결 및 메시지 처리
const socket = new WebSocket(`ws://${window.location.host}/ws/chat`);

let messageHistory = []; // 입력된 메시지를 저장할 배열
let historyIndex = -1; // 현재 히스토리 인덱스

socket.onopen = () => {
    console.log("WebSocket 연결됨");
};

socket.onmessage = (event) => {
    const message = event.data;
    const messagesContainer = document.getElementById("messages");

    // 봇 응답을 표시할 요소 생성
    const botMessageElement = document.createElement("div");
    botMessageElement.className = "message bot-message";
    messagesContainer.appendChild(botMessageElement);

    // 문장 구분자에 따라 개행 추가 (불필요한 개행 방지)
    const formattedResponse = message
        .replace(/([.!?])\s+/g, "$1\n") // 문장 끝에 개행 추가 (1개로 제한)
        .trim(); // 불필요한 공백 제거

    // 코드 블록의 언어를 추출하고 HTML로 변환
    const codeBlockRegex = /```(\w+)\n([\s\S]*?)```/g;
    const htmlResponse = formattedResponse.replace(codeBlockRegex, (match, lang, code) => {
        // HTML 이스케이프 처리
        const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        
        return `<pre><code class="${lang}">${escapedCode.trim()}</code></pre>`;
    });

    botMessageElement.innerHTML = marked.parse(htmlResponse);

    // 문법 강조하기
    hljs.highlightAll();

    messagesContainer.scrollTop = messagesContainer.scrollHeight; // 매 타이핑 후 스크롤 이동
};

// 사용자 메시지 전송 및 히스토리 관리
document.getElementById("sendButton").onclick = () => {
    const userInput = document.getElementById("userInput").value;

    // 입력된 메시지를 히스토리에 추가
    if (userInput) {
        messageHistory.push(userInput);
        historyIndex = messageHistory.length; // 새로운 메시지 추가 후 인덱스 초기화

        // 사용자 메시지를 표시
        const userMessageElement = document.createElement("div");
        userMessageElement.className = "message user-message";
        userMessageElement.textContent = userInput;
        document.getElementById("messages").appendChild(userMessageElement);
        
        console.log(userInput);

        socket.send(userInput);
        document.getElementById("userInput").value = ""; // 입력창 초기화

        // 스크롤을 항상 아래로 이동
        const messagesContainer = document.getElementById("messages");
        messagesContainer.scrollTop = messagesContainer.scrollHeight; // 스크롤 이동
    }
};

// 엔터키로 메시지 전송
document.getElementById("userInput").addEventListener("keypress", function(event) {
    if (event.key === 'Enter') {
        document.getElementById("sendButton").click();
    }
});

// 화살표 키로 히스토리 탐색
document.getElementById("userInput").addEventListener("keydown", function(event) {
    if (event.key === 'ArrowUp') {
        // 이전 메시지로 이동
        if (historyIndex > 0) {
            historyIndex--;
            document.getElementById("userInput").value = messageHistory[historyIndex];
        }
        event.preventDefault(); // 기본 동작 방지
    } else if (event.key === 'ArrowDown') {
        // 다음 메시지로 이동
        if (historyIndex < messageHistory.length - 1) {
            historyIndex++;
            document.getElementById("userInput").value = messageHistory[historyIndex];
        } else {
            historyIndex = messageHistory.length; // 히스토리 초기화
            document.getElementById("userInput").value = ''; // 입력창 비우기
        }
        event.preventDefault(); // 기본 동작 방지
    }
});

// 페이지 로드 시 메시지 로드
window.onload = loadMessages;
