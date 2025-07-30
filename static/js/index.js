document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. Hero 섹션 애니메이션 ---
    const heroAnimate = document.querySelector('.hero-animate');
    if (heroAnimate) {
        // 0.1초 후 'show' 클래스를 추가하여 fade-in 애니메이션 시작
        setTimeout(() => {
            heroAnimate.classList.add('show');
        }, 100);
    }

    // Hero 타이틀 타이핑 애니메이션
    const typingEl = document.getElementById('hero-typing');
    if (typingEl) {
        typingEl.textContent = ''; // 시작 전 내용 비우기

        // 텍스트를 세 부분으로 나눔
        const parts = [
            { text: 'AI가 만드는 ', class: 'part1' },
            { text: '당신만의 ', class: 'part2' },
            { text: '마케팅 콘텐츠', class: 'part3' }
        ];
        const typingSpeed = 70;
        let partIndex = 0;
        let charIndex = 0;

        function type() {
            // 모든 파트 타이핑 완료 시 종료
            if (partIndex >= parts.length) return;

            const currentPart = parts[partIndex];
            const currentText = currentPart.text;

            // 현재 파트에 해당하는 span 태그를 찾거나 새로 만듦
            let span = typingEl.querySelector('.' + currentPart.class);
            if (!span) {
                span = document.createElement('span');
                span.className = currentPart.class;
                typingEl.appendChild(span);
            }

            // 글자 타이핑
            if (charIndex < currentText.length) {
                span.textContent += currentText[charIndex];
                charIndex++;
                setTimeout(type, typingSpeed);
            } else {
                // 다음 파트로 이동
                partIndex++;
                charIndex = 0;
                setTimeout(type, typingSpeed + 100); // 파트 사이에 약간의 딜레이
            }
        }

        // 0.4초 후 애니메이션 시작
        setTimeout(type, 400);
    }

    // --- 2. 후기(Testimonials) 자동 캐러셀 애니메이션 ---
    const cards = document.querySelectorAll('.testimonial-carousel .testimonial-card');
    if (cards.length > 0) {
        let cardIdx = 0;
        
        function showCard(i) {
            cards.forEach((card, j) => {
                if (i === j) {
                    card.style.display = 'block';
                    card.classList.add('fade-in');
                } else {
                    card.style.display = 'none';
                    card.classList.remove('fade-in');
                }
            });
        }

        showCard(cardIdx);

        setInterval(() => {
            if (cards[cardIdx]) {
                cards[cardIdx].classList.remove('fade-in');
            }
            cardIdx = (cardIdx + 1) % cards.length;
            showCard(cardIdx);
        }, 3500);
    }
});