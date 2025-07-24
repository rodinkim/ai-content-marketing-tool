// content.js - 콘텐츠 생성 관련 로직만 분리

document.addEventListener('DOMContentLoaded', function() {
    // --- 1. DOM 요소 캐싱 (콘텐츠 생성 관련만) ---
    const contentForm = document.getElementById('contentForm');
    const generateBtn = document.getElementById('generateBtn');
    const spinner = document.getElementById('generateSpinner');
    const resultPlaceholder = document.getElementById('result-placeholder');
    const generatedContentDiv = document.getElementById('generatedContent');
    const copyBtn = document.getElementById('copyBtn');
    const generatedImage = document.getElementById('generatedImage');
    const contentTypeSelect = document.getElementById('contentType');

    // --- 2. 콘텐츠 생성 폼 제출 이벤트 ---
    if (contentForm) {
        contentForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            // [유효성 검사] SNS 이미지 생성 시 주제(프롬프트)가 비어있는지 확인
            const selectedContentTypeValue = contentTypeSelect.value;
            const topicValue = document.getElementById('topic').value;
            if (selectedContentTypeValue === 'sns' && !topicValue.trim()) {
            alert('SNS 콘텐츠를 생성하려면 핵심 주제(이미지 프롬프트)를 반드시 입력해야 합니다.');
            return;
            }
            // 버튼/스피너/결과 초기화 (null 체크 추가)
            if (generateBtn) generateBtn.disabled = true;
            if (spinner) spinner.style.display = 'inline-block';
            if (resultPlaceholder) resultPlaceholder.style.display = 'none';
            if (generatedContentDiv) generatedContentDiv.style.display = 'none';
            if (generatedImage) generatedImage.style.display = 'none';
            if (copyBtn) copyBtn.style.display = 'none';
            if (generatedContentDiv) {
                generatedContentDiv.innerHTML = `
                    <div class="custom-loading-box">
                        <div class="loading-icon">🤖💭</div>
                        <div class="loading-text">[ . . . 결과 생성 중 . . . ]</div>
                    </div>
                `;
                generatedContentDiv.style.display = 'block';
            }
            // 폼 데이터 → payload 변환
            const formData = new FormData(event.target);
            const payload = Object.fromEntries(formData.entries());
            for (const key in payload) {
                if (payload[key] === '') payload[key] = null;
            }
            // SNS 고급 입력값 개수 체크 (프론트 안내)
            if (payload.content_type === 'sns') {
                const advancedFields = ["brand_style_tone", "product_category", "target_audience", "ad_purpose", "key_points"];
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
                    if (generateBtn) generateBtn.disabled = false;
                    if (spinner) spinner.style.display = 'none';
                    return;
                }
            }
            // API URL/필드 분기
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
                if (generateBtn) generateBtn.disabled = false;
                if (spinner) spinner.style.display = 'none';
                if (generatedContentDiv) generatedContentDiv.style.display = 'none';
                if (resultPlaceholder) resultPlaceholder.style.display = 'flex';
                return;
            }
            // 서버 요청
            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const responseData = await response.json();
                if (response.ok) {
                    if (responseData.status === "info") {
                        showGuideMessage(responseData.message);
                        if (generatedContentDiv) generatedContentDiv.style.display = 'none';
                        if (generatedImage) generatedImage.style.display = 'none';
                        if (copyBtn) copyBtn.style.display = 'none';
                        return;
                    }
                    if (payload.content_type === 'sns' && responseData.image_urls && responseData.image_urls.length > 0) {
                        if (generatedImage) {
                            generatedImage.src = responseData.image_urls[0];
                            generatedImage.style.display = 'block';
                        }
                        if (generatedContentDiv) generatedContentDiv.style.display = 'none';
                        if (copyBtn) copyBtn.style.display = 'none';
                    } else if (responseData.content) {
                        let content = responseData.content;
                        content = content.replace(/(✔[^✔\n]*)(?= ✔)/g, '$1<br>');
                        if (generatedContentDiv) {
                            generatedContentDiv.innerHTML = marked.parse(content);
                            generatedContentDiv.style.display = 'block';
                        }
                        if (generatedImage) generatedImage.style.display = 'none';
                        if (copyBtn) copyBtn.style.display = 'inline-block';
                    } else {
                        if (generatedContentDiv) {
                            generatedContentDiv.innerHTML = `<div class="alert alert-warning">콘텐츠가 생성되었지만, 표시할 내용이 없습니다.</div>`;
                            generatedContentDiv.style.display = 'block';
                        }
                    }
                } else {
                    const errorMessage = responseData.error || responseData.message || '알 수 없는 오류';
                    if (generatedContentDiv) {
                        generatedContentDiv.innerHTML = `<div class="alert alert-danger">오류: ${errorMessage}</div>`;
                        generatedContentDiv.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('Fetch error:', error);
                if (generatedContentDiv) {
                    generatedContentDiv.innerHTML = '<div class="alert alert-danger">네트워크 오류가 발생했습니다.</div>';
                    generatedContentDiv.style.display = 'block';
                }
            } finally {
                if (generateBtn) generateBtn.disabled = false;
                if (spinner) spinner.style.display = 'none';
            }
        });
    }

    // --- 3. 클립보드 복사 버튼 이벤트 ---
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            if (!generatedContentDiv) return;
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
    }
});

// --- 4. 안내 메시지(가이드) 모달 함수 ---
function showGuideMessage(message) {
    const modalBody = document.getElementById('guideModalBody');
    modalBody.innerHTML = message;
    const guideModalEl = document.getElementById('guideModal');
    const guideModal = new bootstrap.Modal(guideModalEl);
    guideModal.show();
    guideModalEl.addEventListener('hidden.bs.modal', function handler() {
        // 함수 내에서 다시 DOM 요소 캐싱
        const generatedContentDiv = document.getElementById('generatedContent');
        const generatedImage = document.getElementById('generatedImage');
        const copyBtn = document.getElementById('copyBtn');
        const spinner = document.getElementById('generateSpinner');
        const resultPlaceholder = document.getElementById('result-placeholder');
        const generateBtn = document.getElementById('generateBtn');
        generatedContentDiv.style.display = 'none';
        generatedImage.style.display = 'none';
        copyBtn.style.display = 'none';
        spinner.style.display = 'none';
        resultPlaceholder.style.display = 'flex';
        generateBtn.disabled = false;
        guideModalEl.removeEventListener('hidden.bs.modal', handler);
    });
} 