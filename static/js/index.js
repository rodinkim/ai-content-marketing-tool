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
    
    // #### START MODIFICATION ####
    // 새로운 DOM 요소 캐싱
    const emailTypeGroup = document.getElementById('emailTypeGroup');
    const emailTypeSelect = document.getElementById('emailType');
    const emailOptionsGroup = document.getElementById('emailOptionsGroup'); // 기존 요소
    
    const snsImageOptionsGroup = document.getElementById('snsImageOptionsGroup');
    const imagePromptTextarea = document.getElementById('imagePrompt');
    const imageAspectRatioSelect = document.getElementById('imageAspectRatio');

    // SNS 관련 필드들 (필수 여부 설정을 위해 캐싱)
    const adPurposeInput = document.getElementById('adPurpose');
    const productCategoryInput = document.getElementById('productCategory');
    const targetAudienceSnsInput = document.getElementById('targetAudienceSns'); // UI 요소는 그대로 캐싱
    const brandStyleToneInput = document.getElementById('brandStyleTone');
    // emphasisMessageInput은 models.py에서 제거되었지만, UI에는 남아있을 수 있으므로 캐싱은 유지
    const emphasisMessageInput = document.getElementById('emphasisMessage'); 
    const cutCountSelect = document.getElementById('cutCount');
    const otherRequirementsTextarea = document.getElementById('otherRequirements');

    const initialResultImage = document.getElementById('initialResultImage');
    const initialResultText = document.getElementById('initialResultText');
    const generatedImage = document.getElementById('generatedImage');

    // 공통 고급 설정 필드 (emailOptionsGroup 밖에 있는 필드들)
    const commonTargetAudienceInput = document.querySelector('input[name="target_audience"]'); // 기존 타겟 고객
    const seoKeywordsInput = document.getElementById('seoKeywords');
    const keyPointsInput = document.querySelector('[name="key_points"]');
    const landingPageUrlInput = document.querySelector('[name="landing_page_url"]');
    // #### END MODIFICATION ####
    
    // --- 초기 UI 설정 ---
    function setupInitialUI() {
        const selectedValue = contentTypeSelect.value;
        
        // #### START MODIFICATION ####
        // 모든 그룹을 숨기고 선택된 타입에 따라 표시
        blogStyleGroup.style.display = 'none';
        emailTypeGroup.style.display = 'none';
        emailOptionsGroup.style.display = 'none';
        snsImageOptionsGroup.style.display = 'none';

        // 필수 속성 초기화 (모든 필드를 기본적으로 필수가 아니게)
        blogStyleSelect.required = false;
        emailTypeSelect.required = false;
        imagePromptTextarea.required = false;
        adPurposeInput.required = false;
        productCategoryInput.required = false;
        targetAudienceSnsInput.required = false; // SNS 타겟 필드
        brandStyleToneInput.required = false;
        emphasisMessageInput.required = false;
        cutCountSelect.required = false;
        imageAspectRatioSelect.required = false;
        otherRequirementsTextarea.required = false;

        // 텍스트 관련 필드들의 required 속성 초기화
        document.getElementById('tone').required = false;
        document.getElementById('length').required = false;
        document.getElementById('seoKeywords').required = false;
        // #### END MODIFICATION ####

        // '수정하기'를 통해 페이지에 진입한 경우 localStorage에서 데이터 로드
        const editContentData = localStorage.getItem('editContentData');
        if (editContentData) {
            const item = JSON.parse(editContentData);
            // 공통 필드 채우기
            document.getElementById('topic').value = item.topic || '';
            document.getElementById('industry').value = item.industry || '';
            contentTypeSelect.value = item.content_type || ''; // contentTypeSelect 값 설정
            
            // #### START MODIFICATION ####
            // '수정하기' 시 공통 고급 설정 필드 채우기 및 SNS 필드 채우는 로직 수정
            document.getElementById('tone').value = item.tone || '';
            document.getElementById('length').value = item.length_option || item.length || '';
            document.getElementById('seoKeywords').value = item.seo_keywords || '';
            
            // 공통 고급 설정 필드 (models.py에 맞게 통합된 필드)
            commonTargetAudienceInput.value = item.target_audience || ''; // 기존 target_audience 사용
            adPurposeInput.value = item.ad_purpose || '';
            productCategoryInput.value = item.product_category || '';
            brandStyleToneInput.value = item.brand_style_tone || '';
            keyPointsInput.value = item.key_points || ''; // 범용 key_points 사용
            landingPageUrlInput.value = item.landing_page_url || '';


            if (item.content_type === 'blog') {
                blogStyleGroup.style.display = 'block';
                blogStyleSelect.value = item.blog_style || '';
                blogStyleSelect.required = true;
            } else if (item.content_type.startsWith('email')) { 
                emailTypeGroup.style.display = 'block';
                emailTypeSelect.value = item.email_type || '';
                emailTypeSelect.required = true;

                emailOptionsGroup.style.display = 'block'; // 이메일 고급 옵션 그룹 표시
                document.getElementById('emailSubject').value = item.email_subject || '';
                // 이메일 고급 옵션 그룹 내의 타겟 고객, 강조 메시지, 랜딩 페이지 URL은 이제 공통 필드를 참조합니다.
            } else if (item.content_type === 'sns') {
                snsImageOptionsGroup.style.display = 'flex'; 
                imagePromptTextarea.value = item.topic || ''; // SNS는 topic 대신 imagePrompt 사용 (DB에 topic으로 저장됨)
                imagePromptTextarea.required = true; 

                // SNS 전용 필드 채우기
                // adPurposeInput, productCategoryInput, brandStyleToneInput은 이미 위에서 공통으로 채워짐
                targetAudienceSnsInput.value = item.target_audience || ''; // SNS 타겟도 기존 target_audience 사용
                emphasisMessageInput.value = item.emphasis_message || ''; // models.py에서 제거되었지만, UI에서 값을 가져올 수 있도록 유지
                cutCountSelect.value = item.cut_count || '';
                imageAspectRatioSelect.value = item.aspect_ratio_sns || '1:1';
                otherRequirementsTextarea.value = item.other_requirements || '';
            }
            // #### END MODIFICATION ####
            
            // 결과물 표시
            // #### START MODIFICATION ####
            // 이미지 결과물 표시 로직 수정
            resultPlaceholder.style.display = 'none'; 
            if (item.content_type === 'sns' && item.generated_image_url) {
                generatedImage.src = item.generated_image_url;
                generatedImage.style.display = 'block';
                generatedContentDiv.style.display = 'none'; 
                copyBtn.style.display = 'none'; 
            } else {
                generatedContentDiv.innerHTML = marked.parse(item.content || item.generated_text || '');
                generatedContentDiv.style.display = 'block';
                generatedImage.style.display = 'none'; 
            }
            // #### END MODIFICATION ####
            copyBtn.style.display = 'inline-block';

            localStorage.removeItem('editContentData');
        }
        updateUIBasedOnContentType(selectedValue);
    }
    
    // #### START MODIFICATION ####
    // contentType 변경 시 UI 업데이트 함수 분리 및 SNS 로직 추가
    function updateUIBasedOnContentType(selectedValue) {
        const isBlog = selectedValue === 'blog';
        const isEmail = selectedValue === 'email';
        const isSns = selectedValue === 'sns';

        blogStyleGroup.style.display = isBlog ? 'block' : 'none';
        blogStyleSelect.required = isBlog;
        if (!isBlog) blogStyleSelect.value = '';

        emailTypeGroup.style.display = isEmail ? 'block' : 'none';
        emailTypeSelect.required = isEmail;
        if (!isEmail) emailTypeSelect.value = '';

        emailOptionsGroup.style.display = isEmail ? 'block' : 'none';
        document.getElementById('emailSubject').required = isEmail;


        snsImageOptionsGroup.style.display = isSns ? 'flex' : 'none'; 
        imagePromptTextarea.required = isSns;
        imageAspectRatioSelect.required = isSns;
        // SNS 필수 필드들의 required 속성 관리
        adPurposeInput.required = isSns;
        productCategoryInput.required = isSns;
        targetAudienceSnsInput.required = isSns; 
        brandStyleToneInput.required = isSns;
        emphasisMessageInput.required = isSns;
        cutCountSelect.required = isSns;
        otherRequirementsTextarea.required = isSns;


        // 텍스트 관련 필드들의 required 속성 관리 (content_type이 'sns'일 때 필수가 아니게)
        document.getElementById('tone').required = !isSns;
        document.getElementById('length').required = !isSns;
        document.getElementById('seoKeywords').required = !isSns;
        // topic과 industry는 모든 콘텐츠 타입에서 필수 (HTML에 required 속성 유지)

        // 공통 고급 설정 필드들의 required 속성 관리 (models.py에서 nullable=True이므로 필수는 아님)
        // 이 필드들은 모든 타입에서 선택 사항이므로, 특정 타입에 따라 required를 변경하지 않습니다.
        // commonTargetAudienceInput.required = !isSns;
        // keyPointsInput.required = !isSns;
        // landingPageUrlInput.required = !isSns;
    }
    // #### END MODIFICATION ####

    // --- 이벤트 리스너 ---
    contentTypeSelect.addEventListener('change', function() {
        updateUIBasedOnContentType(this.value); 
    });

    contentForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        generateBtn.disabled = true;
        spinner.style.display = 'inline-block';
        
        // #### START MODIFICATION ####
        // 결과 표시 영역 초기화 로직 통합 및 이미지 결과 처리 추가
        resultPlaceholder.style.display = 'none'; 
        generatedContentDiv.style.display = 'none'; 
        generatedImage.style.display = 'none'; 
        copyBtn.style.display = 'none'; 

        generatedContentDiv.innerHTML = '<div class="d-flex justify-content-center align-items-center" style="height: 200px;"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        generatedContentDiv.style.display = 'block'; 
        // #### END MODIFICATION ####


        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        
        // #### START MODIFICATION ####
        // 콘텐츠 타입에 따른 데이터 정리 및 API 호출 분기
        const selectedContentType = data.content_type;
        let apiUrl = '';
        let payload = {};

        // 공통 고급 설정 필드들을 payload에 먼저 추가
        payload.topic = data.topic;
        payload.industry = data.industry;
        payload.content_type = selectedContentType;
        payload.target_audience = commonTargetAudienceInput.value || null; // 공통 타겟 고객 필드 사용
        payload.ad_purpose = adPurposeInput.value || null;
        payload.product_category = productCategoryInput.value || null;
        payload.brand_style_tone = brandStyleToneInput.value || null;
        payload.key_points = keyPointsInput.value || null;
        payload.landing_page_url = landingPageUrlInput.value || null;

        if (selectedContentType === 'blog') {
            apiUrl = '/content/generate_content';
            payload.tone = data.tone || null;
            payload.length = data.length || null;
            payload.seo_keywords = data.seo_keywords || null;
            payload.blog_style = data.blog_style || null;

            // 이메일/SNS 관련 필드는 payload에서 제거 (혹시라도 FormData에 남아있을 경우)
            delete payload.email_subject;
            delete payload.email_type;
            delete payload.image_prompt;
            delete payload.image_aspect_ratio;
            delete payload.cut_count;
            delete payload.other_requirements;
            delete payload.emphasis_message; // models.py에서 제거된 필드
            
        } else if (selectedContentType === 'email') {
            apiUrl = '/content/generate_content';
            payload.tone = data.tone || null;
            payload.length = data.length || null;
            payload.seo_keywords = data.seo_keywords || null;
            payload.email_subject = data.email_subject || null;
            payload.email_type = data.email_type || null;

            // 블로그/SNS 관련 필드는 payload에서 제거
            delete payload.blog_style;
            delete payload.image_prompt;
            delete payload.image_aspect_ratio;
            delete payload.cut_count;
            delete payload.other_requirements;
            delete payload.emphasis_message; // models.py에서 제거된 필드

        } else if (selectedContentType === 'sns') {
            apiUrl = '/content/generate-image';
            payload.prompt = imagePromptTextarea.value; // 이미지 생성 프롬프트는 필수
            payload.aspect_ratio_sns = imageAspectRatioSelect.value || null; // SNS 이미지 종횡비
            payload.cut_count = cutCountSelect.value ? parseInt(cutCountSelect.value) : null; // 숫자로 변환
            payload.other_requirements = otherRequirementsTextarea.value || null;
            
            // 텍스트 관련 필드는 payload에서 제거
            delete payload.tone;
            delete payload.length;
            delete payload.seo_keywords;
            delete payload.blog_style;
            delete payload.email_subject;
            delete payload.email_type;
            delete payload.emphasis_message; // models.py에서 제거된 필드

        } else {
            alert('콘텐츠 종류를 선택해주세요.');
            generateBtn.disabled = false;
            spinner.style.display = 'none';
            generatedContentDiv.style.display = 'none'; 
            resultPlaceholder.style.display = 'flex'; 
            return;
        }
        // #### END MODIFICATION ####

        try {
            const response = await fetch(apiUrl, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload) 
            });

            const responseData = await response.json();

            // #### START MODIFICATION ####
            // 결과 표시 로직 분기
            if (response.ok) {
                if (selectedContentType === 'sns' && responseData.image_url) {
                    generatedImage.src = responseData.image_url;
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
                    generatedImage.style.display = 'none';
                }
            } else {
                const errorMessage = responseData.error || responseData.message || '알 수 없는 오류';
                generatedContentDiv.innerHTML = `<div class="alert alert-danger">오류: ${errorMessage}</div>`;
                generatedContentDiv.style.display = 'block';
                generatedImage.style.display = 'none';
            }
            // #### END MODIFICATION ####
        } catch (error) {
            console.error('Fetch error:', error);
            generatedContentDiv.innerHTML = '<div class="alert alert-danger">네트워크 오류가 발생했습니다.</div>';
            generatedContentDiv.style.display = 'block';
            generatedImage.style.display = 'none';
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
