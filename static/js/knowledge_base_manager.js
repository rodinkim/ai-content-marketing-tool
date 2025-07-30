document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소 변수
    const addUrlForm = document.getElementById('addUrlForm');
    const urlInput = document.getElementById('urlInput');
    const industrySelect = document.getElementById('industrySelect');
    const addUrlBtn = document.getElementById('addUrlBtn');
    const addUrlSpinner = addUrlBtn.querySelector('.spinner-border');
    const addUrlIcon = addUrlBtn.querySelector('.add-icon');
    const alertContainer = document.getElementById('alert-container');
    const fileListDiv = document.getElementById('fileList');
    const userListDiv = document.getElementById('userList');
    const paginationContainerAdmin = document.getElementById('pagination-container-admin');
    const paginationContainerUser = document.getElementById('pagination-container-user');

    // 상태 변수
    let currentAdminTarget = null;
    let currentPage = 1;

    // 공통 알림 함수(utils.js의 showAlert 사용)
    function showAlert(message, type = 'success') {
        if (window.showAlert) {
            window.showAlert(message, type);
        } else {
            // fallback
            alert(message);
        }
    }

    // 산업 분야 목록을 가져와 드롭다운을 채우는 함수
    async function fetchAndPopulateIndustries() {
        if (!industrySelect) return;
        try {
            let data;
            if (window.fetchJson) {
                data = await window.fetchJson(flaskIndustriesListUrl);
            } else {
                const response = await fetch(flaskIndustriesListUrl);
                data = await response.json();
            }
            industrySelect.innerHTML = '<option value="">-- 산업 분야 --</option>';
            (data.industries || []).forEach(industry => {
                const option = document.createElement('option');
                option.value = industry;
                option.textContent = industry;
                industrySelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching industries:', error);
        }
    }

    // 관리자용 사이드바를 렌더링하는 함수
    async function fetchAndRenderAdminSidebar() {
        if (!userListDiv) return;
        userListDiv.innerHTML = '<h5>관리 대상</h5>';
        try {
            let usersData, industriesData;
            if (window.fetchJson) {
                usersData = await window.fetchJson(flaskUsersListUrl);
                industriesData = await window.fetchJson(flaskIndustriesListUrl);
            } else {
                const [usersRes, industriesRes] = await Promise.all([fetch(flaskUsersListUrl), fetch(flaskIndustriesListUrl)]);
                usersData = await usersRes.json();
                industriesData = await industriesRes.json();
            }
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

    // 사이드바 아이템을 생성하는 함수
    function createSidebarItem(type, name, icon) {
        const item = document.createElement('button');
        item.className = 'sidebar-item';
        item.dataset.targetType = type;
        item.dataset.targetName = name;
        item.innerHTML = `<span class="icon">${icon}</span> <span class="name">${name}</span>`;
        item.addEventListener('click', handleSelectAdminTarget);
        return item;
    }

    // 관리자가 사이드바에서 대상을 선택했을 때 처리하는 함수
    function handleSelectAdminTarget(event) {
        const selectedBtn = event.currentTarget;
        currentAdminTarget = { type: selectedBtn.dataset.targetType, name: selectedBtn.dataset.targetName };
        document.querySelectorAll('.sidebar-item').forEach(btn => btn.classList.remove('active'));
        selectedBtn.classList.add('active');
        fetchAndRenderFiles(currentAdminTarget.type, currentAdminTarget.name, 1);
    }
    
    // 파일 목록을 서버에서 가져와 렌더링하는 함수 (페이지네이션 적용)
    async function fetchAndRenderFiles(type = null, name = null, page = 1) {
        if (!fileListDiv) return;
        currentPage = page;
        fileListDiv.innerHTML = '<div class="d-flex justify-content-center p-5"><div class="spinner-border text-primary" role="status"></div></div>';
        let url = new URL(isAdminUser ? flaskAdminTargetFilesUrlBase : flaskKnowledgeBaseFilesUrl, window.location.origin);
        if (isAdminUser && type && name) {
            url.searchParams.set('target_type', type);
            url.searchParams.set('target_username', name);
            document.getElementById('fileListHeader').textContent = `[${name}] 파일 목록`;
        }
        url.searchParams.set('page', page);
        try {
            let data;
            if (window.fetchJson) {
                data = await window.fetchJson(url);
            } else {
                const response = await fetch(url);
                data = await response.json();
            }
            const files = data.files || [];
            fileListDiv.innerHTML = '';
            if (files.length === 0) {
                fileListDiv.innerHTML = `<p class="text-muted text-center p-5">표시할 파일이 없습니다.</p>`;
            } else {
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
            }
            renderPagination(data.pagination);
        } catch (error) {
            console.error('Error fetching files:', error);
            fileListDiv.innerHTML = '<p class="text-danger text-center">파일 목록을 불러오는 데 실패했습니다.</p>';
            renderPagination(null);
        }
    }

    // 파일 아이템 DOM 요소를 생성하는 함수
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

    // 페이지네이션 UI를 생성하는 함수
    function renderPagination(pagination) {
        const container = isAdminUser ? paginationContainerAdmin : paginationContainerUser;
        if (!container) return;
        container.innerHTML = '';

        if (!pagination || pagination.total_pages <= 1) {
            return;
        }

        const { page, total_pages } = pagination;
        const ul = document.createElement('ul');
        ul.className = 'pagination';

        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${page === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" data-page="${page - 1}">이전</a>`;
        ul.appendChild(prevLi);

        for (let i = 1; i <= total_pages; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === page ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
            ul.appendChild(pageLi);
        }

        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${page === total_pages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" data-page="${page + 1}">다음</a>`;
        ul.appendChild(nextLi);

        container.appendChild(ul);
    }
    
    // 페이지네이션 클릭 이벤트를 처리하는 함수 (이벤트 위임)
    function setupPaginationListener() {
        const container = isAdminUser ? paginationContainerAdmin : paginationContainerUser;
        if(container) {
            container.addEventListener('click', function(event) {
                event.preventDefault();
                const target = event.target;
                if (target.tagName === 'A' && !target.closest('.disabled') && !target.closest('.active')) {
                    const page = parseInt(target.dataset.page, 10);
                    const { type, name } = currentAdminTarget || {};
                    fetchAndRenderFiles(type, name, page);
                }
            });
        }
    }

    // URL 추가 폼 제출 이벤트 리스너
    addUrlForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const url = urlInput.value;
        const industry = industrySelect.value;
        if (!industry) { showAlert('산업 분야를 선택해주세요.', 'warning'); return; }
        addUrlSpinner.style.display = 'inline-block';
        addUrlIcon.style.display = 'none';
        addUrlBtn.disabled = true;
        try {
            let result;
            if (window.fetchJson) {
                result = await window.fetchJson(flaskAddUrlUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, industry }) });
            } else {
                const response = await fetch(flaskAddUrlUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, industry }) });
                result = await response.json();
            }
            showAlert(result.message, 'success');
            urlInput.value = '';
            const { type, name } = currentAdminTarget || {};
            fetchAndRenderFiles(type, name, 1);
        } catch (error) {
            console.error('Error adding URL:', error);
            showAlert('네트워크 오류: 지식 추가 중 오류 발생', 'danger');
        } finally {
            addUrlSpinner.style.display = 'none';
            addUrlIcon.style.display = 'block';
            addUrlBtn.disabled = false;
        }
    });

    // 파일 목록에서 삭제 버튼 클릭 이벤트 리스너 (이벤트 위임)
    fileListDiv.addEventListener('click', async function(event) {
        const deleteButton = event.target.closest('.delete-btn');
        if (deleteButton) {
            const s3Key = deleteButton.dataset.s3Key;
            if (confirm(`'${s3Key.split('/').pop()}' 파일을 정말로 삭제하시겠습니까?`)) {
                try {
                    let result;
                    if (window.fetchJson) {
                        result = await window.fetchJson(`${flaskDeleteFileUrlBase}${s3Key}`, { method: 'DELETE' });
                    } else {
                        const response = await fetch(`${flaskDeleteFileUrlBase}${s3Key}`, { method: 'DELETE' });
                        result = await response.json();
                    }
                    showAlert(result.message, 'success');
                    const { type, name } = currentAdminTarget || {};
                    fetchAndRenderFiles(type, name, currentPage);
                } catch (error) {
                    console.error('Error deleting file:', error);
                    showAlert('파일 삭제 중 오류 발생', 'danger');
                }
            }
        }
    });

    // --- 최초 실행 ---
    fetchAndPopulateIndustries();
    setupPaginationListener();
    if (isAdminUser) {
        fetchAndRenderAdminSidebar();
    } else {
        fetchAndRenderFiles(null, null, 1);
    }
});