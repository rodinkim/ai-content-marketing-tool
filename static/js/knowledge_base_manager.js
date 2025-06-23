document.addEventListener('DOMContentLoaded', function() {
    // --- DOM 요소 캐싱 ---
    const addUrlForm = document.getElementById('addUrlForm');
    const urlInput = document.getElementById('urlInput');
    const industrySelect = document.getElementById('industrySelect');
    const addUrlBtn = document.getElementById('addUrlBtn');
    const addUrlSpinner = addUrlBtn.querySelector('.spinner-border');
    const mainWrapper = document.querySelector('.main-wrapper');

    const fileListDiv = document.getElementById('fileList');
    const noFilesMessage = document.getElementById('noFilesMessage');
    const fileListHeader = document.getElementById('fileListHeader');

    const userListDiv = document.getElementById('userList');
    const noUsersMessage = document.getElementById('noUsersMessage');

    let currentAdminTargetUser = null;

    // =========================================================
    // 유틸리티 함수: 메시지 표시
    // =========================================================
    function showMessage(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} mt-3`;
        alertDiv.textContent = message;
        const h2Element = mainWrapper.querySelector('h2.mb-4');
        if (h2Element) {
            h2Element.after(alertDiv);
        } else {
            mainWrapper.prepend(alertDiv);
        }
        setTimeout(() => alertDiv.remove(), 5000);
    }

    // =========================================================
    // 산업 목록을 불러와 드롭다운을 채우는 함수
    // =========================================================
    async function fetchAndPopulateIndustries() {
        if (!industrySelect) return;
        try {
            const response = await fetch(flaskIndustriesListUrl);
            if (!response.ok) throw new Error('Failed to fetch industries');
            
            const data = await response.json();
            const industries = data.industries || [];
            
            industries.forEach(industry => {
                const option = document.createElement('option');
                option.value = industry;
                // 한글이나 영문이나 첫 글자 대문자로 표시 (선택사항)
                option.textContent = industry.charAt(0).toUpperCase() + industry.slice(1);
                industrySelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching industries:', error);
            showMessage('산업 목록을 불러오는 데 실패했습니다.', 'danger');
            industrySelect.disabled = true;
        }
    }

    // =========================================================
    // 모든 파일 목록(산업별/사용자별)을 불러와 렌더링하는 함수
    // =========================================================
    async function fetchAndRenderAllFiles(targetUsername = null) {
        if (!fileListDiv) return;

        fileListDiv.innerHTML = '';
        if (noFilesMessage) noFilesMessage.style.display = 'none';
        
        if (fileListHeader) {
            fileListHeader.textContent = targetUsername ? `[사용자] ${targetUsername}의 파일 목록` : '전체 지식 베이스 (산업별/사용자별)';
        }

        try {
            const url = targetUsername ? `${flaskAdminTargetFilesUrlBase}${targetUsername}` : flaskKnowledgeBaseFilesUrl;
            const response = await fetch(url);
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            const files = data.files || [];

            if (files.length === 0) {
                if (noFilesMessage) noFilesMessage.style.display = 'block';
            } else {
                if (noFilesMessage) noFilesMessage.style.display = 'none';
                
                const groupedFiles = {};
                files.forEach(fileData => {
                    const groupName = fileData.s3_key.split('/')[0];
                    if (!groupedFiles[groupName]) groupedFiles[groupName] = [];
                    groupedFiles[groupName].push(fileData);
                });

                Object.keys(groupedFiles).sort().forEach(groupName => {
                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'kb-group mb-3';
                    groupDiv.innerHTML = `<h5 class="kb-group-header">${groupName}</h5>`;
                    
                    const listGroup = document.createElement('div');
                    listGroup.className = 'list-group';

                    groupedFiles[groupName].forEach(fileData => {
                        const fileItem = document.createElement('div');
                        fileItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                        
                        fileItem.innerHTML = `
                            <span class="file-item-name" title="${fileData.s3_key}">${fileData.display_name}</span>
                            <button type="button" class="btn btn-sm btn-outline-danger delete-file-btn" data-s3-key="${fileData.s3_key}">삭제</button>
                        `;
                        listGroup.appendChild(fileItem);
                    });
                    groupDiv.appendChild(listGroup);
                    fileListDiv.appendChild(groupDiv);
                });

                fileListDiv.querySelectorAll('.delete-file-btn').forEach(button => {
                    button.addEventListener('click', handleDeleteFile);
                });
            }
        } catch (error) {
            console.error('Error fetching knowledge base files:', error);
            showMessage('파일 목록을 불러오는 데 실패했습니다.', 'danger');
            fileListDiv.innerHTML = '<p class="text-danger text-center">파일 목록을 불러오는 데 실패했습니다.</p>';
        }
    }
    
    // =========================================================
    // 통합 파일 삭제 함수
    // =========================================================
    async function handleDeleteFile(event) {
        const s3Key = event.target.dataset.s3Key;

        if (confirm(`'${s3Key}' 파일을 정말로 삭제하시겠습니까?`)) {
            try {
                const response = await fetch(`${flaskDeleteFileUrlBase}${s3Key}`, {
                    method: 'DELETE'
                });

                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    fetchAndRenderAllFiles(isAdminUser ? currentAdminTargetUser : null);
                } else {
                    showMessage(result.error || '파일 삭제 실패', 'danger');
                }
            } catch (error) {
                console.error('Error deleting file:', error);
                showMessage('파일 삭제 중 오류가 발생했습니다.', 'danger');
            }
        }
    }

    // =========================================================
    // URL에서 지식 추가 폼 제출 핸들러
    // =========================================================
    addUrlForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const url = urlInput.value;
        const industry = industrySelect.value;

        if (!industry) {
            showMessage('산업 분야를 선택해주세요.', 'warning');
            return;
        }

        addUrlBtn.disabled = true;
        addUrlSpinner.style.display = 'inline-block';
        urlInput.disabled = true;
        industrySelect.disabled = true;

        try {
            const response = await fetch(flaskAddUrlUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, industry: industry })
            });
            const result = await response.json();
            if (response.ok) {
                showMessage(result.message, 'success');
                urlInput.value = '';
                fetchAndRenderAllFiles(isAdminUser ? currentAdminTargetUser : null);
                if (isAdminUser) fetchAndRenderUsers();
            } else {
                showMessage(result.error || 'URL에서 지식 추가 실패', 'danger');
            }
        } catch (error) {
            console.error('Error adding URL content:', error);
            showMessage('네트워크 오류: URL에서 지식 추가 중 오류가 발생했습니다.', 'danger');
        } finally {
            addUrlBtn.disabled = false;
            addUrlSpinner.style.display = 'none';
            urlInput.disabled = false;
            industrySelect.disabled = false;
        }
    });
    
    // =========================================================
    // 관리자 전용 함수
    // =========================================================
    async function fetchAndRenderUsers() {
        if (!userListDiv) return;
        userListDiv.innerHTML = ''; // Clear previous list
        try {
            const response = await fetch(flaskUsersListUrl);
            if (!response.ok) throw new Error('Failed to fetch users');
            const data = await response.json();
            const users = data.users || [];
            
            if (users.length > 0) {
                 users.forEach(username => {
                    const div = document.createElement('div');
                    div.className = 'user-item';
                    div.innerHTML = `
                        <span class="user-item-name">${username}</span>
                        <button class="btn btn-info btn-sm btn-select-user" data-username="${username}">파일 조회</button>
                    `;
                    userListDiv.appendChild(div);
                });
                userListDiv.querySelectorAll('.btn-select-user').forEach(button => {
                    button.addEventListener('click', handleSelectUser);
                });
            } else {
                 if (noUsersMessage) noUsersMessage.style.display = 'block';
            }
        } catch (error) {
            console.error('Error fetching users:', error);
            if (noUsersMessage) noUsersMessage.textContent = '사용자 목록 로드 실패';
        }
    }
    
    function handleSelectUser(event) {
        currentAdminTargetUser = event.target.dataset.username;
        fetchAndRenderAllFiles(currentAdminTargetUser);
    }

    // =========================================================
    // 페이지 로드 시 초기화 로직
    // =========================================================
    window.addEventListener('load', function() {
        fetchAndPopulateIndustries();

        if (isAdminUser) {
            fetchAndRenderUsers();
            fetchAndRenderAllFiles(null);
        } else {
            fetchAndRenderAllFiles();
        }
    });
});