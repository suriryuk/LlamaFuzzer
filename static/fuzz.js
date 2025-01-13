// 모달 기능
const modal = document.getElementById("nuclei-modal");
const btn = document.getElementById("select-nuclei-btn");
const closeBtn = document.getElementsByClassName("close")[0];
const confirmBtn = document.getElementById("confirm-nuclei-btn");
const attackBtn = document.getElementById("attack-btn");
const selectedOptionsBody = document.getElementById("selected-options-body");

function ansiToHtml(text) {
    const ansiColorCodes = {
        '30': 'color: black;',
        '31': 'color: red;',
        '32': 'color: green;',
        '33': 'color: yellow;',
        '34': 'color: blue;',
        '35': 'color: magenta;',
        '36': 'color: cyan;',
        '37': 'color: white;',
        '0': 'color: inherit;', // 기본 색상
    };

    let html = '';
    let currentStyle = '';

    // ANSI 코드 변환
    text.split('\x1b').forEach((part, index) => {
        // 첫 번째 부분은 그냥 추가
        if (index === 0) {
            html += part;
            return;
        }

        const parts = part.split('m');
        const code = parts[0];
        const content = parts.slice(1).join('m');

        // 색깔 코드가 존재할 경우
        if (code in ansiColorCodes) {
            // 현재 스타일이 있으면 종료 태그 추가
            if (currentStyle) {
                html += `</span>`;
            }

            // 새로운 스타일 적용
            currentStyle = ansiColorCodes[code];
            html += `<span style="${currentStyle}">`;
        }

        html += content; // 내용 추가
    });

    // 마지막 스타일 마감
    if (currentStyle) {
        html += `</span>`;
    }

    return html;
}

function showInfo(option) {
    // 숨겨진 JSON 데이터 가져오기
    const hiddenData = JSON.parse(document.getElementById("hidden-data").textContent);
    const info = hiddenData;

    // 옵션에 대한 설명 가져오기
    let optionInfo = "";
    for (const category in info) {
        if (option in info[category]) {
            optionInfo = info[category][option][0]; // 설명을 가져옴
            break;
        }
    }

    // 모달 내용 업데이트
    document.getElementById("info-title").innerText = option + " 정보";
    document.getElementById("info-description").innerText = optionInfo;

    // 모달 열기
    document.getElementById("info-modal").style.display = "block";
}

function closeInfoModal() {
    document.getElementById("info-modal").style.display = "none";
}

// AI 사용 관련 멀티모달 조작
function showAttackTypeModal() {
    const aiOption = document.getElementById("ai-option");
    const attackTypeModal = document.getElementById("attack-type-modal");

    if (aiOption.checked) {
        attackTypeModal.style.display = "block"; // 모달 열기
    } else {
        document.getElementById("selected-value").textContent = ""; // 선택한 값 초기화
        closeAttackTypeModal(); // 체크 해제 시 모달 닫기
    }
}

function closeAttackTypeModal() {
    document.getElementById("attack-type-modal").style.display = "none"; // 모달 닫기
    // document.getElementById("ai-option").checked = false; // 체크박스 해제
    // document.getElementById("selected-value").textContent = ""; 
}

function confirmAttackType() {
    closeAttackTypeModal(); // 모달 닫기
    // 추가적으로 선택한 공격 타입을 처리할 수 있습니다.
    const selectedValue = document.getElementById("attack-type").value;
    const selectedValueDisplay = document.getElementById("selected-value");
    // 여기서 선택한 값을 사용하여 필요한 작업을 수행할 수 있습니다.
    console.log("선택한 공격 타입:", selectedValue); // 선택한 공격 타입을 콘솔에 출력

    // 선택한 값 가져오기
    selectedValueDisplay.textContent = selectedValue; // 체크박스 옆에 선택한 값 출력
}

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modal = document.getElementById("info-modal");
    if (event.target == modal) {
        closeInfoModal();
    }
}

// 모달 열기
btn.onclick = function() {
    modal.style.display = "block";
}

// 모달 닫기
closeBtn.onclick = function() {
    modal.style.display = "none";
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

// Confirm 버튼 클릭 이벤트
confirmBtn.onclick = function() {
    const selectedOptions = Array.from(document.querySelectorAll('.nuclei-option')).filter(option => option.checked).map((option) => {
        const valueInput = option.closest('.nuclei-option-group').querySelector('.nuclei-value');
        return { option: option.value, value: valueInput ? valueInput.value : '' };
    });

    // 선택한 옵션을 테이블에 추가
    selectedOptionsBody.innerHTML = ''; // 기존 내용 제거
    selectedOptions.forEach(({ option, value }) => {
        const row = document.createElement('tr');
        const optionCell = document.createElement('td');
        const valueCell = document.createElement('td');
        optionCell.textContent = option;
        valueCell.textContent = value;
        row.appendChild(optionCell);
        row.appendChild(valueCell);
        selectedOptionsBody.appendChild(row);
    });
    modal.style.display = "none"; // 모달 닫기
}

// Start Fuzzing 버튼 클릭 이벤트
document.addEventListener("DOMContentLoaded", function() {
    const attackBtn = document.getElementById("attack-btn");

    attackBtn.onclick = async function() {
        const selectedOptions = Array.from(document.querySelectorAll('.nuclei-option')).filter(option => option.checked).map((option) => {
            const valueInput = option.closest('.nuclei-option-group').querySelector('.nuclei-value');
            return { option: option.value, value: valueInput ? valueInput.value : '' };
        });

        const targetUrl = document.getElementById("target-url").value; // 타겟 URL 가져오기
        const aiOption = document.getElementById("ai-option").checked; // AI 사용 여부 체크박스 값 가져오기
        const attack = document.getElementById("selected-value").textContent; // 선택된 공격 타입 가져오기

        const requestData = {
            target_url: targetUrl,
            selected_options: selectedOptions,
            ai_option: aiOption, // AI 사용 여부 추가
            attack: attack
        };
        console.log(requestData);

        // WebSocket 연결
        const socket = new WebSocket(`ws://${window.location.host}/ws/fuzz`);
        let outputContent = '';

        socket.onopen = function() {
            // Nuclei 실행 요청 전송
            socket.send(JSON.stringify(requestData));
        };

        socket.onmessage = function(event) {
            // right-panel 클래스를 가진 요소 선택
            const rightPanels = document.getElementsByClassName("right-panel");
            if (rightPanels.length > 0) {
                const outputArea = document.getElementById("output-area"); // output-area 선택
        
                // rightPanel이 실제 DOM 요소인지 확인
                console.log(rightPanels[0]);
        
                if (outputArea instanceof HTMLElement) {
                    // const newLine = document.createElement("div"); // <div> 태그 사용
                    // newLine.textContent = ansiToHtml(event.data); // WebSocket으로 받은 데이터
                    outputContent += ansiToHtml(event.data) + '<br>';
                    console.log(outputContent);
                    // outputArea.appendChild(newLine); // 새로운 줄 추가
                    outputArea.innerHTML = outputContent;
        
                    // 스크롤을 맨 아래로 내리기
                    outputArea.scrollTop = outputArea.scrollHeight;
                } else {
                    console.error("outputArea는 DOM 요소가 아닙니다.");
                }
            } else {
                console.error("right-panel 요소를 찾을 수 없습니다.");
            }
        };

        socket.onclose = function() {
            console.log("WebSocket closed");
        };

        socket.onerror = function(error) {
            console.error("WebSocket error:", error);
        };
    }
});
