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
        const text1 = 'AI가 만드는 ';
        const text2 = '당신만의 마케팅 콘텐츠';
        const typingSpeed = 70;
        let idx1 = 0; // 변수 이름 충돌 방지를 위해 idx1으로 변경
        let idx2 = 0;

        typingEl.textContent = '';

        function typeFirst() {
            if (idx1 < text1.length) {
                typingEl.textContent += text1[idx1];
                idx1++;
                setTimeout(typeFirst, typingSpeed);
            } else {
                const highlight = document.createElement('span');
                highlight.className = 'highlight';
                typingEl.appendChild(highlight);
                setTimeout(() => typeSecond(highlight), 100);
            }
        }

        function typeSecond(highlight) {
            if (idx2 < text2.length) {
                highlight.textContent += text2[idx2];
                idx2++;
                setTimeout(() => typeSecond(highlight), typingSpeed);
            }
        }
        setTimeout(typeFirst, 400);
    }

    // --- 2. 후기(Testimonials) 자동 캐러셀 애니메이션 ---
    const cards = document.querySelectorAll('.testimonial-carousel .testimonial-card');
    if (cards.length > 0) {
        let cardIdx = 0; // 변수 이름 충돌 방지를 위해 cardIdx로 변경
        
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