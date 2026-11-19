/* Global keyboard mapping, shared by every port page (a port addition, not in the original games).
 *
 * The games only ever see phone keys: 'LSK', 'OK', 'RSK', '0'..'9', '*', 'RED'. This module turns
 * keyboard keys (KeyboardEvent.code) into phone keys using one mapping, stored in localStorage
 * ('lcdport.keys') and therefore the same in every game and every open tab.
 *
 *   PhoneKeys.listen({down(k, e), up(k, e)})   the page's handlers (e = the KeyboardEvent)
 *   PhoneKeys.open()                           opens the "Keyboard keys" dialog
 *   PhoneKeys.codesFor(k), PhoneKeys.name(code)
 * Any element with [data-open-keymap] opens the dialog; the on-screen keypad buttons (.keys
 * [data-k]) get a small hint with their keyboard keys.
 */
(() => {
  'use strict';
  const STORE = 'lcdport.keys';
  const PHONE = ['LSK', 'OK', 'RSK', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', 'RED'];
  const LABEL = {LSK: '◤ Left soft', OK: 'OK', RSK: 'Right soft ◥', RED: 'End'};
  const DEFAULTS = {
    LSK: ['F1'], OK: ['Enter', 'NumpadEnter'], RSK: ['F2'], RED: ['Escape'], '*': ['NumpadMultiply'],
    1: ['Digit1', 'Numpad1', 'KeyQ'], 2: ['Digit2', 'Numpad2', 'ArrowUp', 'KeyW'], 3: ['Digit3', 'Numpad3', 'KeyE'],
    4: ['Digit4', 'Numpad4', 'ArrowLeft', 'KeyA'], 5: ['Digit5', 'Numpad5', 'KeyS', 'Space'],
    6: ['Digit6', 'Numpad6', 'ArrowRight', 'KeyD'], 7: ['Digit7', 'Numpad7', 'KeyZ'],
    8: ['Digit8', 'Numpad8', 'ArrowDown', 'KeyX'], 9: ['Digit9', 'Numpad9', 'KeyC'], 0: ['Digit0', 'Numpad0'],
  };
  const MODIFIERS = /^(Shift|Control|Alt|Meta|OS|CapsLock|Fn)/;
  const clone = m => Object.fromEntries(PHONE.map(k => [k, (m[k] || []).slice()]));

  const ls = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  function assign(map, k, code) {                      // one keyboard key drives one phone key
    for (const p of PHONE) map[p] = map[p].filter(c => c !== code);
    map[k].push(code);
  }
  function load() {
    const saved = ls.get(STORE);
    if (saved && typeof saved === 'object') {
      const m = clone({});
      for (const k of PHONE) if (Array.isArray(saved[k])) m[k] = saved[k].filter(c => typeof c === 'string');
      return m;
    }
    const m = clone(DEFAULTS);
    // one-time import of keys changed in the old Move the box "Controls" screen (boxport.bindings)
    const old = ls.get('boxport.bindings');
    if (old && typeof old === 'object') {
      const ACT = {up: '2', down: '8', left: '4', right: '6', undo: 'LSK', reset: 'RSK', ok: 'OK', sound: '*', exit: 'RED'};
      const OLD_DEF = {up: ['ArrowUp', 'Digit2', 'Numpad2'], down: ['ArrowDown', 'Digit8', 'Numpad8'],
        left: ['ArrowLeft', 'Digit4', 'Numpad4'], right: ['ArrowRight', 'Digit6', 'Numpad6'], undo: ['KeyQ', 'Backspace', 'F1'],
        reset: ['KeyW', 'F2'], ok: ['Enter', 'Digit5', 'Numpad5'], sound: ['NumpadMultiply'], exit: ['Escape']};
      for (const [a, k] of Object.entries(ACT))
        for (const c of Array.isArray(old[a]) ? old[a] : []) if (!OLD_DEF[a].includes(c)) assign(m, k, c);
    }
    return m;
  }
  let MAP = load();
  const save = () => { ls.set(STORE, MAP); changed(); };

  function name(code) {
    if (/^Key[A-Z]$/.test(code)) return code.slice(3);
    if (/^Digit\d$/.test(code)) return code.slice(5);
    if (/^Numpad\d$/.test(code)) return 'Num ' + code.slice(6);
    return ({ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Escape: 'Esc', Space: 'Space', Enter: 'Enter',
      NumpadEnter: 'Num Enter', NumpadMultiply: 'Num *', NumpadAdd: 'Num +', NumpadSubtract: 'Num −', NumpadDivide: 'Num /',
      NumpadDecimal: 'Num .', Backspace: 'Backspace', Minus: '-', Equal: '=', BracketLeft: '[', BracketRight: ']',
      Semicolon: ';', Quote: "'", Backslash: '\\', Comma: ',', Period: '.', Slash: '/', Backquote: '`', IntlBackslash: '<'})[code] || code;
  }
  function phoneKeyOf(e) {
    for (const k of PHONE) if (MAP[k].includes(e.code)) return k;
    if (e.key === '*' && !PHONE.some(k => MAP[k].includes(e.code))) return '*';   // a typed '*' on any layout
    return null;
  }

  /* ---- dispatch to the page --------------------------------------------------------------- */
  const handlers = [];
  const editable = t => t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
  addEventListener('keydown', e => {
    if (dlg?.open || e.ctrlKey || e.metaKey || e.altKey || editable(e.target)) return;
    const k = phoneKeyOf(e);
    if (!k) return;
    e.preventDefault();
    for (const h of handlers) h.down?.(k, e);
  });
  addEventListener('keyup', e => {
    if (dlg?.open) return;
    const k = phoneKeyOf(e);
    if (k) for (const h of handlers) h.up?.(k, e);
  });

  /* ---- dialog ----------------------------------------------------------------------------- */
  const css = document.createElement('style');
  css.textContent = `
    .keymap { border: 1px solid var(--line, #ccc); border-radius: 16px; padding: 0; width: min(640px, calc(100vw - 32px));
              background: var(--surface, #fff); color: var(--ink, #111); box-shadow: 0 24px 60px rgba(0,0,0,.35); }
    .keymap::backdrop { background: rgba(10, 12, 10, .55); }
    .keymap header { padding: 16px 18px 8px; }
    .keymap h2 { margin: 0; font: 700 17px/1.2 var(--mono, monospace); }
    .keymap header p { margin: 4px 0 0; color: var(--muted, #666); font-size: 13px; }
    .km-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 8px 18px 4px; }
    .km-cell { border: 1px solid var(--line, #ddd); border-radius: 10px; padding: 8px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
    .km-cell.capturing { outline: 2px solid var(--lcd-ink, #1f2a17); outline-offset: 1px; }
    .km-key { align-self: flex-start; background: var(--key, #4a4e55); color: var(--key-ink, #fff); border-radius: 7px;
              padding: 2px 8px; font: 600 12px/1.5 system-ui, sans-serif; }
    .km-key.red { background: var(--key-red, #8f3b36); } .km-key.green { background: var(--key-green, #3d7a46); }
    .km-chips { display: flex; flex-wrap: wrap; gap: 4px; min-height: 22px; align-items: center; }
    .km-chip { display: inline-flex; align-items: center; gap: 2px; font: 11px/1.6 var(--mono, monospace); padding: 0 2px 0 6px;
               border: 1px solid var(--line, #ccc); border-bottom-width: 2px; border-radius: 5px; background: var(--bg, #eee); }
    .km-chip button { border: 0; background: none; color: var(--muted, #666); cursor: pointer; font-size: 13px; line-height: 1; padding: 0 3px; }
    .km-chip button:hover { color: var(--ink, #000); }
    .km-none { color: var(--muted, #888); font-size: 12px; font-style: italic; }
    .km-add { align-self: flex-start; border: 1px dashed var(--line, #bbb); background: none; color: var(--muted, #555); border-radius: 6px;
              font: 12px system-ui, sans-serif; padding: 2px 8px; cursor: pointer; }
    .km-add:hover { color: var(--ink, #000); border-color: var(--muted, #888); }
    .km-cell.capturing .km-add { border-style: solid; color: var(--ink, #000); }
    .keymap footer { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 12px 18px 16px; }
    .keymap footer small { color: var(--muted, #666); }
    .btn { border: 1px solid var(--line, #ccc); background: var(--surface, #fff); color: var(--ink, #111); border-radius: 8px;
           font: 600 13px system-ui, sans-serif; padding: 6px 12px; cursor: pointer; }
    .btn:hover { border-color: var(--muted, #888); }
    .btn.primary { background: var(--lcd-ink, #1f2a17); border-color: var(--lcd-ink, #1f2a17); color: var(--lcd, #c9d3b4); }
    .keys button[data-k] { position: relative; }
    .keys button .kb { position: absolute; right: 7px; bottom: 3px; font: 500 9px/1 var(--mono, monospace); opacity: .55;
                       max-width: calc(100% - 12px); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; pointer-events: none; }
    @media (max-width: 520px) { .km-grid { gap: 6px; padding: 6px 12px 2px; } .km-cell { padding: 6px; } .keymap header, .keymap footer { padding-left: 12px; padding-right: 12px; } }`;
  document.head.appendChild(css);

  let dlg = null, capturing = null;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  function buildDialog() {
    dlg = document.createElement('dialog');
    dlg.className = 'keymap';
    dlg.setAttribute('aria-label', 'Keyboard keys');
    dlg.innerHTML = `<header><h2>Keyboard keys</h2>
      <p>Which keyboard keys press which phone key. One mapping for every game; it is saved in this browser.</p></header>
      <div class="km-grid"></div>
      <footer><button class="btn" data-act="reset">Reset to defaults</button>
        <small class="km-hint">Ctrl, Alt, Shift and ⌘ can't be mapped</small>
        <button class="btn primary" data-act="done">Done</button></footer>`;
    document.body.appendChild(dlg);
    dlg.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) { if (e.target === dlg) close(); return; }          // click on the backdrop
      const act = b.dataset.act, k = b.closest('[data-pk]')?.dataset.pk;
      if (act === 'done') close();
      else if (act === 'reset') { MAP = clone(DEFAULTS); capturing = null; save(); }
      else if (act === 'add') { capturing = capturing === k ? null : k; drawDialog(); }
      else if (act === 'del') { MAP[k] = MAP[k].filter(c => c !== b.dataset.code); save(); }
    });
    dlg.addEventListener('cancel', e => { if (capturing) e.preventDefault(); });   // Esc while capturing: handled below
    dlg.addEventListener('keydown', e => {
      if (!capturing) return;
      e.preventDefault(); e.stopPropagation();
      if (MODIFIERS.test(e.key) || MODIFIERS.test(e.code)) return;  // wait for a real key
      if (e.code === 'Escape' && capturing !== 'RED') { capturing = null; drawDialog(); return; }   // Esc cancels
      assign(MAP, capturing, e.code); capturing = null; save();
    });
    dlg.addEventListener('close', () => { capturing = null; });
  }
  function drawDialog() {
    if (!dlg) return;
    dlg.querySelector('.km-grid').innerHTML = PHONE.map(k => {
      const cls = k === 'RED' ? ' red' : k === 'OK' ? ' green' : '';
      const chips = MAP[k].map(c => `<span class="km-chip">${esc(name(c))}<button data-act="del" data-code="${esc(c)}"
        aria-label="Remove ${esc(name(c))}" title="Remove">×</button></span>`).join('') || '<span class="km-none">no key</span>';
      return `<div class="km-cell${capturing === k ? ' capturing' : ''}" data-pk="${k}"><span class="km-key${cls}">${esc(LABEL[k] || k)}</span>
        <div class="km-chips">${chips}</div>
        <button class="km-add" data-act="add">${capturing === k ? 'Press a key… (Esc: cancel)' : '+ Add key'}</button></div>`;
    }).join('');
    if (capturing) dlg.querySelector('.km-cell.capturing .km-add')?.focus();
  }
  function open() { if (!dlg) buildDialog(); capturing = null; drawDialog(); if (!dlg.open) dlg.showModal(); }
  function close() { capturing = null; dlg?.close(); }

  /* ---- hints on the on-screen keypad, refreshed on every change ---------------------------- */
  function drawHints() {
    document.querySelectorAll('.keys button[data-k]').forEach(b => {
      const k = b.dataset.k;
      const codes = (MAP[k] || []).filter(c => !(c === 'Digit' + k || c === 'Numpad' + k));
      let kb = b.querySelector('.kb');
      if (!codes.length) { kb?.remove(); return; }
      if (!kb) { kb = document.createElement('small'); kb.className = 'kb'; kb.setAttribute('aria-hidden', 'true'); b.appendChild(kb); }
      kb.textContent = codes.slice(0, 2).map(name).join(' ') + (codes.length > 2 ? ' …' : '');
      b.title = `Keyboard: ${(MAP[k] || []).map(name).join(', ') || 'none'}`;
    });
  }
  function changed() { drawHints(); if (dlg?.open) drawDialog(); dispatchEvent(new CustomEvent('phonekeyschange')); }

  document.addEventListener('click', e => { if (e.target.closest?.('[data-open-keymap]')) { e.preventDefault(); open(); } });
  addEventListener('storage', e => { if (e.key === STORE) { MAP = load(); changed(); } });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', drawHints); else drawHints();

  window.PhoneKeys = {
    listen(h) { handlers.push(h); },
    open, close, name,
    codesFor: k => (MAP[k] || []).slice(),
    isOpen: () => !!dlg?.open,
  };
})();
