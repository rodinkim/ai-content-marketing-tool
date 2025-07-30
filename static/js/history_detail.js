document.addEventListener('DOMContentLoaded', function() {
    // content_id는 서버에서 템플릿 변수로 전달
    const contentId = window.contentId || (typeof content_id !== 'undefined' ? content_id : null) || (typeof contentId !== 'undefined' ? contentId : null) || null;
    if (!contentId) return;
    fetch(`/history-api/${contentId}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('content-title').textContent = data.topic || '제목 없음';
            document.getElementById('content-meta').textContent = data.timestamp ? `생성일: ${formatDate(data.timestamp)}` : '';
            document.getElementById('content-body').textContent = data.generated_text || '';
        })
        .catch(() => {
            document.getElementById('content-body').textContent = '콘텐츠를 불러오는 데 실패했습니다.';
        });

    function formatDate(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        if (isNaN(date)) return isoString;
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        return `${y}.${m}.${d} ${h}:${min}`;
    }
});
