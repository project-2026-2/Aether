// 페이지의 모든 HTML 요소가 로드된 후 실행
document.addEventListener('DOMContentLoaded', () => {

    // 1. 테마 토글 로직
    const themeBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const nextTheme = currentTheme === 'light' ? 'dark' : 'light';

            htmlElement.setAttribute('data-bs-theme', nextTheme);
            localStorage.setItem('theme', nextTheme);
            console.log("Theme changed to:", nextTheme); // 디버깅용
        });
    }

    // 2. 저장된 테마 불러오기
    const savedTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-bs-theme', savedTheme);

});

// 3. 상세 모달 열기 함수 (이건 이벤트 리스너 밖에서도 호출 가능해야 함)
function openModal(anime) {
    document.getElementById('m-title').innerText = anime.title.romaji;
    document.getElementById('m-native').innerText = anime.title.native || '';
    document.getElementById('m-cover').src = anime.coverImage.large;
    document.getElementById('m-banner').style.backgroundImage = `url(${anime.bannerImage || anime.coverImage.large})`;
    document.getElementById('m-desc').innerHTML = anime.description || "설명이 없습니다.";
    document.getElementById('m-score').innerText = `⭐ ${anime.averageScore || '??'}%`;
    document.getElementById('m-episodes').innerText = `${anime.episodes || '?'} eps`;
    document.getElementById('m-status').innerText = anime.status;

    const modalElement = document.getElementById('detailModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

// 4. 토스트 알림 함수
function toast(msg, cls) {
    const el = document.getElementById('liveToast');
    const msgBody = document.getElementById('toastMessage');
    if (el && msgBody) {
        msgBody.innerText = msg;
        el.className = `toast align-items-center text-white border-0 ${cls}`;
        new bootstrap.Toast(el).show();
    }
}