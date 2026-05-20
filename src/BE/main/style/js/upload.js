'use strict';
/* ════════════════════════════
   upload.js — 업로드 & 드래그앤드롭
   ════════════════════════════ */

async function uploadFiles(fileList) {
  const folderId = currentFolderId();
  for (const file of Array.from(fileList)) {
    const t = toastProg(`⬆️ "${file.name}" 업로드 중…`);
    try {
      await apiUpload(file, folderId);
      t.remove();
      toast(`✅ "${file.name}" 업로드 완료`, 'success');
    } catch (_) { t.remove(); }
  }
  if (!['my-drive', 'folder'].includes(S.view)) {
    S.view = 'my-drive'; setActiveNav('my-drive');
  }
  render();
}

function initUpload() {
  /* 파일 선택 버튼 */
  document.getElementById('file-input').addEventListener('change', e => {
    if (e.target.files.length) uploadFiles(e.target.files);
    e.target.value = '';
  });

  /* 드래그앤드롭 */
  const dropZone = document.getElementById('drop-zone');
  let dragCnt = 0;

  document.addEventListener('dragenter', e => {
    e.preventDefault(); dragCnt++;
    dropZone.classList.add('active');
  });
  document.addEventListener('dragleave', () => {
    if (!--dragCnt) { dragCnt = 0; dropZone.classList.remove('active', 'dragover'); }
  });
  document.addEventListener('dragover', e => {
    e.preventDefault(); dropZone.classList.add('dragover');
  });
  document.addEventListener('drop', async e => {
    e.preventDefault(); dragCnt = 0;
    dropZone.classList.remove('active', 'dragover');
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  });
}