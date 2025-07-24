document.addEventListener('DOMContentLoaded', function() {
    const historyList = document.getElementById('historyList');
    const noHistoryMessage = document.getElementById('noHistoryMessage');
    const searchInput = document.getElementById('searchInput');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    let allHistoryData = [];

    // 공통 알림 함수(utils.js의 showAlert 사용)
    function showAlert(message, type = 'success') {
        if (window.showAlert) {
            window.showAlert(message, type);
        } else {
            // fallback
            alert(message);
        }
    }

    function displayHistoryList(data) {
        historyList.innerHTML = '';
        noHistoryMessage.style.display = 'none';
        if (data.length === 0) {
            if (searchInput.value) {
                historyList.innerHTML = '<p class="text-muted text-center p-4">검색 결과가 없습니다.</p>';
            } else {
                noHistoryMessage.style.display = 'block';
            }
        } else {
            data.forEach(item => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                historyItem.setAttribute('data-id', item.id);
                let iconChar = '📄';
                if (item.content_type.includes('SNS')) iconChar = '📱';
                if (item.content_type.includes('이메일')) iconChar = '✉️';
                const date = new Date(item.timestamp);
                const formattedDate = `${date.getFullYear()}. ${String(date.getMonth() + 1).padStart(2, '0')}. ${String(date.getDate()).padStart(2, '0')}.`;
                historyItem.innerHTML = `
                    <div class="icon"><span>${iconChar}</span></div>
                    <div class="content">
                        <p class="topic">${item.topic}</p>
                        <p class="meta">${item.content_type} &middot; ${item.industry}</p>
                    </div>
                    <div class="timestamp">${formattedDate}</div>
                    <div class="actions">
                        <button class="delete-btn" title="삭제">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3-fill" viewBox="0 0 16 16"><path d="M11 1.5v1h3.5a.5.5 0 0 1 0 1h-.538l-.853 10.66A2 2 0 0 1 11.115 16h-6.23a2 2 0 0 1-1.994-1.84L2.038 3.5H1.5a.5.5 0 0 1 0-1H5v-1A1.5 1.5 0 0 1 6.5 0h3A1.5 1.5 0 0 1 11 1.5Zm-5 0v1h4v-1a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5ZM4.5 5.029l.5 8.5a.5.5 0 1 0 .998-.06l-.5-8.5a.5.5 0 1 0-.998.06Zm3.53-.528a.5.5 0 0 0-.499.438l-.5 8.5a.5.5 0 0 0 .998.058l.5-8.5a.5.5 0 0 0-.499-.496ZM9.5 5a.5.5 0 0 0-.5.5v8.5a.5.5 0 0 0 1 0V5.5a.5.5 0 0 0-.5-.5Z"/></svg>
                        </button>
                    </div>
                `;
                historyList.appendChild(historyItem);
            });
        }
    }

    function applyFilters() {
        const searchTerm = searchInput.value.toLowerCase();
        const filteredData = allHistoryData.filter(item => 
            item.topic.toLowerCase().includes(searchTerm) ||
            item.content.toLowerCase().includes(searchTerm)
        );
        displayHistoryList(filteredData);
    }

    // fetchHistory, deleteContent 등 fetchJson 사용
    async function fetchHistory() {
        try {
            if (window.fetchJson) {
                allHistoryData = await window.fetchJson(flaskHistoryApiUrl);
            } else {
                const response = await fetch(flaskHistoryApiUrl);
                allHistoryData = await response.json();
            }
            displayHistoryList(allHistoryData);
        } catch (error) {
            console.error('Fetch error:', error);
            historyList.innerHTML = '<p class="text-danger text-center">기록을 불러오는 데 실패했습니다.</p>';
        }
    }

    // 상세 콘텐츠 모달 관련 함수, 이벤트 리스너, 변수 등 모두 삭제
    // (populateModal, modalGeneratedContent, modalLoadForEditBtn, modalCopyBtn 등)

    historyList.addEventListener('click', function(e) {
        const itemElement = e.target.closest('.history-item');
        if (!itemElement) return;
        const contentId = itemElement.getAttribute('data-id');
        if (e.target.closest('.delete-btn')) {
            if (confirm('정말로 이 기록을 삭제하시겠습니까?')) {
                deleteContent(contentId);
            }
            return;
        }
        // 상세 페이지로 이동
        if (contentId) {
            window.location.href = `/history/${contentId}`;
        }
    });

    searchInput.addEventListener('input', applyFilters);
    resetFiltersBtn.addEventListener('click', () => {
        searchInput.value = '';
        applyFilters();
    });

    async function deleteContent(contentId) {
        try {
            let responseData;
            if (window.fetchJson) {
                responseData = await window.fetchJson(`${flaskDeleteContentUrlBase}${contentId}`, { method: 'DELETE' });
                showAlert(responseData.message || '콘텐츠가 성공적으로 삭제되었습니다.');
                fetchHistory();
            } else {
                const response = await fetch(`${flaskDeleteContentUrlBase}${contentId}`, { method: 'DELETE' });
                responseData = await response.json();
                if (response.ok) {
                    showAlert(responseData.message || '콘텐츠가 성공적으로 삭제되었습니다.');
                    fetchHistory();
                } else {
                    showAlert(responseData.error || '삭제에 실패했습니다.', 'danger');
                }
            }
        } catch (error) {
            console.error('Delete error:', error);
            showAlert('삭제 중 오류가 발생했습니다.', 'danger');
        }
    }

    // document.getElementById('modalCopyBtn').addEventListener('click', function() { // 삭제됨
    //     const content = document.getElementById('modalGeneratedContent').innerText;
    //     navigator.clipboard.writeText(content).then(() => {
    //         this.textContent = '복사 완료!';
    //         setTimeout(() => { this.textContent = '클립보드에 복사'; }, 2000);
    //     }).catch(err => console.error('Copy failed:', err));
    // }); // 삭제됨

    // document.getElementById('modalLoadForEditBtn').addEventListener('click', function() { // 삭제됨
    //     const contentId = this.getAttribute('data-id');
    //     const itemToEdit = allHistoryData.find(item => item.id == contentId);
    //     if (itemToEdit) {
    //         localStorage.setItem('editContentData', JSON.stringify(itemToEdit));
    //         window.location.href = flaskIndexUrl;
    //     }
    // }); // 삭제됨

    fetchHistory();
});