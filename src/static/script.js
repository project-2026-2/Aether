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
document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', saved);
});

// ── Traffic Chart 초기화 ──
const ctx = document.getElementById('trafficChart').getContext('2d');
const labels = Array.from({length: 20}, (_, i) => `${20-i}s`).reverse();
const trafficData = Array(20).fill(0);

const trafficChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels,
        datasets: [{
            label: 'req/s',
            data: trafficData,
            borderColor: '#0071e3',
            backgroundColor: 'rgba(0,113,227,0.08)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        animation: false,
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: { beginAtZero: true, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 } } }
        }
    }
});

// ── /api/stats 폴링 (2초마다) ──
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const d = await res.json();

        // CPU
        document.getElementById('cpu-bar').style.width = d.cpu + '%';
        document.getElementById('cpu-val').innerHTML = `${d.cpu}<span style="font-size:1rem;font-weight:400;">%</span>`;
        document.getElementById('cpu-cores').textContent = `코어 수: ${d.cpu_cores}`;

        // RAM
        document.getElementById('ram-bar').style.width = d.ram + '%';
        document.getElementById('ram-val').innerHTML = `${d.ram}<span style="font-size:1rem;font-weight:400;">%</span>`;
        document.getElementById('ram-detail').textContent =
            `사용: ${d.ram_used_gb}GB / 전체: ${d.ram_total_gb}GB`;

        // 트래픽 차트 슬라이딩
        trafficData.push(d.rps);
        trafficData.shift();
        trafficChart.data.datasets[0].data = [...trafficData];
        trafficChart.update('none');

        // 요청 수 갱신
        document.getElementById('stat-requests').textContent = d.request_count;

    } catch(e) { console.error('stats fetch error', e); }
}

fetchStats();
setInterval(fetchStats, 2000);