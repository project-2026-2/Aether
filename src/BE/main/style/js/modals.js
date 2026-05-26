'use strict';
/* ════════════════════════════
   modals.js — 모달 관리
   ════════════════════════════ */

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

/* ── 공통 초기화 ─────────────────────────────────────────── */
function initModals() {
  /* [data-close] 버튼 */
  document.querySelectorAll('[data-close]').forEach(btn =>
    btn.addEventListener('click', () => closeModal(btn.dataset.close)));

  /* 오버레이 클릭 닫기 */
  document.querySelectorAll('.modal-overlay').forEach(ov =>
    ov.addEventListener('click', e => { if (e.target === ov) closeModal(ov.id); }));

  initRenameModal();
  initFolderModal();
  initNewFileModal();
  initShareModal();
  initNewDropdown();
}

/* ── 이름 변경 ───────────────────────────────────────────── */
function openRenameModal(file) {
  const input = document.getElementById('rename-input');
  input.value = file.name;
  openModal('modal-rename');
  setTimeout(() => input.select(), 50);

  document.getElementById('btn-rename-confirm').onclick = async () => {
    const name = input.value.trim();
    if (!name) return;
    await apiUpdate(file.id, { name });
    closeModal('modal-rename');
    toast('이름이 변경됐습니다', 'success');
    render();
  };
}

function initRenameModal() {
  document.getElementById('rename-input').addEventListener('keydown', e => {
    if (e.key === 'Enter')  document.getElementById('btn-rename-confirm').click();
    if (e.key === 'Escape') closeModal('modal-rename');
  });
}

/* ── 새 폴더 ─────────────────────────────────────────────── */
function initFolderModal() {
  document.getElementById('btn-folder-confirm').addEventListener('click', async () => {
    const name = document.getElementById('folder-name-input').value.trim();
    if (!name) return;
    await apiCreateFolder(name, currentFolderId());
    closeModal('modal-folder');
    if (!['my-drive', 'folder'].includes(S.view)) { S.view = 'my-drive'; setActiveNav('my-drive'); }
    toast(`"${name}" 폴더가 생성됐습니다`, 'success');
    render();
  });
  document.getElementById('folder-name-input').addEventListener('keydown', e => {
    if (e.key === 'Enter')  document.getElementById('btn-folder-confirm').click();
    if (e.key === 'Escape') closeModal('modal-folder');
  });
}

/* ── 새 파일 (문서/시트/슬라이드) ───────────────────────── */
let _newFileType = null;

function initNewFileModal() {
  document.getElementById('btn-newfile-confirm').addEventListener('click', async () => {
    const rawName = document.getElementById('newfile-name-input').value.trim();
    if (!rawName || !_newFileType) return;
    const meta = TYPE_META[_newFileType];
    const name = rawName.includes('.') ? rawName : rawName + meta.ext;
    const blob = new Blob([''], { type: meta.mime || 'text/plain' });
    const file = new File([blob], name, { type: meta.mime });
    await apiUpload(file, currentFolderId());
    closeModal('modal-newfile');
    if (!['my-drive', 'folder'].includes(S.view)) { S.view = 'my-drive'; setActiveNav('my-drive'); }
    toast(`"${name}"이(가) 생성됐습니다`, 'success');
    render(); _newFileType = null;
  });
  document.getElementById('newfile-name-input').addEventListener('keydown', e => {
    if (e.key === 'Enter')  document.getElementById('btn-newfile-confirm').click();
    if (e.key === 'Escape') closeModal('modal-newfile');
  });
}

/* ── 새로 만들기 드롭다운 ────────────────────────────────── */
function initNewDropdown() {
  const btnNew  = document.getElementById('btn-new');
  const dropdown = document.getElementById('new-dropdown');

  // Defensive checks: if elements are not present yet, delay initialization
  if (!btnNew || !dropdown) {
    // Try again shortly; this avoids throwing when called before DOM is ready.
    setTimeout(initNewDropdown, 50);
    return;
  }

  btnNew.addEventListener('click', e => {
    e.stopPropagation();
    btnNew.classList.toggle('open');
    dropdown.classList.toggle('open');
  });
  document.addEventListener('click', () => {
    btnNew.classList.remove('open'); dropdown.classList.remove('open');
  });

  dropdown.addEventListener('click', e => {
    const btn = e.target.closest('[data-new]');
    if (!btn) return;
    e.stopPropagation();
    btnNew.classList.remove('open'); dropdown.classList.remove('open');

    const type = btn.dataset.new;
    if (type === 'upload') {
      document.getElementById('file-input').click();
    } else if (type === 'folder') {
      document.getElementById('folder-name-input').value = '새 폴더';
      openModal('modal-folder');
      setTimeout(() => document.getElementById('folder-name-input').select(), 50);
    } else {
      _newFileType = type;
      const meta = TYPE_META[type];
      document.getElementById('newfile-title').textContent     = meta.name + ' 만들기';
      document.getElementById('newfile-name-input').value      = '제목 없는 ' + meta.name;
      openModal('modal-newfile');
      setTimeout(() => document.getElementById('newfile-name-input').select(), 50);
    }
  });
}

