// static/js/history.js

// DOM 요소 캐싱
const historyListDiv = document.getElementById('historyList');
const noHistoryMessage = document.getElementById('noHistoryMessage');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const contentDetailModal = new bootstrap.Modal(document.getElementById('contentDetailModal')); // Bootstrap Modal 객체

// 모달 내 요소 캐싱
const modalTopic = document.getElementById('modalTopic');
const modalIndustry = document.getElementById('modalIndustry');
const modalContentType = document.getElementById('modalContentType');
const modalTone = document.getElementById('modalTone');
const modalLength = document.getElementById('modalLength');
const modalSeoKeywords = document.getElementById('modalSeoKeywords');
const modalEmailSubjectArea = document.getElementById('modalEmailSubjectArea');
const modalEmailSubject = document.getElementById('modalEmailSubject');
const modalGeneratedContent = document.getElementById('modalGeneratedContent');
const modalCopyBtn = document.getElementById('modalCopyBtn');
const modalLoadForEditBtn = document.getElementById('modalLoadForEditBtn'); // 모달 불러오기 버튼 캐싱 추가

// 검색 및 필터 요소 캐싱
const searchInput = document.getElementById('searchInput');
const filterContentType = document.getElementById('filterContentType');
const resetFiltersBtn = document.getElementById('resetFiltersBtn');


// 히스토리 데이터를 저장할 배열 (모달에서 사용)
let allHistoryItems = [];

