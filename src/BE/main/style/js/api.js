'use strict';
/* ════════════════════════════
   api.js — Flask API 통신
   ════════════════════════════ */

const API = '/api';

async function apiFetch(path, opts = {}) {
  try {
    const res  = await fetch(API + path, opts);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'API 오류');
    return data.data;
  } catch (e) {
    const msg = e.message === 'Failed to fetch'
      ? '서버에 연결할 수 없습니다. app.py 를 먼저 실행하세요.'
      : e.message;
    toast(msg, 'error');
    throw e;
  }
}

/* 파일 목록 */
async function apiListFiles({ folderId, trashed, starred, keyword, orderBy, pageSize } = {}) {
  const p = new URLSearchParams({ pageSize: pageSize || 50 });
  if (trashed)  p.set('trashed', 'true');
  if (starred)  p.set('starred', 'true');
  if (folderId) p.set('folderId', folderId);
  if (keyword)  p.set('q', keyword);
  if (orderBy)  p.set('orderBy', orderBy);
  const raw = await apiFetch('/files?' + p);
  return (raw || []).map(normalize);
}

/* 업로드 */
async function apiUpload(file, folderId = null) {
  const fd = new FormData();
  fd.append('file', file);
  if (folderId) fd.append('folderId', folderId);
  return apiFetch('/upload', { method: 'POST', body: fd });
}

/* 파일 수정 (이름·별표·휴지통) */
async function apiUpdate(fileId, body) {
  return apiFetch(`/files/${fileId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/* 영구 삭제 */
async function apiDelete(fileId) {
  return apiFetch(`/files/${fileId}`, { method: 'DELETE' });
}

/* 휴지통 비우기 */
async function apiEmptyTrash() {
  return apiFetch('/trash', { method: 'DELETE' });
}

/* 폴더 생성 */
async function apiCreateFolder(name, parentId = null) {
  return apiFetch('/folders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, parentId }),
  });
}

/* 공유 권한 */
async function apiListPerms(fileId) {
  return apiFetch(`/files/${fileId}/permissions`);
}
async function apiAddPerm(fileId, { email, role, type }) {
  return apiFetch(`/files/${fileId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, role, type: type || 'user' }),
  });
}
async function apiRemovePerm(fileId, permId) {
  return apiFetch(`/files/${fileId}/permissions/${permId}`, { method: 'DELETE' });
}

/* 저장 용량 */
async function apiStorage() {
  return apiFetch('/storage');
}