/* ── 공유 모달 ───────────────────────────────────────────── */
let _shareFile = null;

async function openShareModal(file) {
  _shareFile = file;
  document.getElementById('chk-link-share').checked  = file.shared;
  document.getElementById('share-link-input').value  = file.shared && file.webViewLink ? file.webViewLink : '';
  document.getElementById('share-email-input').value = '';
  openModal('modal-share');
  await renderPerms(file.id);
}

async function renderPerms(fileId) {
  const el    = document.getElementById('perm-list');
  el.innerHTML = '';
  try {
    const perms = await apiListPerms(fileId);
    if (!perms.length) {
      el.innerHTML = '<div style="color:var(--text-3);font-size:12px;padding:8px 0">공유된 사용자가 없습니다</div>';
      return;
    }
    const labels = { reader:'보기', commenter:'댓글', writer:'편집' };
    perms.forEach(p => {
      const row   = document.createElement('div');
      row.className = 'perm-item';
      const label = p.emailAddress || p.displayName || p.type;
      row.innerHTML = `
        <span class="perm-email">${esc(label)}</span>
        <span class="perm-role">${labels[p.role] || p.role}</span>
        <button class="perm-rm" data-pid="${p.id}">×</button>`;
      el.appendChild(row);
    });
    el.querySelectorAll('.perm-rm').forEach(btn =>
      btn.addEventListener('click', async () => {
        await apiRemovePerm(fileId, btn.dataset.pid);
        toast('권한이 제거됐습니다', 'info');
        renderPerms(fileId);
      }));
  } catch (_) {}
}

function initShareModal() {
  document.getElementById('chk-link-share').addEventListener('change', async () => {
    if (!_shareFile) return;
    if (document.getElementById('chk-link-share').checked) {
      await apiAddPerm(_shareFile.id, { type: 'anyone', role: 'reader' });
      document.getElementById('share-link-input').value =
        _shareFile.webViewLink || `${location.origin}${API}/download/${_shareFile.id}`;
      toast('링크 공유가 활성화됐습니다', 'success');
      renderPerms(_shareFile.id);
    } else {
      document.getElementById('share-link-input').value = '';
      toast('링크 공유가 비활성화됐습니다', 'info');
    }
  });

  document.getElementById('btn-copy-link').addEventListener('click', () => {
    const v = document.getElementById('share-link-input').value;
    if (!v) { toast('먼저 링크 공유를 활성화하세요', 'warn'); return; }
    navigator.clipboard.writeText(v).catch(() => {});
    toast('링크가 복사됐습니다', 'success');
  });

  document.getElementById('btn-share-add').addEventListener('click', async () => {
    const email = document.getElementById('share-email-input').value.trim();
    const role  = document.getElementById('share-role-select').value;
    if (!email || !_shareFile) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { toast('유효한 이메일을 입력하세요', 'error'); return; }
    await apiAddPerm(_shareFile.id, { email, role, type: 'user' });
    document.getElementById('share-email-input').value = '';
    toast(`${email}에게 공유됐습니다`, 'success');
    renderPerms(_shareFile.id);
  });
}

/* ── 미리보기 모달 ───────────────────────────────────────── */
function openPreviewModal(file) {
  document.getElementById('preview-icon-lg').textContent = getIcon(file);
  document.getElementById('preview-name').textContent    = file.name;
  document.getElementById('preview-meta').textContent    = `${fmtSize(file.size)} · ${fmtDate(file.createdAt)}`;

  const ext = getExt(file);
  let body = '';
  if (['png','jpg','jpeg','gif','webp'].includes(ext))
    body = `<span style="font-size:48px">🖼️</span><span>Google Drive에서 이미지 미리보기 가능합니다</span>`;
  else if (ext === 'pdf')
    body = `<span style="font-size:48px">📄</span><span style="color:var(--text-2)">${esc(file.name)}</span>`;
  else
    body = `<span style="font-size:42px">${getIcon(file)}</span>
            <span style="color:var(--text-2)">${esc(file.name)}</span>
            <span>${fmtSize(file.size)}</span>`;

  document.getElementById('preview-body').innerHTML = body;
  document.getElementById('preview-dl').onclick = () => {
    window.location.href = `${API}/download/${file.id}`;
    closeModal('modal-preview');
  };
  openModal('modal-preview');
}