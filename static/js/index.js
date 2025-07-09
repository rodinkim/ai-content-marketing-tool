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

    // --- 초기 UI 설정 ---
    function setupInitialUI() {
        // '블로그 스타일' 메뉴의 초기 디스플레이 상태 설정
        blogStyleGroup.style.display = contentTypeSelect.value === 'blog' ? 'block' : 'none';
        
        // '수정하기'를 통해 페이지에 진입한 경우 localStorage에서 데이터 로드
        const editContentData = localStorage.getItem('editContentData');
        if (editContentData) {
            const item = JSON.parse(editContentData);
            document.getElementById('topic').value = item.topic || '';
            document.getElementById('industry').value = item.industry || '';
            document.getElementById('contentType').value = item.content_type || '';
            document.getElementById('tone').value = item.tone || '';
            document.getElementById('length').value = item.length || '';
            document.getElementById('seoKeywords').value = item.seo_keywords || '';
            
            // 로드된 데이터 타입이 'blog'일 경우 blog_style 필드 채우기
            if (item.content_type === 'blog') {
                blogStyleGroup.style.display = 'block';
                blogStyleSelect.value = item.blog_style || '';
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
        const selectedValue = this.value;

        // '콘텐츠 종류' 선택에 따라 '블로그 스타일' 메뉴를 동적으로 변경
        blogStyleGroup.style.display = selectedValue === 'blog' ? 'block' : 'none';
        blogStyleSelect.required = selectedValue === 'blog';
        if (selectedValue !== 'blog') {
            blogStyleSelect.value = '';
        }
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
        
        // 'blog' 타입이 아니면 blog_style 데이터를 전송하지 않도록 정리
        if (data.content_type !== 'blog') {
            delete data.blog_style;
        }

        try {
            const response = await fetch('/content/generate_content', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const responseData = await response.json();

            if (response.ok) {
                let htmlContent = marked.parse(responseData.content); 
                generatedContentDiv.innerHTML = htmlContent; 
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