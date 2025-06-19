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
    // HTML에서 id가 'fileList', 'noFilesMessage', 'clearAllKbBtn'인 요소들을 참조
    const fileListDivUser = document.getElementById('fileList');
    const noFilesMessageUser = document.getElementById('noFilesMessage');
    const clearAllKbBtnUser = document.getElementById('clearAllKbBtn');

    // 관리자용 요소 (isAdminUser가 true일 때만 존재)
    // HTML에서 id가 'userList', 'noUsersMessage', 'adminFileList', 'noAdminFilesMessage', 'adminFileListHeader', 'adminClearUserKbBtn'인 요소들을 참조
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
            mainWrapper.prepend(alertDiv); // H2가 없으면 최상단에 추가
        }
        setTimeout(() => alertDiv.remove(), 5000); // 5초 후 메시지 제거
    }

    // =========================================================
    // 일반 사용자: 자신의 파일 목록을 불러와 렌더링하는 함수
    // =========================================================
    async function fetchAndRenderUserFiles() {
        if (!fileListDivUser) return; // 요소가 없으면 (관리자 모드일 경우) 실행하지 않음

        fileListDivUser.innerHTML = '';
        noFilesMessageUser.style.display = 'none';
        clearAllKbBtnUser.style.display = 'none';

        try {
            // flaskKnowledgeBaseFilesUrl는 "/knowledge_base/files" 엔드포인트에 매핑됩니다.
            const response = await fetch(flaskKnowledgeBaseFilesUrl);

            if (!response.ok) {
                // 로그인 필요 또는 리다이렉트 처리
                if (response.status === 401 || response.redirected) {
                    fileListDivUser.innerHTML = '<p class="text-info text-center">로그인하시면 지식 베이스를 관리할 수 있습니다.</p>';
                    if (response.redirected) {
                        window.location.href = flaskAuthLoginUrl; // 로그인 페이지로 리다이렉트
                    }
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const files = data.files || []; // 파일명만 포함 (예: "기사제목.txt")

            if (files.length === 0) {
                noFilesMessageUser.style.display = 'block'; // 파일 없음 메시지 표시
            } else {
                noFilesMessageUser.style.display = 'none';
                clearAllKbBtnUser.style.display = 'block'; // '모든 파일 삭제' 버튼 표시
                files.forEach(filename => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <span class="file-item-name">${filename}</span>
                        <div class="file-item-actions">
                            <button type="button" class="btn btn-sm btn-danger delete-file-btn" data-filename="${filename}">삭제</button>
                        </div>
                    `;
                    fileListDivUser.appendChild(fileItem);
                });
                // 동적으로 생성된 삭제 버튼에 이벤트 리스너 추가
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
    // 일반 사용자: 자신의 파일 삭제 함수
    // =========================================================
    async function handleDeleteUserFile(event) {
        const filename = event.target.dataset.filename; // 순수 파일명 (예: "기사제목.txt")
        if (confirm(`'${filename}' 파일을 정말로 삭제하시겠습니까?`)) {
            try {
                // flaskDeleteFileUrlBase는 "/knowledge_base/delete/" 로 끝납니다.
                // 합치면 "/knowledge_base/delete/기사제목.txt" 형태의 URL이 됩니다.
                const response = await fetch(`${flaskDeleteFileUrlBase}${filename}`, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    fetchAndRenderUserFiles(); // 파일 목록 새로고침
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
    if (clearAllKbBtnUser) { // 버튼이 존재할 때만 이벤트 리스너 추가
        clearAllKbBtnUser.addEventListener('click', async function() {
            if (confirm("정말로 나의 모든 지식 베이스 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
                try {
                    // flaskClearAllKbUrl는 "/knowledge_base/clear_all_files" 엔드포인트에 매핑됩니다.
                    const response = await fetch(flaskClearAllKbUrl, {
                        method: 'DELETE'
                    });
                    const result = await response.json();
                    if (response.ok) {
                        showMessage(result.message, 'success');
                        fetchAndRenderUserFiles(); // 파일 목록 새로고침
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
        if (!userListDiv) return; // 요소가 없으면 (일반 사용자 모드일 경우) 실행하지 않음

        userListDiv.innerHTML = '';
        noUsersMessage.style.display = 'none';
        adminFileListDiv.innerHTML = '<p class="text-muted text-center">사용자를 선택하여 파일을 확인하세요.</p>'; // 파일 목록 초기화
        noAdminFilesMessage.style.display = 'block';
        adminFileListHeader.textContent = '선택된 사용자의 파일';
        adminClearUserKbBtn.style.display = 'none';


        try {
            // flaskUsersListUrl는 "/knowledge_base/users" 엔드포인트에 매핑됩니다.
            const response = await fetch(flaskUsersListUrl);
            if (!response.ok) {
                const errorData = await response.json();
                showMessage(errorData.error || `사용자 목록을 불러오는 데 실패했습니다: ${response.statusText}`, 'danger');
                noUsersMessage.style.display = 'block';
                return;
            }
            const data = await response.json();
            const users = data.users || []; // 사용자명 목록 (예: ["ohsung", "testuser"])

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
                // 사용자 선택 이벤트 리스너 (이벤트 위임 대신 각 버튼에 직접 추가)
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
    // 관리자: 특정 사용자의 파일 목록을 불러와 렌더링하는 함수
    // =========================================================
    async function fetchAndRenderAdminTargetFiles(username) {
        if (!adminFileListDiv) return; // 요소가 없으면 실행하지 않음

        currentAdminTargetUser = username; // 현재 선택된 사용자 업데이트
        adminFileListDiv.innerHTML = '';
        noAdminFilesMessage.style.display = 'none';
        adminClearUserKbBtn.style.display = 'none';
        adminFileListHeader.textContent = `${username}의 파일 목록`;

        try {
            // flaskAdminTargetFilesUrlBase는 "/knowledge_base/files/"로 끝납니다.
            // 여기에 target_username을 붙여 "/knowledge_base/files/someuser" 형태로 만듭니다.
            const url = `${flaskAdminTargetFilesUrlBase}${username}`;
            const response = await fetch(url);

            if (!response.ok) {
                const errorData = await response.json();
                showMessage(errorData.error || `사용자 ${username}의 파일을 불러오는 데 실패했습니다: ${response.statusText}`, 'danger');
                noAdminFilesMessage.style.display = 'block';
                return;
            }

            const data = await response.json();
            const files = data.files || []; // 파일명만 포함 (예: "기사제목.txt")

            if (files.length === 0) {
                noAdminFilesMessage.style.display = 'block';
            } else {
                noAdminFilesMessage.style.display = 'none';
                adminClearUserKbBtn.style.display = 'block'; // 파일이 있으면 '모든 파일 삭제' 버튼 표시
                files.forEach(filename => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <span class="file-item-name">${filename}</span>
                        <div class="file-item-actions">
                            <button type="button" class="btn btn-sm btn-danger btn-admin-delete-file" data-filename="${filename}" data-username="${username}">삭제</button>
                        </div>
                    `;
                    adminFileListDiv.appendChild(fileItem);
                });
                // 동적으로 생성된 삭제 버튼에 이벤트 리스너 추가
                adminFileListDiv.querySelectorAll('.btn-admin-delete-file').forEach(button => {
                    button.addEventListener('click', handleAdminDeleteFile);
                });
            }
        } catch (error) {
            console.error(`Error fetching files for user ${username} (Admin):`, error);
            showMessage(`네트워크 오류: 사용자 ${username}의 파일 목록을 불러올 수 없습니다.`, 'danger');
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
        const filename = event.target.dataset.filename;
        const targetUsername = event.target.dataset.username;

        if (confirm(`관리자: 사용자 '${targetUsername}'의 파일 '${filename}'을 정말로 삭제하시겠습니까?`)) {
            try {
                // flaskAdminTargetDeleteUrlBase는 "/knowledge_base/delete/" 로 끝납니다.
                // Flask 라우트는 /delete/<target_username>/<filename> 형태이므로, URL을 정확히 조합합니다.
                const deleteUrl = `${flaskAdminTargetDeleteUrlBase}${targetUsername}/${filename}`;

                const response = await fetch(deleteUrl, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    fetchAndRenderAdminTargetFiles(targetUsername); // 파일 목록 새로고침
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
    if (adminClearUserKbBtn) { // 버튼이 존재할 때만 이벤트 리스너 추가
        adminClearUserKbBtn.addEventListener('click', async function() {
            if (!currentAdminTargetUser) {
                showMessage("파일을 삭제할 사용자를 먼저 선택해주세요.", "warning");
                return;
            }
            if (confirm(`관리자: 사용자 '${currentAdminTargetUser}'의 모든 지식 베이스 파일을 정말로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
                try {
                    // flaskAdminTargetClearAllUrlBase는 "/knowledge_base/clear_all_files/" 로 끝납니다.
                    // Flask 라우트는 /clear_all_files/<target_username> 형태이므로, URL을 정확히 조합합니다.
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
                // 파일 추가 후 현재 보고 있는 뷰에 따라 다르게 새로고침
                if (isAdminUser && currentAdminTargetUser) {
                    // 관리자가 특정 유저의 파일을 보고 있었으면 그 유저 파일 새로고침
                    fetchAndRenderAdminTargetFiles(currentAdminTargetUser);
                } else {
                    // 일반 사용자 또는 관리자가 자기 파일을 보고 있었으면 자기 파일 새로고침
                    fetchAndRenderUserFiles();
                }
                // 관리자는 사용자 목록도 새로고침할 필요가 있을 수 있음 (새로운 사용자 폴더 생성 등)
                if (isAdminUser) {
                    fetchAndRenderUsers();
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
        } else {
            fetchAndRenderUserFiles(); // 일반 사용자는 자기 파일 목록 로드
        }
    });
});