// 기록을 불러와 렌더링하는 함수
async function fetchAndRenderHistory() {
    try {
        // flaskHistoryApiUrl 변수 사용 (content_routes.get_history_api)
        const response = await fetch(flaskHistoryApiUrl);
        if (!response.ok) {
            if (response.status === 401 || response.redirected) {
                historyListDiv.innerHTML = '<p class="text-info text-center">로그인하시면 나의 콘텐츠 기록을 볼 수 있습니다.</p>';
                noHistoryMessage.style.display = 'none';
                clearHistoryBtn.style.display = 'none';
                // 로그인 페이지로 리디렉션
                if (response.redirected) {
                    window.location.href = flaskLoginUrl;
                }
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        allHistoryItems = await response.json(); 

        renderFilteredHistory(); 
        
    } catch (error) {
        console.error('Error fetching history:', error);
        historyListDiv.innerHTML = '<p class="text-danger text-center">기록을 불러오는 데 실패했습니다.</p>';
        noHistoryMessage.style.display = 'none';
        clearHistoryBtn.style.display = 'none';
    }
}

// 필터링된 기록을 렌더링하는 함수
function renderFilteredHistory() {
    const searchText = searchInput.value.toLowerCase();
    const selectedType = filterContentType.value;

    const filteredItems = allHistoryItems.filter(item => {
        const matchesSearch = searchText === '' || 
                               item.topic.toLowerCase().includes(searchText) ||
                               item.industry.toLowerCase().includes(searchText) ||
                               item.content.toLowerCase().includes(searchText); 
        
        const matchesType = selectedType === '' || item.content_type === selectedType;

        return matchesSearch && matchesType;
    });

    historyListDiv.innerHTML = ''; 

    if (filteredItems.length === 0) {
        noHistoryMessage.style.display = 'block';
        noHistoryMessage.textContent = "검색 조건에 맞는 콘텐츠가 없습니다."; 
        clearHistoryBtn.style.display = 'none';
    } else {
        noHistoryMessage.style.display = 'none';
        clearHistoryBtn.style.display = 'block';

        filteredItems.forEach((item) => { 
            const historyItem = document.createElement('div');
            historyItem.className = 'list-group-item history-item d-flex justify-content-between align-items-center';
            historyItem.setAttribute('data-id', item.id); 

            // historyItem 자체에 클릭 이벤트 추가 (상세 보기)
            historyItem.onclick = () => { 
                showContentDetail(item.id);
            };

            const previewText = document.createElement('span');
            previewText.className = 'history-item-content';
            const date = new Date(item.timestamp);
            const formattedDate = date.toLocaleString('ko-KR', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit'
            });
            previewText.textContent = `${formattedDate} | ${item.topic} (${item.content_type}, ${item.industry})`;

            const actionsSpan = document.createElement('span');
            actionsSpan.className = 'history-item-actions';

            const deleteButton = document.createElement('span');
            deleteButton.className = 'history-item-delete';
            deleteButton.textContent = 'x';
            deleteButton.setAttribute('data-id', item.id);
            deleteButton.onclick = async (e) => {
                e.stopPropagation(); // 부모 요소 클릭 이벤트 방지
                if (confirm("이 기록을 삭제하시겠습니까?")) {
                    try {
                        // flaskDeleteContentUrlBase 변수 사용 (content_routes.delete_content)
                        const deleteResponse = await fetch(`${flaskDeleteContentUrlBase}${item.id}`, { 
                            method: 'DELETE'
                        });
                        if (!deleteResponse.ok) {
                            if (deleteResponse.status === 401 || deleteResponse.status === 404) {
                                alert('권한이 없거나 기록을 찾을 수 없습니다.');
                            }
                            throw new Error(`HTTP error! status: ${deleteResponse.status}`);
                        }
                        await fetchAndRenderHistory(); 
                        alert('콘텐츠가 성공적으로 삭제되었습니다.');
                    } catch (error) {
                        console.error('Error deleting history item:', error);
                        alert('기록 삭제 중 오류가 발생했습니다.');
                    }
                }
            };
            
            actionsSpan.appendChild(deleteButton); // 삭제 버튼은 유지
            historyItem.appendChild(previewText);
            historyItem.appendChild(actionsSpan);

            historyListDiv.appendChild(historyItem);
        });

        if (allHistoryItems.length > 0 && filteredItems.length === 0) {
            noHistoryMessage.style.display = 'block';
            noHistoryMessage.textContent = "검색 조건에 맞는 콘텐츠가 없습니다.";
        } else if (allHistoryItems.length === 0) {
            noHistoryMessage.style.display = 'block';
            noHistoryMessage.textContent = "아직 생성된 콘텐츠가 없습니다.";
        }
    }
}


// 콘텐츠 상세 보기 모달 표시 함수
function showContentDetail(contentId) {
    const item = allHistoryItems.find(i => i.id === contentId);
    if (!item) return;

    modalTopic.textContent = item.topic || 'N/A';
    modalIndustry.textContent = item.industry || 'N/A';
    modalContentType.textContent = item.content_type || 'N/A';
    modalTone.textContent = item.tone || 'N/A';
    modalLength.textContent = item.length || 'N/A';
    modalSeoKeywords.textContent = item.seo_keywords || 'N/A';

    if (item.content_type === '이메일 뉴스레터' && item.email_subject) {
        modalEmailSubjectArea.style.display = 'block';
        modalEmailSubject.textContent = item.email_subject;
    } else {
        modalEmailSubjectArea.style.display = 'none';
        modalEmailSubject.textContent = '';
    }

    modalGeneratedContent.innerHTML = marked.parse(item.content);
    
    // 모달의 "클립보드에 복사" 버튼
    modalCopyBtn.onclick = () => {
        navigator.clipboard.writeText(item.content)
            .then(() => alert('콘텐츠가 클립보드에 복사되었습니다!'))
            .catch(err => console.error('복사 실패:', err));
    };

    // 모달 내 "불러오기" 버튼 이벤트 리스너 설정
    modalLoadForEditBtn.onclick = () => { 
        localStorage.setItem('editContentData', JSON.stringify(item)); // 현재 item 저장
        window.location.href = flaskIndexUrl; // index 페이지로 이동
    };

    contentDetailModal.show();
}

// 모든 기록 삭제 함수
async function clearAllHistory() {
    if (confirm("정말로 모든 생성 기록을 삭제하시겠습니까? (현재 사용자의 기록만)")) {
        try {
            // '/content/history/clear_all' 라우트는 content_routes 블루프린트에 있습니다.
            // flaskDeleteContentUrlBase는 /content/history/ 로 끝나므로, 'clear_all'만 붙이면 됩니다.
            const response = await fetch(`${flaskDeleteContentUrlBase}clear_all`, { 
                method: 'DELETE'
            });
            if (!response.ok) {
                if (response.status === 401) {
                    alert('로그인 세션이 만료되었습니다. 다시 로그인해주세요.');
                    window.location.href = flaskLoginUrl; 
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            await fetchAndRenderHistory(); 
            alert('모든 기록이 삭제되었습니다.');
        } catch (error) {
            console.error('Error clearing all history:', error);
            alert('모든 기록 삭제 중 오류가 발생했습니다.');
        }
    }
}

// "기록 전체 삭제" 버튼 이벤트 리스너
clearHistoryBtn.addEventListener('click', clearAllHistory);


// 검색 및 필터 이벤트 리스너 추가
searchInput.addEventListener('input', renderFilteredHistory);
filterContentType.addEventListener('change', renderFilteredHistory);
resetFiltersBtn.addEventListener('click', () => {
    searchInput.value = '';
    filterContentType.value = '';
    renderFilteredHistory(); // 필터 초기화 후 다시 렌더링
});

// 페이지 로드 시 히스토리 로드 및 렌더링
window.addEventListener('load', fetchAndRenderHistory);