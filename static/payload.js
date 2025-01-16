function sendRequest() {
    const attack = document.getElementById("attack").value;
    const requestData = { attack: attack };
    const loader = document.getElementById("loader");
    const responseElement = document.getElementById("response");
    
    // 로딩 아이콘 표시
    loader.style.display = "inline-block";
    responseElement.style.display = "none"; // 응답 숨김
    document.querySelector("h2").style.display = "none"; // 제목 숨김

    // WebSocket 연결 생성
    const socket = new WebSocket(`ws://${window.location.host}/ws/payload`);

    socket.onopen = function() {
        console.log("Connected to WebSocket server");
        socket.send(JSON.stringify(requestData));
        console.log("Sent:", requestData);
    };

    socket.onmessage = function(event) {
        const result = JSON.parse(event.data); // JSON 문자열 파싱
        console.log("Received result:", result); // 응답 확인

        // 로딩 아이콘 숨김
        loader.style.display = "none";

        // 제목 및 응답 표시
        document.querySelector("h2").style.display = "block"; // 제목 보이기
        responseElement.style.display = "block"; // 응답 div 보이기
        responseElement.innerHTML = `<a href="/downloads/payloads.yaml" target="_blank">Download Payload Templates.</a>`;
    };

    socket.onclose = function() {
        console.log("Disconnected from WebSocket server");
    };

    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
        loader.style.display = "none"; // 로딩 아이콘 숨김
    };
}

window.onload = function() {
    document.getElementById("sendButton").onclick = sendRequest;
};