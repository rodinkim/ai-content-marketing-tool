// utils.js - 공통 유틸 함수 모음

/**
 * 안내/가이드 모달을 표시합니다.
 * @param {string} message - 안내 메시지(HTML 가능)
 * @param {function=} onClose - 모달 닫힐 때 실행할 콜백
 */
export function showGuideMessage(message, onClose) {
    const modalBody = document.getElementById('guideModalBody');
    modalBody.innerHTML = message;
    const guideModalEl = document.getElementById('guideModal');
    const guideModal = new bootstrap.Modal(guideModalEl);
    guideModal.show();
    function handler() {
        if (typeof onClose === 'function') onClose();
        guideModalEl.removeEventListener('hidden.bs.modal', handler);
    }
    guideModalEl.addEventListener('hidden.bs.modal', handler);
}

/**
 * 페이지 상단에 알림/경고 메시지를 표시합니다.
 * @param {string} message - 메시지
 * @param {string} type - success, danger, warning 등
 */
export function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    document.body.prepend(alertDiv);
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(alertDiv)?.close(), 4000);
}

/**
 * fetch 기반 JSON 요청 래퍼
 * @param {string} url
 * @param {object} options
 * @returns {Promise<object>} JSON 응답
 */
export async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || data.message || '요청 실패');
    return data;
} 