document.getElementById("upload-btn").addEventListener("click", async function() {
    const fileInput = document.getElementById("csv-file");
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/upload-csv", {
            method: "POST",
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            const tableHeader = document.getElementById("table-header");
            const tableBody = document.getElementById("table-body");

            // 테이블 헤더 설정
            tableHeader.innerHTML = "";  // 이전 내용 지우기
            if (data.preview.length > 0) {
                Object.keys(data.preview[0]).forEach(key => {
                    const th = document.createElement("th");
                    th.textContent = key;
                    tableHeader.appendChild(th);
                });
            }

            // 테이블 본문 설정
            tableBody.innerHTML = "";  // 이전 내용 지우기
            data.preview.forEach(row => {
                const tr = document.createElement("tr");
                Object.values(row).forEach(value => {
                    const td = document.createElement("td");
                    td.textContent = value === '' ? 'N/A' : value; // 빈 값을 'N/A'로 표시
                    tr.appendChild(td);
                });
                tableBody.appendChild(tr);
            });

            // Upload 버튼 숨기기
            document.getElementById("upload-btn").style.display = "none";
            // Train 버튼 보이기
            document.getElementById("train-btn").style.display = "inline-block";
        } else {
            alert("Failed to upload the CSV file.");
        }
    } else {
        alert("Please select a CSV file.");
    }
});

document.getElementById("train-btn").addEventListener("click", function() {
    const fileInput = document.getElementById("csv-file");
    const attackType = document.getElementById("attack-type").value;

    const fileName = fileInput.files[0].name; // 업로드한 파일 이름

    // 웹 소켓 연결
    const socket = new WebSocket(`ws://${window.location.host}/ws/train`);

    socket.onopen = function() {
        // 웹 소켓이 열리면 파일 이름과 공격 타입을 전송
        socket.send(JSON.stringify({ fileName, attackType }));
    };

    socket.onmessage = function(event) {
        const message = event.data;
        const logBody = document.getElementById("log-body");

        // 현재 시간 가져오기
        const currentTime = new Date().toLocaleTimeString();

        // 새로운 로그 행 생성
        const newRow = document.createElement('tr');
        const timeCell = document.createElement('td');
        const logCell = document.createElement('td');

        timeCell.textContent = currentTime; // 시간 추가
        logCell.textContent = message; // 로그 추가

        newRow.appendChild(timeCell);
        newRow.appendChild(logCell);
        logBody.appendChild(newRow);
        // 학습 현황을 trainer-output에 추가
        // const outputDiv = document.getElementById("trainer-output");
        // outputDiv.innerHTML += `<p>${message}</p>`;
    };

    socket.onclose = function() {
        console.log("WebSocket connection closed");
    };
});