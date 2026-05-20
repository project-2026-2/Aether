'use strict';
/* ════════════════════════════
   actions.js — 파일 액션
   ════════════════════════════ */

/* ── 파일 열기 (더블클릭) ───────────────────────────────── */
function handleOpen(file) {
  if (file.type === 'folder') {
    S.folderStack.push({ id: file.id, name: file.name });
    S.view = 'folder';
    setActiveNav('my-drive');
    render();
    return;
  }
  if (file.webViewLink) window.open(file.webViewLink, '_blank');
  else openPreviewModal(file);
}

/* ── 별표 토글 ──────────────────────────────────────────── */
async function handleStar(file) {
  await apiUpdate(file.id, { starred: !file.starred });
  toast(file.starred ? '즐겨찾기에서 제거됐습니다' : '즐겨찾기에 추가됐습니다', 'info');
  render();
}

/* ── 휴지통 이동 ────────────────────────────────────────── */
async function handleTrash(file) {
  await apiUpdate(file.id, { trashed: true });
  toast(`"${file.name}"을(를) 휴지통으로 이동했습니다`, 'info');
  render();
}

/* ── 복원 ───────────────────────────────────────────────── */
async function handleRestore(file) {
  await apiUpdate(file.id, { trashed: false });
  toast(`"${file.name}"이(가) 복원됐습니다`, 'success');
  render();
}

/* ── 영구 삭제 ──────────────────────────────────────────── */
async function handleDelete(file) {
  if (!confirm(`"${file.name}"을(를) 영구 삭제할까요?\n이 작업은 되돌릴 수 없습니다.`)) return;
  await apiDelete(file.id);
  toast(`"${file.name}"이(가) 영구 삭제됐습니다`, 'error');
  render();
}

/* ── 다운로드 ───────────────────────────────────────────── */
function handleDownload(file) {
  window.location.href = `${API}/download/${file.id}`;
  toast(`"${file.name}" 다운로드 시작`, 'success');
}