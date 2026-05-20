'use strict';
/* ════════════════════════════
   app.js — 진입점 & 이벤트 바인딩
   로드 순서: utils → toast → api → state → render
              → actions → upload → modals → context → app
   ════════════════════════════ */

function initializeApp() {
  /* ── 모달·컨텍스트·업로드 초기화 ───────────────────────── */
  initModals();
  initContextMenu();
  initUpload();

  /* ── 사이드바 내비게이션 ────────────────────────────────── */
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      S.view        = item.dataset.view;
      S.folderStack = [];
      S.search      = '';
      document.getElementById('search-input').value = '';
      document.getElementById('search-clear').style.display = 'none';
      render();
    });
  });

  /* ── 사이드바 접기 ──────────────────────────────────────── */
  document.getElementById('sidebar-toggle').addEventListener('click', () =>
    document.getElementById('sidebar').classList.toggle('collapsed'));

  /* ── 그리드 / 리스트 전환 ───────────────────────────────── */
  document.getElementById('btn-view-toggle').addEventListener('click', () => {
    S.gridMode = !S.gridMode;
    document.getElementById('icon-grid').style.display = S.gridMode ? '' : 'none';
    document.getElementById('icon-list').style.display = S.gridMode ? 'none' : '';
    render();
  });

  /* ── 검색 ───────────────────────────────────────────────── */
  document.getElementById('search-input').addEventListener('input', e => {
    S.search = e.target.value;
    document.getElementById('search-clear').style.display = S.search ? '' : 'none';
    if (S.search && S.view === 'home') { S.view = 'my-drive'; setActiveNav('my-drive'); }
    render();
  });
  document.getElementById('search-clear').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    S.search = '';
    document.getElementById('search-clear').style.display = 'none';
    render();
  });

  /* ── 휴지통 비우기 ──────────────────────────────────────── */
  document.getElementById('btn-empty-trash').addEventListener('click', async () => {
    if (!S.files.length) return;
    if (!confirm('휴지통을 완전히 비울까요? 복구할 수 없습니다.')) return;
    await apiEmptyTrash();
    toast('휴지통을 비웠습니다', 'info');
    render();
  });

  /* ── 키보드 단축키 ──────────────────────────────────────── */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
      document.getElementById('context-menu').classList.remove('open');
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault(); document.getElementById('search-input').focus();
    }
    /* Backspace = 상위 폴더로 */
    if (e.key === 'Backspace' && S.view === 'folder' &&
        !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      if (S.folderStack.length > 1) S.folderStack.pop();
      else { S.folderStack = []; S.view = 'my-drive'; }
      render();
    }
  });

  /* ── 첫 렌더 ────────────────────────────────────────────── */
  render();
}

/* DOM이 준비되었을 때 초기화 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  /* 스크립트가 body 끝에 있으면 이미 DOM이 준비된 상태 */
  initializeApp();
}
