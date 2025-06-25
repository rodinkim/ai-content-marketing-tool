document.addEventListener('DOMContentLoaded', function() {
    const addUrlForm = document.getElementById('addUrlForm');
    const urlInput = document.getElementById('urlInput');
    const industrySelect = document.getElementById('industrySelect');
    const addUrlBtn = document.getElementById('addUrlBtn');
    const addUrlSpinner = addUrlBtn.querySelector('.spinner-border');
    const addUrlIcon = addUrlBtn.querySelector('.add-icon');
    const alertContainer = document.getElementById('alert-container');
    const fileListDiv = document.getElementById('fileList');
    const userListDiv = document.getElementById('userList');
    let currentAdminTarget = null;

    function showMessage(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show m-3`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        alertContainer.prepend(alertDiv);
        setTimeout(() => bootstrap.Alert.getOrCreateInstance(alertDiv)?.close(), 5000);
    }

    async function fetchAndPopulateIndustries() {
        if (!industrySelect) return;
        try {
            const response = await fetch(flaskIndustriesListUrl);
            if (!response.ok) throw new Error('Failed to fetch industries');
            const data = await response.json();
            industrySelect.innerHTML = '<option value="">-- 산업 분야 --</option>';
            (data.industries || []).forEach(industry => {
                const option = document.createElement('option');
                option.value = industry;
                option.textContent = industry;
                industrySelect.appendChild(option);
            });
        } catch (error) { console.error('Error fetching industries:', error); }
    }

    async function fetchAndRenderAdminSidebar() {
        if (!userListDiv) return;
        userListDiv.innerHTML = '<h5>관리 대상</h5>';
        try {
            const [usersRes, industriesRes] = await Promise.all([fetch(flaskUsersListUrl), fetch(flaskIndustriesListUrl)]);
            if (!usersRes.ok || !industriesRes.ok) throw new Error('Failed to fetch admin data');

            const usersData = await usersRes.json();
            const industriesData = await industriesRes.json();

            const industryHeader = document.createElement('h5');
            industryHeader.className = 'mt-4';
            industryHeader.textContent = '산업별 공용';
            userListDiv.appendChild(industryHeader);
            industriesData.industries.forEach(industry => userListDiv.appendChild(createSidebarItem('industry', industry, '🏢')));

            const userHeader = document.createElement('h5');
            userHeader.className = 'mt-4';
            userHeader.textContent = '사용자별';
            userListDiv.appendChild(userHeader);
            usersData.users.forEach(username => userListDiv.appendChild(createSidebarItem('user', username, '👤')));
        } catch (error) {
            console.error('Error fetching admin sidebar data:', error);
            userListDiv.innerHTML += '<p class="text-danger small">목록 로드 실패</p>';
        }
    }

    function createSidebarItem(type, name, icon) {
        const item = document.createElement('button');
        item.className = 'sidebar-item';
        item.dataset.targetType = type;
        item.dataset.targetName = name;
        item.innerHTML = `<span class="icon">${icon}</span> <span class="name">${name}</span>`;
        item.addEventListener('click', handleSelectAdminTarget);
        return item;
    }

    function handleSelectAdminTarget(event) {
        const selectedBtn = event.currentTarget;
        currentAdminTarget = { type: selectedBtn.dataset.targetType, name: selectedBtn.dataset.targetName };
        document.querySelectorAll('.sidebar-item').forEach(btn => btn.classList.remove('active'));
        selectedBtn.classList.add('active');
        fetchAndRenderFiles(currentAdminTarget.type, currentAdminTarget.name);
    }

    async function fetchAndRenderFiles(type = null, name = null) {
        if (!fileListDiv) return;
        fileListDiv.innerHTML = '<div class="d-flex justify-content-center p-5"><div class="spinner-border text-primary" role="status"></div></div>';
        let url = flaskKnowledgeBaseFilesUrl;
        if (isAdminUser && type && name) {
            url = `${flaskAdminTargetFilesUrlBase.split('?')[0]}?target_type=${type}&target_username=${name}`;
            document.getElementById('fileListHeader').textContent = `[${name}] 파일 목록`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            const files = data.files || [];
            fileListDiv.innerHTML = '';
            if (files.length === 0) {
                fileListDiv.innerHTML = `<p class="text-muted text-center p-5">표시할 파일이 없습니다.</p>`;
                return;
            }

            if (isAdminUser) {
                files.forEach(fileData => fileListDiv.appendChild(createFileItem(fileData)));
            } else {
                const groupedFiles = {};
                files.forEach(fileData => {
                    const groupName = fileData.s3_key.split('/')[0];
                    if (!groupedFiles[groupName]) groupedFiles[groupName] = [];
                    groupedFiles[groupName].push(fileData);
                });
                Object.keys(groupedFiles).sort().forEach(groupName => {
                    const groupTitle = document.createElement('h4');
                    groupTitle.className = 'kb-group-title';
                    groupTitle.textContent = groupName;
                    fileListDiv.appendChild(groupTitle);
                    const listContainer = document.createElement('div');
                    listContainer.className = 'list-container';
                    groupedFiles[groupName].forEach(fileData => listContainer.appendChild(createFileItem(fileData)));
                    fileListDiv.appendChild(listContainer);
                });
            }
        } catch (error) {
            console.error('Error fetching files:', error);
            fileListDiv.innerHTML = '<p class="text-danger text-center">파일 목록을 불러오는 데 실패했습니다.</p>';
        }
    }

    function createFileItem(fileData) {
        const item = document.createElement('div');
        item.className = 'kb-file-item';
        item.innerHTML = `
            <span class="icon">📄</span>
            <span class="filename" title="${fileData.s3_key}">${fileData.display_name}</span>
            <button class="delete-btn" data-s3-key="${fileData.s3_key}" title="삭제">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash3-fill" viewBox="0 0 16 16"><path d="M11 1.5v1h3.5a.5.5 0 0 1 0 1h-.538l-.853 10.66A2 2 0 0 1 11.115 16h-6.23a2 2 0 0 1-1.994-1.84L2.038 3.5H1.5a.5.5 0 0 1 0-1H5v-1A1.5 1.5 0 0 1 6.5 0h3A1.5 1.5 0 0 1 11 1.5Zm-5 0v1h4v-1a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5ZM4.5 5.029l.5 8.5a.5.5 0 1 0 .998-.06l-.5-8.5a.5.5 0 1 0-.998.06Zm3.53-.528a.5.5 0 0 0-.499.438l-.5 8.5a.5.5 0 0 0 .998.058l.5-8.5a.5.5 0 0 0-.499-.496ZM9.5 5a.5.5 0 0 0-.5.5v8.5a.5.5 0 0 0 1 0V5.5a.5.5 0 0 0-.5-.5Z"/></svg>
            </button>
        `;
        return item;
    }

    addUrlForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const url = urlInput.value;
        const industry = industrySelect.value;
        if (!industry) { showMessage('산업 분야를 선택해주세요.', 'warning'); return; }
        addUrlSpinner.style.display = 'inline-block';
        addUrlIcon.style.display = 'none';
        addUrlBtn.disabled = true;
        try {
            const response = await fetch(flaskAddUrlUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, industry }) });
            const result = await response.json();
            if (response.ok) {
                showMessage(result.message, 'success');
                urlInput.value = '';
                const { type, name } = currentAdminTarget || {};
                fetchAndRenderFiles(type, name);
            } else { showMessage(result.error || 'URL 추가 실패', 'danger'); }
        } catch (error) { console.error('Error adding URL:', error); showMessage('네트워크 오류: 지식 추가 중 오류 발생', 'danger'); } 
        finally { addUrlSpinner.style.display = 'none'; addUrlIcon.style.display = 'block'; addUrlBtn.disabled = false; }
    });

    fileListDiv.addEventListener('click', async function(event) {
        const deleteButton = event.target.closest('.delete-btn');
        if (deleteButton) {
            const s3Key = deleteButton.dataset.s3Key;
            if (confirm(`'${s3Key.split('/').pop()}' 파일을 정말로 삭제하시겠습니까?`)) {
                try {
                    const response = await fetch(`${flaskDeleteFileUrlBase}${s3Key}`, { method: 'DELETE' });
                    const result = await response.json();
                    if (response.ok) {
                        showMessage(result.message, 'success');
                        const { type, name } = currentAdminTarget || {};
                        fetchAndRenderFiles(type, name);
                    } else { showMessage(result.error || '파일 삭제 실패', 'danger'); }
                } catch (error) { console.error('Error deleting file:', error); showMessage('파일 삭제 중 오류 발생', 'danger'); }
            }
        }
    });

    fetchAndPopulateIndustries();
    if (isAdminUser) {
        fetchAndRenderAdminSidebar();
    } else {
        fetchAndRenderFiles();
    }
});