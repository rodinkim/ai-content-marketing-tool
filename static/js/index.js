document.addEventListener('DOMContentLoaded', function() {
    // --- 1. DOM 요소 캐싱 ---
    const contentForm = document.getElementById('contentForm');
    const generateBtn = document.getElementById('generateBtn');
    const spinner = document.getElementById('generateSpinner');
    const contentTypeSelect = document.getElementById('contentType');
    const resultPlaceholder = document.getElementById('result-placeholder');
    const generatedContentDiv = document.getElementById('generatedContent');
    const copyBtn = document.getElementById('copyBtn');
    const generatedImage = document.getElementById('generatedImage');

    // 각 콘텐츠 타입별 옵션 그룹 (HTML의 실제 ID/클래스에 맞게 수정)
    const advancedOptions = document.getElementById('advancedOptions');
    const blogStyleGroup = document.getElementById('blogStyleGroup');
    const emailOptions = document.getElementById('emailOptions');
    const snsOptions = document.getElementById('snsOptions');
    const textOnlyGroup = document.querySelector('.advanced-text-only');


    // --- 2. 이벤트 리스너 설정 ---

    // '콘텐츠 종류' 선택이 변경될 때마다 UI를 업데이트합니다.
    contentTypeSelect.addEventListener('change', function() {
        updateUIBasedOnContentType(this.value);
    });

    // '생성하기' 버튼이 있는 폼을 제출할 때 실행됩니다.
    contentForm.addEventListener('submit', async function(event) {
        event.preventDefault(); // 폼의 기본 제출 동작(새로고침)을 막습니다.

        // [유효성 검사] SNS 이미지 생성 시 주제(프롬프트)가 비어있는지 확인합니다.
        const selectedContentTypeValue = document.getElementById('contentType').value;
        const topicValue = document.getElementById('topic').value;

        if (selectedContentTypeValue === 'sns' && !topicValue.trim()) {
            alert('SNS 콘텐츠를 생성하려면 핵심 주제(이미지 프롬프트)를 반드시 입력해야 합니다.');
            return; // 함수 실행을 중단합니다.
        }

        // 버튼을 비활성화하고 로딩 스피너를 보여줍니다.
        generateBtn.disabled = true;
        spinner.style.display = 'inline-block';
        
        // 이전 결과 영역을 초기화합니다.
        resultPlaceholder.style.display = 'none'; 
        generatedContentDiv.style.display = 'none'; 
        generatedImage.style.display = 'none'; 
        copyBtn.style.display = 'none'; 

        // 로딩 스피너를 표시합니다.
        generatedContentDiv.innerHTML = '<div class="d-flex justify-content-center align-items-center" style="height: 200px;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        generatedContentDiv.style.display = 'block'; 

        // 폼 데이터를 가져와 서버에 보낼 payload 객체로 변환합니다.
        const formData = new FormData(event.target);
        const payload = Object.fromEntries(formData.entries());
        
        // 빈 값은 'null'로 변환합니다.
        for (const key in payload) {
            if (payload[key] === '') {
                payload[key] = null;
            }
        }
        
        // SNS 고급 입력값 개수 체크 (프론트엔드에서 안내)
        if (payload.content_type === 'sns') {
            const advancedFields = [
                "brand_style_tone", "product_category", "target_audience", "ad_purpose", "key_points"
            ];
            const filled = advancedFields.filter(field => payload[field] !== null && payload[field] !== undefined && String(payload[field]).trim() !== "").length;
            if (filled < 2) {
                showGuideMessage(
                    `<div style='font-family: "Noto Sans KR", sans-serif; font-size:17px; line-height:1.9; color:#222;'>
                    조금 더 구체적으로 입력해 주시면,<br>
                    <span style='color:#0052cc; font-weight:600;'>AI가 더욱 완성도 높은 이미지를 만들어 드릴 수 있어요 🌿</span><br><br>
                    <b>아래 항목 중 2개 이상</b> 입력해 주세요:<br>
                    <span style='color:#1976d2;'>· 타겟 고객 · 브랜드 스타일 · 제품 카테고리<br>· 광고 목적 · 핵심 메시지</span><br><br>
                    <span style='font-size:14px; color:#888;'>* 정보가 풍부할수록 이미지도 더 좋아집니다 :)</span>
                    </div>`
                );
                generateBtn.disabled = false;
                spinner.style.display = 'none';
                return;
            }
        }

        // 콘텐츠 종류에 따라 API URL을 설정하고 불필요한 필드를 제거합니다.
        let apiUrl = '';
        if (payload.content_type === 'blog' || payload.content_type === 'email') {
            apiUrl = '/content/generate_content';
            delete payload.cut_count;
            delete payload.aspect_ratio_sns;
            delete payload.other_requirements;
        } else if (payload.content_type === 'sns') {
            apiUrl = '/content/generate-image';
            delete payload.blog_style;
            delete payload.email_type;
            delete payload.email_subject;
            delete payload.tone;
            delete payload.length_option;
            delete payload.seo_keywords;
            delete payload.landing_page_url;
        } else {
            alert('콘텐츠 종류를 선택해주세요.');
            generateBtn.disabled = false;
            spinner.style.display = 'none';
            generatedContentDiv.style.display = 'none'; 
            resultPlaceholder.style.display = 'flex'; 
            return;
        }

        // 서버에 데이터를 요청합니다.
        try {
            const response = await fetch(apiUrl, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload) 
            });
            const responseData = await response.json();

            // 응답 결과에 따라 화면을 업데이트합니다.
            if (response.ok) {
                if (responseData.status === "info") {
                    showGuideMessage(responseData.message);
                    generatedContentDiv.style.display = 'none';
                    generatedImage.style.display = 'none';
                    copyBtn.style.display = 'none';
                    return; // 안내만 띄우고 함수 종료
                }
                if (payload.content_type === 'sns' && responseData.image_urls && responseData.image_urls.length > 0) {
                    generatedImage.src = responseData.image_urls[0];
                    generatedImage.style.display = 'block';
                    generatedContentDiv.style.display = 'none'; 
                    copyBtn.style.display = 'none'; 
                } else if (responseData.content) { 
                    generatedContentDiv.innerHTML = marked.parse(responseData.content);
                    generatedContentDiv.style.display = 'block';
                    generatedImage.style.display = 'none'; 
                    copyBtn.style.display = 'inline-block';
                } else {
                    generatedContentDiv.innerHTML = `<div class="alert alert-warning">콘텐츠가 생성되었지만, 표시할 내용이 없습니다.</div>`;
                    generatedContentDiv.style.display = 'block';
                }
            } else {
                const errorMessage = responseData.error || responseData.message || '알 수 없는 오류';
                generatedContentDiv.innerHTML = `<div class="alert alert-danger">오류: ${errorMessage}</div>`;
                generatedContentDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('Fetch error:', error);
            generatedContentDiv.innerHTML = '<div class="alert alert-danger">네트워크 오류가 발생했습니다.</div>';
            generatedContentDiv.style.display = 'block';
        } finally {
            // 요청이 끝나면 버튼을 다시 활성화하고 스피너를 숨깁니다.
            generateBtn.disabled = false;
            spinner.style.display = 'none';
        }
    });

    // '클립보드에 복사' 버튼을 클릭할 때 실행됩니다.
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


    // --- 3. UI 업데이트 함수 ---
    function updateUIBasedOnContentType(selectedValue) {
        const isBlog = selectedValue === 'blog';
        const isEmail = selectedValue === 'email';
        const isSns = selectedValue === 'sns';
        
        // 콘텐츠 종류가 선택되었는지에 따라 고급 설정 전체를 보이거나 숨김
        if (isBlog || isEmail || isSns) {
            advancedOptions.style.display = 'block';
        } else {
            advancedOptions.style.display = 'none';
        }

        // 모든 개별 옵션 그룹을 일단 숨깁니다.
        textOnlyGroup.style.display = 'none';
        blogStyleGroup.style.display = 'none';
        emailOptions.style.display = 'none';
        snsOptions.style.display = 'none';
        
        // 선택된 종류에 맞는 UI만 보여줍니다.
        if (isBlog) {
            textOnlyGroup.style.display = 'block';
            blogStyleGroup.style.display = 'block';
        } else if (isEmail) {
            textOnlyGroup.style.display = 'block';
            emailOptions.style.display = 'block'; 
        } else if (isSns) {
            snsOptions.style.display = 'flex';
        }
    }

    // --- 4. 페이지 로드 시 초기 실행 ---
    function initializePage() {
        updateUIBasedOnContentType(contentTypeSelect.value);
    }

    initializePage();
});

function showGuideMessage(message) {
    const modalBody = document.getElementById('guideModalBody');
    modalBody.innerHTML = message;
    const guideModalEl = document.getElementById('guideModal');
    const guideModal = new bootstrap.Modal(guideModalEl);
    guideModal.show();

    // 팝업이 닫힐 때 UI를 초기 상태로 복구
    guideModalEl.addEventListener('hidden.bs.modal', function handler() {
        // 결과 영역/이미지/복사 버튼/로딩 스피너 모두 숨김
        generatedContentDiv.style.display = 'none';
        generatedImage.style.display = 'none';
        copyBtn.style.display = 'none';
        spinner.style.display = 'none';
        resultPlaceholder.style.display = 'flex'; // 필요하다면
        generateBtn.disabled = false;
        // 이벤트 중복 등록 방지
        guideModalEl.removeEventListener('hidden.bs.modal', handler);
    });
}