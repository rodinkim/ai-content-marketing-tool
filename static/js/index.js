document.addEventListener('DOMContentLoaded', function() {
    // --- DOM 요소 캐싱 ---
    const contentForm = document.getElementById('contentForm');
    const generateBtn = document.getElementById('generateBtn');
    const spinner = document.getElementById('generateSpinner');
    
    const contentTypeSelect = document.getElementById('contentType');
    const emailSubjectField = document.getElementById('emailSubjectField');
    
    const resultPlaceholder = document.getElementById('result-placeholder');
    const generatedContentDiv = document.getElementById('generatedContent');
    const copyBtn = document.getElementById('copyBtn');

    // --- 초기 UI 설정 ---
    function setupInitialUI() {
        emailSubjectField.style.display = contentTypeSelect.value === '이메일 뉴스레터' ? 'block' : 'none';
        
        const editContentData = localStorage.getItem('editContentData');
        if (editContentData) {
            const item = JSON.parse(editContentData);
            document.getElementById('topic').value = item.topic || '';
            document.getElementById('industry').value = item.industry || '';
            document.getElementById('contentType').value = item.content_type || '';
            document.getElementById('tone').value = item.tone || '';
            document.getElementById('length').value = item.length || '';
            document.getElementById('seoKeywords').value = item.seo_keywords || '';
            
            if (item.content_type === '이메일 뉴스레터') {
                emailSubjectField.style.display = 'block';
                document.getElementById('emailSubject').value = item.email_subject || '';
            }
            
            resultPlaceholder.style.display = 'none';
            generatedContentDiv.innerHTML = marked.parse(item.content);
            generatedContentDiv.style.display = 'block';
            copyBtn.style.display = 'inline-block';

            localStorage.removeItem('editContentData');
        }
    }
    
    // --- 이벤트 리스너 ---
    contentTypeSelect.addEventListener('change', function() {
        emailSubjectField.style.display = this.value === '이메일 뉴스레터' ? 'block' : 'none';
    });

    contentForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        generateBtn.disabled = true;
        spinner.style.display = 'inline-block';
        
        resultPlaceholder.style.display = 'none';
        generatedContentDiv.style.display = 'block';
        generatedContentDiv.innerHTML = '<div class="d-flex justify-content-center align-items-center" style="height: 200px;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        copyBtn.style.display = 'none';

        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        
        if (data.content_type !== '이메일 뉴스레터') {
            delete data.email_subject;
        }

        try {
            const response = await fetch('/content/generate_content', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const responseData = await response.json();

            if (response.ok) {
                generatedContentDiv.innerHTML = marked.parse(responseData.content);
                copyBtn.style.display = 'inline-block';
            } else {
                generatedContentDiv.innerHTML = `<div class="alert alert-danger">오류: ${responseData.error}</div>`;
            }
        } catch (error) {
            console.error('Fetch error:', error);
            generatedContentDiv.innerHTML = '<div class="alert alert-danger">네트워크 오류가 발생했습니다.</div>';
        } finally {
            generateBtn.disabled = false;
            spinner.style.display = 'none';
        }
    });

    copyBtn.addEventListener('click', function() {
        const contentToCopy = generatedContentDiv.innerText;
        navigator.clipboard.writeText(contentToCopy).then(() => {
            const originalText = this.textContent;
            this.textContent = '복사 완료!';
            setTimeout(() => { this.textContent = originalText; }, 2000);
        }).catch(err => {
            console.error('Copy failed:', err);
            alert('복사에 실패했습니다.');
        });
    });

    // --- 페이지 로드 시 실행 ---
    setupInitialUI();
});