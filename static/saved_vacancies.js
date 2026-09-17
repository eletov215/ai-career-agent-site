/* Progressive enhancement. Never auto-import or treat local marks as server saves. */
(() => {
  'use strict';
  const key = 'ai-career-agent:saved-vacancies';
  const words = {
    saving: '\u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u043c...',
    saved: '\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e',
    failed: '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u044b\u0445 \u0438\u043b\u0438 \u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435.',
    count: '\u041e\u0442\u043c\u0435\u0442\u043e\u043a \u0432 \u0431\u0440\u0430\u0443\u0437\u0435: ',
    imported: '\u041f\u0435\u0440\u0435\u043d\u0435\u0441\u0435\u043d\u043e: ',
    unresolved: '. \u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e \u043e\u0434\u043d\u043e\u0437\u043d\u0430\u0447\u043d\u043e: ',
    refresh: '. \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u0435 \u0441\u043f\u0438\u0441\u043e\u043a.',
  };
  async function post(form, body) {
    const response = await fetch(form.action, { method:'POST', body,
      credentials:'same-origin', headers:{ Accept:'application/json' }, redirect:'error' });
    let data;
    try { data = await response.json(); } catch (_) { throw new Error(words.failed); }
    if (!response.ok || data.ok !== true) throw new Error(data.error || words.failed);
    return data;
  }
  document.querySelectorAll('[data-server-save]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (form.dataset.busy === '1') return;
      const button = form.querySelector('button[type=submit]');
      const label = button.querySelector('span');
      const oldLabel = label.textContent;
      const status = form.parentElement.querySelector('[data-save-status]');
      form.dataset.busy = '1'; button.disabled = true; label.textContent = words.saving;
      if (status) status.textContent = '';
      try {
        const data = await post(form, new FormData(form));
        const target = new URL(data.url, location.origin);
        if (target.origin !== location.origin || !target.pathname.startsWith('/saved-vacancies/')) throw new Error(words.failed);
        const link = document.createElement('a');
        link.className = 'btn btn-ghost vacancy-save-button is-saved';
        link.href = target.pathname; link.textContent = words.saved;
        form.replaceWith(link);
        if (status) status.textContent = words.saved;
        link.focus();
      } catch (error) {
        if (status) status.textContent = error.message;
        label.textContent = oldLabel;
      } finally { button.disabled = false; form.dataset.busy = '0'; }
    });
  });
  const panel = document.querySelector('[data-legacy-panel]');
  if (!panel) return;
  function load() {
    try {
      const raw = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(raw) ? Array.from(new Set(raw.filter(item => typeof item === 'string' && item.length > 0 && item.length <= 2048))) : [];
    } catch (_) { return []; }
  }
  let marks = load();
  if (!marks.length) return;
  panel.hidden = false;
  panel.querySelector('[data-legacy-count]').textContent = words.count + marks.length;
  const form = panel.querySelector('[data-legacy-form]');
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity() || form.dataset.busy === '1') return;
    marks = load();
    if (!marks.length) { panel.hidden = true; return; }
    const button = form.querySelector('button');
    const result = panel.querySelector('[data-legacy-result]');
    const body = new FormData(form);
    body.set('keys', JSON.stringify(marks.slice(0,50)));
    button.disabled = true; form.dataset.busy = '1';
    try {
      const data = await post(form, body);
      const saved = new Set(Array.isArray(data.saved_keys) ? data.saved_keys : []);
      // Remove only submitted keys acknowledged by the server; retain concurrent additions.
      const acknowledged = new Set(marks.slice(0,50).filter(item => saved.has(item)));
      try { localStorage.setItem(key, JSON.stringify(load().filter(item => !acknowledged.has(item)))); } catch (_) { /* Server data remains saved; replay is idempotent. */ }
      result.textContent = words.imported + data.saved_count + words.unresolved + data.unresolved_count + words.refresh;
      panel.querySelector('[data-legacy-count]').textContent = words.count + load().length;
    } catch (error) { result.textContent = error.message; }
    finally { button.disabled = false; form.dataset.busy = '0'; }
  });
})();
