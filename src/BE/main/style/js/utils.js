'use strict';
/* ════════════════════════════
   utils.js — 아이콘·포맷·유틸
   ════════════════════════════ */

const EXT_ICON = {
  folder:'📁', pdf:'📄', doc:'📝', docx:'📝', xls:'📊', xlsx:'📊',
  ppt:'📋', pptx:'📋', png:'🖼️', jpg:'🖼️', jpeg:'🖼️', gif:'🖼️',
  webp:'🖼️', svg:'🎨', mp4:'🎬', mov:'🎬', avi:'🎬', mp3:'🎵',
  wav:'🎵', zip:'🗜️', rar:'🗜️', tar:'🗜️', js:'⚡', ts:'⚡',
  py:'🐍', json:'📋', html:'🌐', css:'🎨', txt:'📃', md:'📃',
  default:'📄',
};

const EXT_BG = ext => ({
  folder:'rgba(68,136,255,.16)',  pdf:'rgba(255,85,102,.14)',
  xls:'rgba(34,221,170,.13)',     xlsx:'rgba(34,221,170,.13)',
  png:'rgba(34,221,170,.13)',     jpg:'rgba(34,221,170,.13)',
  jpeg:'rgba(34,221,170,.13)',    gif:'rgba(34,221,170,.13)',
  mp4:'rgba(255,170,51,.14)',     mov:'rgba(255,170,51,.14)',
  py:'rgba(68,136,255,.13)',
}[ext] || 'rgba(255,255,255,.05)');

const TYPE_META = {
  doc:   { name:'문서',         ext:'.doc',  mime:'application/msword' },
  sheet: { name:'스프레드시트', ext:'.xlsx', mime:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  slide: { name:'프레젠테이션', ext:'.pptx', mime:'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
};

/* API 파일 객체 → 내부 포맷 */
function normalize(f) {
  const name = f.name || '';
  const ext  = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
  return {
    id:          f.id,
    name,
    type:        f.mimeType === 'application/vnd.google-apps.folder' ? 'folder' : 'file',
    mimeType:    f.mimeType || '',
    size:        f.size ? parseInt(f.size) : 0,
    starred:     !!f.starred,
    shared:      !!f.shared,
    createdAt:   f.modifiedTime ? new Date(f.modifiedTime).getTime() : Date.now(),
    webViewLink: f.webViewLink || null,
    _ext: ext,
  };
}

function getExt(file)  { return file._ext || (file.type === 'folder' ? 'folder' : 'default'); }
function getIcon(file) { return EXT_ICON[getExt(file)] || EXT_ICON.default; }
function getBg(file)   { return EXT_BG(getExt(file)); }

function fmtSize(b) {
  if (!b) return '-';
  if (b < 1024)    return b + ' B';
  if (b < 1 << 20) return (b / 1024).toFixed(1) + ' KB';
  if (b < 1 << 30) return (b / (1 << 20)).toFixed(1) + ' MB';
  return (b / (1 << 30)).toFixed(2) + ' GB';
}

function fmtDate(ts) {
  if (!ts) return '-';
  const diff = Date.now() - ts;
  if (diff < 60000)        return '방금 전';
  if (diff < 3600000)      return Math.floor(diff / 60000) + '분 전';
  if (diff < 86400000)     return Math.floor(diff / 3600000) + '시간 전';
  if (diff < 86400000 * 7) return Math.floor(diff / 86400000) + '일 전';
  return new Date(ts).toLocaleDateString('ko-KR', { month:'short', day:'numeric' });
}

function esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                  .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}