// static/js/index.js

// DOM 요소 캐싱
const generatedContentDiv = document.getElementById('generatedContent');
const generateBtn = document.getElementById('generateBtn');
const spinner = generateBtn.querySelector('.spinner-border');
const copyBtn = document.getElementById('copyBtn');
const contentTypeSelect = document.getElementById('contentType');
const emailSubjectField = document.getElementById('emailSubjectField');
const emailSubjectInput = document.getElementById('emailSubject');

// 폼 필드 요소 캐싱
const formFields = {
    topic: document.getElementById('topic'),
    industry: document.getElementById('industry'),
    contentType: document.getElementById('contentType'),
    tone: document.getElementById('tone'),
    length: document.getElementById('length'),
    seoKeywords: document.getElementById('seoKeywords'),
    emailSubject: document.getElementById('emailSubject')
};

// 콘텐츠 종류 변경 이벤트 리스너
contentTypeSelect.addEventListener('change', function() {
    if (this.value === '이메일 뉴스레터') {
        emailSubjectField.style.display = 'block';
    } else {
        emailSubjectField.style.display = 'none';
        emailSubjectInput.value = ''; // 이메일이 아니면 제목 필드 초기화
    }
});

// 초기 로드 시에도 한 번 체크
if (contentTypeSelect.value === '이메일 뉴스레터') {
    emailSubjectField.style.display = 'block';
} else {
    emailSubjectField.style.display = 'none';
}

// history.html에서 전달된 데이터로 폼 채우기 로직 (onload 이벤트 리스너)
window.addEventListener('load', () => {
    const editContentData = localStorage.getItem('editContentData');
    if (editContentData) {
        const item = JSON.parse(editContentData);
        
        // 폼 필드 채우기
        formFields.topic.value = item.topic || '';
        formFields.industry.value = item.industry || '';
        formFields.contentType.value = item.content_type || '';
        formFields.tone.value = item.tone || '';
        formFields.length.value = item.length || '';
        formFields.seoKeywords.value = item.seo_keywords || '';
        
        if (item.content_type === '이메일 뉴스레터') {
            emailSubjectField.style.display = 'block';
            formFields.emailSubject.value = item.email_subject || '';
        } else {
            emailSubjectField.style.display = 'none';
            formFields.emailSubject.value = '';
        }

        // 생성된 콘텐츠 영역에 내용 표시 (marked.parse 사용)
        generatedContentDiv.innerHTML = marked.parse(item.content);
        copyBtn.style.display = 'block'; // 복사 버튼 표시

        // localStorage에서 데이터 제거 (한 번 사용 후)
        localStorage.removeItem('editContentData');
        // 폼으로 스크롤 이동
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
});

// 콘텐츠 생성 폼 제출 이벤트 리스너
document.getElementById('contentForm').addEventListener('submit', async function(event) {
    event.preventDefault();

    generateBtn.disabled = true;
    spinner.style.display = 'inline-block';
    generatedContentDiv.innerHTML = 'AI가 콘텐츠를 생성 중입니다...';
    copyBtn.style.display = 'none';

    // 기존에 표시된 모든 알림 메시지 제거
    document.querySelectorAll('.alert.mt-3').forEach(alert => alert.remove());


    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    
    if (data.content_type !== '이메일 뉴스레터') {
        delete data.email_subject;
    }

    try {
        // 백엔드 URL을 /content/generate_content로 변경
        const response = await fetch('/content/generate_content', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const responseData = await response.json();

        if (response.ok) {
            generatedContentDiv.innerHTML = marked.parse(responseData.content);
            copyBtn.style.display = 'block';

            // Flask flash 메시지와 유사하게 UI에 성공 메시지 표시
            const successMessage = document.createElement('div');
            successMessage.className = 'alert alert-success mt-3';
            successMessage.textContent = '콘텐츠가 성공적으로 생성되고 저장되었습니다!';
            document.querySelector('.main-wrapper').prepend(successMessage);
            setTimeout(() => successMessage.remove(), 5000);

        } else {
            generatedContentDiv.innerHTML = '오류: ' + responseData.error;
            // Flask flash 메시지와 유사하게 UI에 오류 메시지 표시
            const errorMessage = document.createElement('div');
            errorMessage.className = 'alert alert-danger mt-3';
            errorMessage.textContent = responseData.error || '콘텐츠 생성 중 알 수 없는 오류 발생.';
            document.querySelector('.main-wrapper').prepend(errorMessage);
            setTimeout(() => errorMessage.remove(), 5000);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        generatedContentDiv.innerHTML = '네트워크 오류가 발생했습니다.';
        // Flask flash 메시지와 유사하게 UI에 오류 메시지 표시
        const networkErrorMessage = document.createElement('div');
        networkErrorMessage.className = 'alert alert-danger mt-3';
        networkErrorMessage.textContent = '네트워크 오류가 발생했습니다. 인터넷 연결을 확인해주세요.';
        document.querySelector('.main-wrapper').prepend(networkErrorMessage);
        setTimeout(() => networkErrorMessage.remove(), 5000);
    } finally {
        generateBtn.disabled = false;
        spinner.style.display = 'none';
    }
});

// 클립보드에 복사 버튼 이벤트 리스너
document.getElementById('copyBtn').addEventListener('click', function() {
    const content = generatedContentDiv.innerText;
    navigator.clipboard.writeText(content)
        .then(() => alert('클립보드에 복사되었습니다!'))
        .catch(err => console.error('복사 실패:', err));
});