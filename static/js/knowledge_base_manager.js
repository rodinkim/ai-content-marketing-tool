// static/js/knowledge_base_manager.js

document.addEventListener('DOMContentLoaded', function() {
    // --- DOM 요소 캐싱 ---
    // 공통 요소
    const addUrlForm = document.getElementById('addUrlForm');
    const urlInput = document.getElementById('urlInput');
    const addUrlBtn = document.getElementById('addUrlBtn');
    const addUrlSpinner = addUrlBtn.querySelector('.spinner-border');
    const mainWrapper = document.querySelector('.main-wrapper');

    // 일반 사용자용 요소 (isAdminUser가 false일 때만 존재)
    const fileListDivUser = document.getElementById('fileList');
    const noFilesMessageUser = document.getElementById('noFilesMessage');
    const clearAllKbBtnUser = document.getElementById('clearAllKbBtn');

    // 관리자용 요소 (isAdminUser가 true일 때만 존재)
    const userListDiv = document.getElementById('userList');
    const noUsersMessage = document.getElementById('noUsersMessage');
    const adminFileListDiv = document.getElementById('adminFileList');
    const noAdminFilesMessage = document.getElementById('noAdminFilesMessage');
    const adminFileListHeader = document.getElementById('adminFileListHeader');
    const adminClearUserKbBtn = document.getElementById('adminClearUserKbBtn');

    let currentAdminTargetUser = null; // 관리자가 현재 보고 있는 사용자의 username

    // =========================================================
    // 유틸리티 함수: 메시지 표시 (화면 상단에 알림 표시)
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
    // 일반 사용자: 자신의 파일 목록을 불러와 렌더링하는 함수
    // =========================================================
    async function fetchAndRenderUserFiles() {
        if (!fileListDivUser) return;

        fileListDivUser.innerHTML = '';
        noFilesMessageUser.style.display = 'none';
        clearAllKbBtnUser.style.display = 'none';

        try {
            const response = await fetch(flaskKnowledgeBaseFilesUrl);
            
            if (!response.ok) {
                if (response.status === 401 || response.redirected) {
                    fileListDivUser.innerHTML = '<p class="text-info text-center">로그인하시면 지식 베이스를 관리할 수 있습니다.</p>';
                    if (response.redirected) {
                        window.location.href = flaskAuthLoginUrl;
                    }
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            // files는 이제 [{display_name: "제목.txt", s3_key: "username/제목_URLHASH.txt"}, ...] 형태
            const files = data.files || []; 

            if (files.length === 0) {
                noFilesMessageUser.style.display = 'block';
            } else {
                noFilesMessageUser.style.display = 'none';
                clearAllKbBtnUser.style.display = 'block';
                files.forEach(fileData => { // fileData는 {display_name, s3_key} 객체
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <span class="file-item-name">${fileData.display_name}</span>
                        <div class="file-item-actions">
                            <button type="button" class="btn btn-sm btn-danger delete-file-btn" data-filename="${fileData.s3_key}">삭제</button>
                        </div>
                    `;
                    fileListDivUser.appendChild(fileItem);
                });
                fileListDivUser.querySelectorAll('.delete-file-btn').forEach(button => {
                    button.addEventListener('click', handleDeleteUserFile);
                });
            }
        } catch (error) {
            console.error('Error fetching knowledge base files (User):', error);
            showMessage('네트워크 오류: 지식 베이스 파일을 불러오는 데 실패했습니다.', 'danger');
            if (fileListDivUser) fileListDivUser.innerHTML = '<p class="text-danger text-center">지식 베이스 파일을 불러오는 데 실패했습니다.</p>';
            if (noFilesMessageUser) noFilesMessageUser.style.display = 'none';
            if (clearAllKbBtnUser) clearAllKbBtnUser.style.display = 'none';
        }
    }

    // =========================================================
    // 일반 사용자: 파일 삭제 함수
    // =========================================================
    async function handleDeleteUserFile(event) {
        const filename = event.target.dataset.filename; // 실제 S3 키 (예: "username/제목_URLHASH.txt")
        if (confirm(`'${filename}' 파일을 정말로 삭제하시겠습니까?`)) {
            try {
                // flaskDeleteFileUrlBase는 "/knowledge_base/delete/" 로 끝납니다.
                // 백엔드 라우트는 /delete/<path:filename> 이므로 S3 키를 그대로 전달
                const response = await fetch(`${flaskDeleteFileUrlBase}${filename}`, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    fetchAndRenderUserFiles();
                } else {
                    showMessage(result.error || `파일 삭제 실패: ${response.statusText}`, 'danger');
                }
            } catch (error) {
                console.error('Error deleting file (User):', error);
                showMessage('파일 삭제 중 오류가 발생했습니다.', 'danger');
            }
        }
    }

    // =========================================================
    // 일반 사용자: 모든 지식 베이스 파일 삭제 함수
    // =========================================================
    if (clearAllKbBtnUser) {
        clearAllKbBtnUser.addEventListener('click', async function() {
            if (confirm("정말로 나의 모든 지식 베이스 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
                try {
                    const response = await fetch(flaskClearAllKbUrl, {
                        method: 'DELETE'
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showMessage(result.message, 'success');
                        fetchAndRenderUserFiles();
                    } else {
                        showMessage(result.error || `모든 파일 삭제 실패: ${response.statusText}`, 'danger');
                    }
                } catch (error) {
                    console.error('Error clearing all KB files (User):', error);
                    showMessage('모든 지식 베이스 파일 삭제 중 오류가 발생했습니다.', 'danger');
                }
            }
        });
    }

    // =========================================================
    // 관리자: 모든 사용자 목록을 불러와 렌더링하는 함수
    // =========================================================
    async function fetchAndRenderUsers() {
        if (!userListDiv) return;

        userListDiv.innerHTML = '';
        noUsersMessage.style.display = 'none';
        adminFileListDiv.innerHTML = '<p class="text-muted text-center">사용자를 선택하여 파일을 확인하세요.</p>';
        noAdminFilesMessage.style.display = 'block';
        adminFileListHeader.textContent = '선택된 사용자의 파일';
        adminClearUserKbBtn.style.display = 'none';


        try {
            const response = await fetch(flaskUsersListUrl);
            if (!response.ok) {
                const errorData = await response.json();
                showMessage(errorData.error || `사용자 목록을 불러오는 데 실패했습니다: ${response.statusText}`, 'danger');
                noUsersMessage.style.display = 'block';
                return;
            }
            const data = await response.json();
            const users = data.users || [];

            if (users.length === 0) {
                noUsersMessage.style.display = 'block';
            } else {
                noUsersMessage.style.display = 'none';
                users.forEach(username => {
                    const div = document.createElement('div');
                    div.className = 'user-item';
                    div.innerHTML = `
                        <span class="user-item-name">${username}</span>
                        <button class="btn btn-info btn-sm btn-select-user" data-username="${username}">조회</button>
                    `;
                    userListDiv.appendChild(div);
                });
                userListDiv.querySelectorAll('.btn-select-user').forEach(button => {
                    button.addEventListener('click', handleSelectUser);
                });
            }
        } catch (error) {
            console.error('Error fetching users (Admin):', error);
            showMessage('네트워크 오류: 사용자 목록을 불러올 수 없습니다.', 'danger');
            noUsersMessage.style.display = 'block';
        }
    }

    // =========================================================
    // 관리자: 특정 사용자의 파일 목록을 불러와 렌더링하는 함수 (혹은 모든 파일 통합 조회)
    // =========================================================
    async function fetchAndRenderAdminTargetFiles(username = null) { // username이 null이면 통합 조회
        if (!adminFileListDiv) return;

        currentAdminTargetUser = username;
        adminFileListDiv.innerHTML = '';
        noAdminFilesMessage.style.display = 'none';
        adminClearUserKbBtn.style.display = 'none';
        adminFileListHeader.textContent = username ? `${username}의 파일 목록` : '모든 사용자 파일 (통합)';

        try {
            let url;
            if (username) {
                // 특정 사용자 파일 조회: /knowledge_base/files/username
                url = `${flaskAdminTargetFilesUrlBase}${username}`;
            } else {
                // 모든 사용자 파일 통합 조회: /knowledge_base/files
                url = flaskKnowledgeBaseFilesUrl;
            }
            
            const response = await fetch(url);

            if (!response.ok) {
                const errorData = await response.json();
                showMessage(errorData.error || `파일을 불러오는 데 실패했습니다: ${response.statusText}`, 'danger');
                noAdminFilesMessage.style.display = 'block';
                return;
            }

            const data = await response.json();
            // files는 이제 [{display_name: "제목.txt", s3_key: "username/제목_URLHASH.txt"}, ...] 형태
            const files = data.files || [];

            if (files.length === 0) {
                noAdminFilesMessage.style.display = 'block';
            } else {
                noAdminFilesMessage.style.display = 'none';
                // 관리자 통합 조회 시에만 '모든 파일 삭제' 버튼 활성화 (특정 유저 삭제는 해당 유저 클릭 후)
                if (username) { // 특정 사용자 조회 시에는 해당 사용자 모든 파일 삭제 버튼
                    adminClearUserKbBtn.style.display = 'block';
                } else { // 통합 조회 시에는 버튼을 숨기거나, 관리자 전체 삭제 기능으로 연결
                    // adminClearUserKbBtn.style.display = 'block'; // <- 모든 사용자 파일 삭제 버튼 필요시 활성화
                }
                
                files.forEach(fileData => { // fileData는 {display_name, s3_key} 객체
                    const div = document.createElement('div');
                    div.className = 'file-item';
                    
                    // 관리자 통합 조회시에는 '사용자명/제목.txt' 형태로 보여줄 수 있습니다.
                    let displayName = fileData.display_name;
                    if (!username && fileData.s3_key && fileData.s3_key.includes('/')) {
                        // 통합 조회이면서 S3 키에 사용자명이 포함된 경우
                        const parts = fileData.s3_key.split('/');
                        const userFolder = parts[0];
                        displayName = `${userFolder}/${fileData.display_name}`;
                    }

                    div.innerHTML = `
                        <span class="file-item-name">${displayName}</span>
                        <div class="file-item-actions">
                            <button type="button" class="btn btn-sm btn-danger btn-admin-delete-file" data-filename="${fileData.s3_key}" data-username="${fileData.s3_key.split('/')[0]}">삭제</button>
                        </div>
                    `;
                    adminFileListDiv.appendChild(div);
                });
                adminFileListDiv.querySelectorAll('.btn-admin-delete-file').forEach(button => {
                    button.addEventListener('click', handleAdminDeleteFile);
                });
            }
        } catch (error) {
            console.error(`Error fetching files for user ${username || 'all users'} (Admin):`, error);
            showMessage(`네트워크 오류: 파일을 불러올 수 없습니다.`, 'danger');
            noAdminFilesMessage.style.display = 'block';
        }
    }

    // =========================================================
    // 관리자: 사용자 선택 핸들러
    // =========================================================
    function handleSelectUser(event) {
        const username = event.target.dataset.username;
        fetchAndRenderAdminTargetFiles(username);
    }

    // =========================================================
    // 관리자: 특정 사용자의 파일 삭제 함수
    // =========================================================
    async function handleAdminDeleteFile(event) {
        const filename = event.target.dataset.filename; // 실제 S3 키 (예: "username/제목_URLHASH.txt")
        const targetUsername = event.target.dataset.username; // 실제 S3 키에서 추출한 사용자명

        if (confirm(`관리자: 사용자 '${targetUsername}'의 파일 '${filename.split('/').pop()}'을 정말로 삭제하시겠습니까?`)) {
            try {
                // Flask 라우트가 /delete/<string:target_username>/<path:filename> 이므로 정확히 조합
                const deleteUrl = `${flaskAdminTargetDeleteUrlBase}${targetUsername}/${filename.split('/').pop()}`; // filename은 순수 파일명만

                const response = await fetch(deleteUrl, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    // 현재 보고 있는 뷰에 따라 파일 목록 새로고침
                    if (currentAdminTargetUser) { // 특정 유저를 보고 있으면 해당 유저 파일 새로고침
                        fetchAndRenderAdminTargetFiles(currentAdminTargetUser);
                    } else { // 통합 목록을 보고 있었으면 통합 목록 새로고침
                        fetchAndRenderAdminTargetFiles(null);
                    }
                } else {
                    showMessage(result.error || `파일 삭제 실패: ${response.statusText}`, 'danger');
                }
            } catch (error) {
                console.error('Error deleting file by admin:', error);
                showMessage('파일 삭제 중 오류가 발생했습니다.', 'danger');
            }
        }
    }

    // =========================================================
    // 관리자: 선택된 사용자의 모든 파일 삭제 함수
    // =========================================================
    if (adminClearUserKbBtn) {
        adminClearUserKbBtn.addEventListener('click', async function() {
            if (!currentAdminTargetUser) {
                showMessage("파일을 삭제할 사용자를 먼저 선택해주세요.", "warning");
                return;
            }
            if (confirm(`관리자: 사용자 '${currentAdminTargetUser}'의 모든 지식 베이스 파일을 정말로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
                try {
                    // Flask 라우트가 /clear_all_files/<string:target_username> 형태이므로 조합
                    const clearUrl = `${flaskAdminTargetClearAllUrlBase}${currentAdminTargetUser}`;

                    const response = await fetch(clearUrl, {
                        method: 'DELETE'
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showMessage(result.message, 'success');
                        fetchAndRenderAdminTargetFiles(currentAdminTargetUser); // 파일 목록 새로고침
                    } else {
                        showMessage(result.error || `모든 파일 삭제 실패: ${response.statusText}`, 'danger');
                    }
                } catch (error) {
                    console.error('Error clearing all KB files by admin:', error);
                    showMessage('모든 지식 베이스 파일 삭제 중 오류가 발생했습니다.', 'danger');
                }
            }
        });
    }

    // =========================================================
    // 공통: URL에서 지식 추가 폼 제출 핸들러
    // =========================================================
    addUrlForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        addUrlBtn.disabled = true;
        addUrlSpinner.style.display = 'inline-block';
        urlInput.disabled = true;

        const url = urlInput.value;

        try {
            const response = await fetch(flaskAddUrlUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });
            const result = await response.json();
            if (response.ok) {
                showMessage(result.message, 'success');
                urlInput.value = '';
                if (isAdminUser) {
                    // 관리자일 경우, 현재 보고 있는 뷰에 따라 새로고침
                    if (currentAdminTargetUser) { // 특정 유저를 보고 있으면 해당 유저 파일 새로고침
                        fetchAndRenderAdminTargetFiles(currentAdminTargetUser);
                    } else { // 통합 목록을 보고 있으면 통합 목록 새로고침
                        fetchAndRenderAdminTargetFiles(null);
                    }
                    fetchAndRenderUsers(); // 사용자 목록도 새로고침 (새 사용자 폴더 생길 경우 대비)
                } else {
                    fetchAndRenderUserFiles(); // 일반 사용자: 자기 파일 목록 새로고침
                }
            } else {
                showMessage(result.error || `URL에서 지식 추가 실패: ${response.statusText}`, 'danger');
            }
        } catch (error) {
            console.error('Error adding URL content:', error);
            showMessage('네트워크 오류: URL에서 지식 추가 중 오류가 발생했습니다.', 'danger');
        } finally {
            addUrlBtn.disabled = false;
            addUrlSpinner.style.display = 'none';
            urlInput.disabled = false;
        }
    });

    // =========================================================
    // 페이지 로드 시 초기화 로직
    // =========================================================
    window.addEventListener('load', function() {
        if (isAdminUser) {
            fetchAndRenderUsers(); // 관리자는 사용자 목록부터 로드
            fetchAndRenderAdminTargetFiles(null); // 관리자 페이지 로드 시, 모든 사용자 파일 통합 목록을 바로 보여줍니다.
        } else {
            fetchAndRenderUserFiles(); // 일반 사용자는 자기 파일 목록 로드
        }
    });
});