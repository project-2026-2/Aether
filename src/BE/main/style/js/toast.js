'use strict';
/* ════════════════════════════
   toast.js — 토스트 알림
   ════════════════════════════ */

function toast(msg, type = 'info', dur = 3000) {
  const el = document.createElement('div');
  el.className  = `toast ${type}`;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  }, dur);
}

/* 진행 중 토스트 (수동 제거) */
function toastProg(msg) {
  const el = document.createElement('div');
  el.className  = 'toast info';
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  return el;
}