'use strict';
/* ════════════════════════════
   state.js — 앱 상태 관리
   ════════════════════════════ */

const S = {
  view:        'home',   // home | my-drive | shared | recent | starred | trash | folder
  search:      '',
  gridMode:    true,
  ctxTarget:   null,
  folderStack: [],       // [{id, name}]
  files:       [],       // 현재 뷰 파일 목록
  homeRecent:  [],       // 홈 뷰 최근 파일
};

/* 현재 폴더 ID (folderStack 최상단) */
function currentFolderId() {
  return S.folderStack.length ? S.folderStack[S.folderStack.length - 1].id : null;
}

/* 뷰에 맞는 파일 로드 → S.files, S.homeRecent 채움 */
async function loadViewData() {
  showLoading(true);
  try {
    const opts = { keyword: S.search };

    if (S.view === 'starred')             opts.starred  = true;
    else if (S.view === 'trash')          opts.trashed  = true;
    else if (S.view === 'recent')         opts.orderBy  = 'modifiedTime desc';
    else if (S.view === 'folder')         opts.folderId = currentFolderId();

    S.files = await apiListFiles(opts);

    if (S.view === 'home') {
      try {
        const recent  = await apiListFiles({ orderBy: 'modifiedTime desc', pageSize: 6 });
        S.homeRecent  = recent.filter(f => f.type !== 'folder').slice(0, 6);
      } catch (_) {
        S.homeRecent = S.files.filter(f => f.type === 'file').slice(0, 6);
      }
    }
  } catch (_) {
    S.files = []; S.homeRecent = [];
  } finally {
    showLoading(false);
  }
}