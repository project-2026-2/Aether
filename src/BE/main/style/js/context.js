'use strict';
/* ════════════════════════════
   context.js — 컨텍스트 메뉴
   ════════════════════════════ */

function initContextMenu() {
  const menu = document.getElementById('context-menu');

  /* 열기 */
  function openCtx(e, file) {
    e.preventDefault();
    S.ctxTarget = file;
    const inTrash = S.view === 'trash';
    menu.querySelector('[data-action="trash"]').style.display   = inTrash ? 'none' : '';
    menu.querySelector('[data-action="restore"]').style.display = inTrash ? '' : 'none';
    menu.querySelector('[data-action="delete"]').style.display  = inTrash ? '' : 'none';
    document.getElementById('ctx-star-label').textContent =
      file.starred ? '즐겨찾기 해제' : '즐겨찾기 추가';

    menu.style.left = Math.min(e.clientX, innerWidth  - 190) + 'px';
    menu.style.top  = Math.min(e.clientY, innerHeight - 300) + 'px';
    menu.classList.add('open');
  }

  /* 전역 openCtx (render.js에서 카드 이벤트에 사용) */
  window.openCtx = openCtx;

  function closeCtx() { menu.classList.remove('open'); S.ctxTarget = null; }

  /* 액션 클릭 */
  menu.addEventListener('click', async e => {
    const btn = e.target.closest('[data-action]');
    if (!btn || !S.ctxTarget) return;
    const file = S.ctxTarget, action = btn.dataset.action;
    closeCtx();

    if (action === 'open')    handleOpen(file);
    if (action === 'download') handleDownload(file);
    if (action === 'rename')  openRenameModal(file);
    if (action === 'star')    await handleStar(file);
    if (action === 'share')   openShareModal(file);
    if (action === 'trash')   await handleTrash(file);
    if (action === 'restore') await handleRestore(file);
    if (action === 'delete')  await handleDelete(file);
    if (action === 'copy') {
      toast('복사본 만들기는 Google Drive에서 지원됩니다', 'info');
    }
  });

  document.addEventListener('click', e => {
    if (!menu.contains(e.target)) closeCtx();
  });
}