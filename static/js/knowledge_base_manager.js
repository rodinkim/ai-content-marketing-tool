// static/js/knowledge_base_manager.js

// DOM 요소 캐싱
const fileListDiv = document.getElementById('fileList');
const noFilesMessage = document.getElementById('noFilesMessage');
const clearAllKbBtn = document.getElementById('clearAllKbBtn');

const addUrlForm = document.getElementById('addUrlForm');
const urlInput = document.getElementById('urlInput');
const addUrlBtn = document.getElementById('addUrlBtn');
const addUrlSpinner = addUrlBtn.querySelector('.spinner-border');

const uploadFileForm = document.getElementById('uploadFileForm');
const fileInput = document.getElementById('fileInput');
const uploadFileBtn = document.getElementById('uploadFileBtn');
const uploadFileSpinner = uploadFileBtn.querySelector('.spinner-border');

// --- 파일 목록을 불러와 렌더링하는 함수 ---
async function fetchAndRenderFiles() {
    try {
        const response = await fetch(flaskKnowledgeBaseFilesUrl); 
        if (!response.ok) {
            if (response.status === 401 || response.redirected) {
                fileListDiv.innerHTML = '<p class="text-info text-center">로그인하시면 지식 베이스를 관리할 수 있습니다.</p>';
                noFilesMessage.style.display = 'none';
                clearAllKbBtn.style.display = 'none';
                if (response.redirected) {
                    window.location.href = flaskAuthLoginUrl;
                }
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const files = data.files || [];

        fileListDiv.innerHTML = ''; 

        if (files.length === 0) {
            noFilesMessage.style.display = 'block';
            clearAllKbBtn.style.display = 'none';
        } else {
            noFilesMessage.style.display = 'none';
            clearAllKbBtn.style.display = 'block'; 
            files.forEach(filename => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                // data-filename에 파일의 전체 상대 경로를 저장합니다 (예: "Fashion/기사제목.txt")
                fileItem.innerHTML = `
                    <span class="file-item-name">${filename}</span>
                    <div class="file-item-actions">
                        <button type="button" class="btn btn-sm btn-danger delete-file-btn" data-filename="${filename}">삭제</button>
                    </div>
                `;
                fileListDiv.appendChild(fileItem);
            });
            // 동적으로 생성된 삭제 버튼에 이벤트 리스너 추가
            document.querySelectorAll('.delete-file-btn').forEach(button => {
                button.addEventListener('click', handleDeleteFile);
            });
        }
    } catch (error) {
        console.error('Error fetching knowledge base files:', error);
        fileListDiv.innerHTML = '<p class="text-danger text-center">지식 베이스 파일을 불러오는 데 실패했습니다.</p>';
        noFilesMessage.style.display = 'none';
        clearAllKbBtn.style.display = 'none';
    }
}

// --- 파일 삭제 함수 ---
async function handleDeleteFile(event) {
    const filename = event.target.dataset.filename; // 예: "Fashion/기사제목.txt"
    if (confirm(`'${filename}' 파일을 정말로 삭제하시겠습니까?`)) {
        try {
            // flaskDeleteFileUrlBase는 "/knowledge_base/delete/" 로 정확히 구성되어 있습니다.
            // filename은 'Fashion/기사제목.txt'와 같은 knowledge_base 하위의 상대 경로여야 합니다.
            // 합치면 "/knowledge_base/delete/Fashion/기사제목.txt" 형태의 URL이 됩니다.
            const response = await fetch(`${flaskDeleteFileUrlBase}${filename}`, { 
                method: 'DELETE'
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.message);
                fetchAndRenderFiles(); 
            } else {
                alert(`파일 삭제 실패: ${result.error || response.statusText}`);
            }
        } catch (error) {
            console.error('Error deleting file:', error);
            alert('파일 삭제 중 오류가 발생했습니다.');
        }
    }
}

// --- URL에서 지식 추가 폼 제출 핸들러 ---
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
            alert(result.message);
            urlInput.value = ''; 
            fetchAndRenderFiles(); 
        } else {
            alert(`URL에서 지식 추가 실패: ${result.error || response.statusText}`);
        }
    } catch (error) {
        console.error('Error adding URL content:', error);
        alert('URL에서 지식 추가 중 오류가 발생했습니다.');
    } finally {
        addUrlBtn.disabled = false;
        addUrlSpinner.style.display = 'none';
        urlInput.disabled = false;
    }
});

// --- 파일 업로드 폼 제출 핸들러 ---
uploadFileForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    uploadFileBtn.disabled = true;
    uploadFileSpinner.style.display = 'inline-block';
    fileInput.disabled = true;

    const formData = new FormData(uploadFileForm);

    try {
        const response = await fetch(flaskUploadFileUrl, { 
            method: 'POST',
            body: formData 
        });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            fileInput.value = ''; 
            fetchAndRenderFiles(); 
        } else {
            alert(`파일 업로드 실패: ${result.error || response.statusText}`);
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        alert('파일 업로드 중 오류가 발생했습니다.');
    } finally {
        uploadFileBtn.disabled = false;
        uploadFileSpinner.style.display = 'none';
        fileInput.disabled = false;
    }
});

// --- 모든 지식 베이스 파일 삭제 함수 ---
async function clearAllKbFiles() {
    if (confirm("정말로 모든 지식 베이스 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
        try {
            // flaskClearAllKbUrl 변수 사용 (knowledge_base_routes.clear_all_knowledge_base_files)
            const response = await fetch(flaskClearAllKbUrl, { 
                method: 'DELETE'
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.message);
                fetchAndRenderFiles(); 
            } else {
                alert(`모든 파일 삭제 실패: ${result.error || response.statusText}`);
            }
        } catch (error) {
            console.error('Error clearing all KB files:', error);
            alert('모든 지식 베이스 파일 삭제 중 오류가 발생했습니다.');
        }
    }
}
clearAllKbBtn.addEventListener('click', clearAllKbFiles);


// 페이지 로드 시 파일 목록 불러오기
window.addEventListener('load', fetchAndRenderFiles);