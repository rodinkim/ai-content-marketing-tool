document.addEventListener('DOMContentLoaded', function() {
    // --- DOM 요소 캐싱 ---
    const contentForm = document.getElementById('contentForm');
    const generateBtn = document.getElementById('generateBtn');
    const spinner = document.getElementById('generateSpinner');
    const contentTypeSelect = document.getElementById('contentType');
    const blogStyleGroup = document.getElementById('blogStyleGroup');
    const blogStyleSelect = document.getElementById('blogStyle');
    const resultPlaceholder = document.getElementById('result-placeholder');
    const generatedContentDiv = document.getElementById('generatedContent');
    const copyBtn = document.getElementById('copyBtn');
    
    // ▼▼▼ [수정 1] 새로운 DOM 요소 캐싱 ▼▼▼
    const emailTypeGroup = document.getElementById('emailTypeGroup');
    const emailTypeSelect = document.getElementById('emailType');
    // ▲▲▲ [수정 1] ▲▲▲
    
    const emailOptionsGroup = document.getElementById('emailOptionsGroup');

    // --- 초기 UI 설정 ---
    function setupInitialUI() {
        const selectedValue = contentTypeSelect.value;
        blogStyleGroup.style.display = selectedValue === 'blog' ? 'block' : 'none';
        
        // ▼▼▼ [수정 2] 이메일 유형 및 고급 설정 그룹 초기 상태 설정 ▼▼▼
        emailTypeGroup.style.display = selectedValue === 'email' ? 'block' : 'none';
        emailOptionsGroup.style.display = selectedValue === 'email' ? 'block' : 'none';
        // ▲▲▲ [수정 2] ▲▲▲
        
        // '수정하기'를 통해 페이지에 진입한 경우 localStorage에서 데이터 로드
        const editContentData = localStorage.getItem('editContentData');
        if (editContentData) {
            const item = JSON.parse(editContentData);
            // 공통 필드 채우기
            document.getElementById('topic').value = item.topic || '';
            document.getElementById('industry').value = item.industry || '';
            document.getElementById('contentType').value = item.content_type || '';
            document.getElementById('tone').value = item.tone || '';
            document.getElementById('length').value = item.length_option || item.length || '';
            document.getElementById('seoKeywords').value = item.seo_keywords || '';
            
            // 콘텐츠 타입에 따라 다른 UI 처리
            if (item.content_type === 'blog') {
                blogStyleGroup.style.display = 'block';
                blogStyleSelect.value = item.blog_style || '';

            } else if (item.content_type === 'email') {
                // ▼▼▼ [수정 3] '수정하기' 시 이메일 필드 채우는 로직 수정 ▼▼▼
                // 이메일 유형 (필수 항목)
                emailTypeGroup.style.display = 'block';
                emailTypeSelect.value = item.email_type || '';

                // 고급 설정 (선택 항목)
                emailOptionsGroup.style.display = 'block';
                document.querySelector('[name="email_subject"]').value = item.email_subject || '';
                document.querySelector('[name="target_audience"]').value = item.target_audience || '';
                document.querySelector('[name="key_points"]').value = item.key_points || '';
                document.querySelector('[name="landing_page_url"]').value = item.landing_page_url || '';
                // ▲▲▲ [수정 3] ▲▲▲
            }
            
            // 결과물 표시
            resultPlaceholder.style.display = 'none';
            generatedContentDiv.innerHTML = marked.parse(item.content || item.generated_text || '');
            generatedContentDiv.style.display = 'block';
            copyBtn.style.display = 'inline-block';

            localStorage.removeItem('editContentData');
        }
    }
    
    // --- 이벤트 리스너 ---
    contentTypeSelect.addEventListener('change', function() {
        const selectedValue = this.value;

        const isBlog = selectedValue === 'blog';
        const isEmail = selectedValue === 'email';

        // 블로그 스타일 메뉴 표시/숨김
        blogStyleGroup.style.display = isBlog ? 'block' : 'none';
        blogStyleSelect.required = isBlog;
        if (!isBlog) {
            blogStyleSelect.value = '';
        }

        // ▼▼▼ [수정 4] 이메일 유형 메뉴 표시/숨김 로직 추가 ▼▼▼
        emailTypeGroup.style.display = isEmail ? 'block' : 'none';
        emailTypeSelect.required = isEmail;
        if (!isEmail) {
            emailTypeSelect.value = '';
        }
        // ▲▲▲ [수정 4] ▲▲▲

        // 이메일 전용 고급 옵션 그룹 표시/숨김
        emailOptionsGroup.style.display = isEmail ? 'block' : 'none';
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
        
        // 불필요한 데이터 정리 로직 수정
        if (data.content_type !== 'blog') {
            delete data.blog_style;
        }
        if (data.content_type !== 'email') {
            delete data.email_subject;
            delete data.target_audience;
            // ▼▼▼ [수정 5] 이 줄이 삭제되었는지 확인하세요. 이메일 유형은 더 이상 여기서 지우지 않습니다. ▼▼▼
            // delete data.email_type; 
            // ▲▲▲ [수정 5] ▲▲▲
            delete data.key_points;
            delete data.landing_page_url;
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
            this.style.backgroundColor = '#198754';
            setTimeout(() => { 
                this.textContent = originalText;
                this.style.backgroundColor = 'var(--gray-color)';
            }, 2000);
        }).catch(err => {
            console.error('Copy failed:', err);
            alert('복사에 실패했습니다.');
        });
    });

    // --- 페이지 로드 시 실행 ---
    setupInitialUI();
});