'use strict';
/* ════════════════════════════
   render.js — 화면 렌더링
   ════════════════════════════ */

const VIEW_TITLES = {
  home:'홈', 'my-drive':'내 드라이브', shared:'공유 문서함',
  recent:'최근 문서함', starred:'즐겨찾기', trash:'휴지통',
};

async function render() {
  await loadViewData();
  updateNav();
  updateBreadcrumb();
  updateSectionTitle();
  updateTrashBtn();
  loadStorageBar();

  if (S.view === 'home') {
    document.getElementById('view-home').style.display  = '';
    document.getElementById('view-files').style.display = 'none';
    renderHome();
  } else {
    document.getElementById('view-home').style.display  = 'none';
    document.getElementById('view-files').style.display = '';
    renderFileView();
  }
}

/* ── 홈 뷰 ──────────────────────────────────────────────── */
function renderHome() {
  const recentGrid  = document.getElementById('recent-grid');
  const recentEmpty = document.getElementById('recent-empty');
  recentGrid.innerHTML = '';

  if (!S.homeRecent.length) {
    recentEmpty.style.display = '';
  } else {
    recentEmpty.style.display = 'none';
    S.homeRecent.forEach(file => {
      const card = document.createElement('div');
      card.className = 'recent-card';
      card.innerHTML = `
        <span class="rc-icon">${getIcon(file)}</span>
        <div class="rc-info">
          <div class="rc-name" title="${esc(file.name)}">${esc(file.name)}</div>
          <div class="rc-time">${fmtDate(file.createdAt)}</div>
        </div>`;
      card.addEventListener('click',       () => handleOpen(file));
      card.addEventListener('contextmenu', e  => openCtx(e, file));
      recentGrid.appendChild(card);
    });
  }

  const hg = document.getElementById('home-file-grid');
  hg.innerHTML = '';
  hg.className = S.gridMode ? 'file-grid' : 'file-grid list-view';
  S.files.slice(0, 8).forEach((f, i) =>
    hg.appendChild(S.gridMode ? buildCard(f, i) : buildRow(f, i)));
}

/* ── 파일 뷰 ────────────────────────────────────────────── */
function renderFileView() {
  const grid    = document.getElementById('file-grid');
  const empty   = document.getElementById('empty-state');
  const listHdr = document.getElementById('list-header');

  grid.innerHTML = '';
  grid.className = S.gridMode ? 'file-grid' : 'file-grid list-view';
  listHdr.style.display = S.gridMode ? 'none' : 'flex';

  if (!S.files.length) {
    empty.style.display = 'flex';
    document.getElementById('empty-hint').textContent = S.view === 'trash'
      ? '휴지통이 비어 있습니다' : '새로 만들기로 파일을 추가해 보세요';
    return;
  }
  empty.style.display = 'none';
  S.files.forEach((f, i) =>
    grid.appendChild(S.gridMode ? buildCard(f, i) : buildRow(f, i)));
}

/* ── 카드 (그리드) ──────────────────────────────────────── */
function buildCard(file, idx) {
  const div = document.createElement('div');
  div.className = 'file-card';
  div.dataset.id = file.id;
  div.style.animationDelay = (idx * 0.025) + 's';
  div.innerHTML = `
    <div class="fc-icon" style="background:${getBg(file)}">${getIcon(file)}</div>
    <div class="fc-name" title="${esc(file.name)}">${esc(file.name)}</div>
    <div class="fc-meta">${fmtSize(file.size)}</div>
    ${file.starred ? '<span class="fc-star">★</span>' : ''}
    ${file.shared  ? `<span class="fc-shared">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>
        <circle cx="18" cy="19" r="3"/>
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
      </svg></span>` : ''}`;
  div.addEventListener('dblclick',    () => handleOpen(file));
  div.addEventListener('contextmenu', e  => openCtx(e, file));
  return div;
}

/* ── 로우 (리스트) ──────────────────────────────────────── */
function buildRow(file, idx) {
  const div = document.createElement('div');
  div.className = 'file-row';
  div.dataset.id = file.id;
  div.style.animationDelay = (idx * 0.018) + 's';
  div.innerHTML = `
    <span class="fr-icon">${getIcon(file)}</span>
    <span class="fr-name" title="${esc(file.name)}">${esc(file.name)}</span>
    ${file.starred ? '<span class="fr-star">★</span>' : ''}
    <span class="fr-date">${fmtDate(file.createdAt)}</span>
    <span class="fr-size">${fmtSize(file.size)}</span>`;
  div.addEventListener('dblclick',    () => handleOpen(file));
  div.addEventListener('contextmenu', e  => openCtx(e, file));
  return div;
}

/* ── 네비 활성화 ─────────────────────────────────────────── */
function updateNav() {
  const active = S.view === 'folder' ? 'my-drive' : S.view;
  document.querySelectorAll('.nav-item').forEach(el =>
    el.classList.toggle('active', el.dataset.view === active));
}
function setActiveNav(v) {
  document.querySelectorAll('.nav-item').forEach(el =>
    el.classList.toggle('active', el.dataset.view === v));
}

/* ── 브레드크럼 ──────────────────────────────────────────── */
function updateBreadcrumb() {
  const bc = document.getElementById('breadcrumb');
  if (S.view !== 'folder' || !S.folderStack.length) { bc.style.display = 'none'; return; }
  bc.style.display = 'flex';

  document.getElementById('bc-root').onclick = () => {
    S.folderStack = []; S.view = 'my-drive'; setActiveNav('my-drive'); render();
  };

  const list = document.getElementById('bc-list');
  list.innerHTML = '';
  S.folderStack.forEach((item, i) => {
    const sep = document.createElement('span'); sep.className = 'bc-sep'; sep.textContent = '›';
    list.appendChild(sep);
    if (i === S.folderStack.length - 1) {
      const cur = document.createElement('span'); cur.className = 'bc-current'; cur.textContent = item.name;
      list.appendChild(cur);
    } else {
      const span = document.createElement('span'); span.className = 'bc-item'; span.textContent = item.name;
      span.onclick = () => { S.folderStack = S.folderStack.slice(0, i + 1); S.view = 'folder'; render(); };
      list.appendChild(span);
    }
  });
}

/* ── 섹션 제목 ───────────────────────────────────────────── */
function updateSectionTitle() {
  const folderName = S.folderStack.length ? S.folderStack[S.folderStack.length - 1].name : '내 드라이브';
  const title = S.search
    ? `검색 결과: "${S.search}"`
    : (VIEW_TITLES[S.view] || folderName);
  document.getElementById('section-title').textContent = title;
}

function updateTrashBtn() {
  document.getElementById('trash-actions').style.display =
    S.view === 'trash' && S.files.length ? '' : 'none';
}

/* ── 로딩 스피너 ─────────────────────────────────────────── */
function showLoading(on) {
  const el = document.getElementById('loading');
  if (el) el.style.display = on ? 'flex' : 'none';
}

/* ── 저장 용량 바 ────────────────────────────────────────── */
async function loadStorageBar() {
  try {
    const s   = await apiStorage();
    const pct = s.total ? Math.min(s.used / s.total * 100, 100) : 0;
    document.getElementById('storage-fill').style.width      = pct.toFixed(1) + '%';
    document.getElementById('storage-used-text').textContent = fmtSize(s.used);
    if (s.displayName)
      document.querySelector('.user-avatar').textContent = s.displayName.charAt(0).toUpperCase();
  } catch (_) {}
}