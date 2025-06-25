document.addEventListener('DOMContentLoaded', function() {
    const historyList = document.getElementById('historyList');
    const noHistoryMessage = document.getElementById('noHistoryMessage');
    const contentDetailModal = new bootstrap.Modal(document.getElementById('contentDetailModal'));
    const searchInput = document.getElementById('searchInput');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    let allHistoryData = [];

    function showDynamicAlert(message, category = 'success') {
        const alertContainer = document.querySelector('.page-header');
        if (!alertContainer) return;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category} alert-dismissible fade show mt-3`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        alertContainer.after(alertDiv);

        setTimeout(() => bootstrap.Alert.getOrCreateInstance(alertDiv)?.close(), 5000);
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

    async function fetchHistory() {
        try {
            const response = await fetch(flaskHistoryApiUrl);
            if (!response.ok) throw new Error('Network response was not ok');
            allHistoryData = await response.json();
            displayHistoryList(allHistoryData);
        } catch (error) {
            console.error('Fetch error:', error);
            historyList.innerHTML = '<p class="text-danger text-center">기록을 불러오는 데 실패했습니다.</p>';
        }
    }
    
    function populateModal(item) {
        document.getElementById('modalTopic').textContent = item.topic;
        document.getElementById('modalIndustry').textContent = item.industry;
        document.getElementById('modalContentType').textContent = item.content_type;
        document.getElementById('modalTone').textContent = item.tone;
        document.getElementById('modalLength').textContent = item.length_option;
        document.getElementById('modalSeoKeywords').textContent = item.seo_keywords || '없음';
        
        const emailSubjectArea = document.getElementById('modalEmailSubjectArea');
        if (item.content_type === '이메일 뉴스레터' && item.email_subject) {
            document.getElementById('modalEmailSubject').textContent = item.email_subject;
            emailSubjectArea.style.display = 'block';
        } else {
            emailSubjectArea.style.display = 'none';
        }
        document.getElementById('modalGeneratedContent').innerHTML = marked.parse(item.content);
        document.getElementById('modalLoadForEditBtn').setAttribute('data-id', item.id);
    }

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

        const itemData = allHistoryData.find(item => item.id == contentId);
        if (itemData) {
            populateModal(itemData);
            contentDetailModal.show();
        }
    });

    searchInput.addEventListener('input', applyFilters);
    resetFiltersBtn.addEventListener('click', () => {
        searchInput.value = '';
        applyFilters();
    });

    async function deleteContent(contentId) {
        try {
            const response = await fetch(`${flaskDeleteContentUrlBase}${contentId}`, { method: 'DELETE' });
            const responseData = await response.json();
            if (response.ok) {
                showDynamicAlert(responseData.message || '콘텐츠가 성공적으로 삭제되었습니다.');
                fetchHistory();
            } else {
                showDynamicAlert(responseData.error || '삭제에 실패했습니다.', 'danger');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showDynamicAlert('삭제 중 오류가 발생했습니다.', 'danger');
        }
    }
    
    document.getElementById('modalCopyBtn').addEventListener('click', function() {
        const content = document.getElementById('modalGeneratedContent').innerText;
        navigator.clipboard.writeText(content).then(() => {
            this.textContent = '복사 완료!';
            setTimeout(() => { this.textContent = '클립보드에 복사'; }, 2000);
        }).catch(err => console.error('Copy failed:', err));
    });

    document.getElementById('modalLoadForEditBtn').addEventListener('click', function() {
        const contentId = this.getAttribute('data-id');
        const itemToEdit = allHistoryData.find(item => item.id == contentId);
        if (itemToEdit) {
            localStorage.setItem('editContentData', JSON.stringify(itemToEdit));
            window.location.href = flaskIndexUrl;
        }
    });

    fetchHistory();
});