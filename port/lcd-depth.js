/* LCD depth effect, shared by all the port pages (not part of the original games).
 *
 * Passive monochrome LCDs show a faint shadow of every dark pixel a little below and to the
 * right of it, because the liquid-crystal layer sits slightly above the reflective back.
 * This adds that look on top of the page's 101x64 canvas#lcd without touching its rendering:
 * every frame the dark pixels are copied into a second, transparent canvas, drawn in a soft,
 * translucent ink colour, nudged by a fraction of an LCD pixel and slightly blurred.
 * The HTML text screens (menus, texts, soft-key labels) get the same look via text-shadow.
 *
 * On/off is shared by every page (localStorage 'lcdport.depth'); a checkbox is added under
 * the phone and window.LcdDepth.{get,set,toggle} lets a page offer it in its own menus.
 */
(() => {
  'use strict';
  const KEY = 'lcdport.depth';
  const OFFSET = 0.6;          // shadow offset in LCD pixels (down and right)
  const ALPHA = 0.38;          // shadow strength for a fully dark pixel
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) ?? true; } catch { return true; } };
  const save = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch {} };

  const src = document.getElementById('lcd');
  if (!src || !src.parentElement) return;
  const css = document.createElement('style');
  css.textContent = `
    .lcd-shadow { position: absolute; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none;
                  image-rendering: pixelated; image-rendering: crisp-edges; filter: blur(0.2px); display: none;
                  transform: translate(${OFFSET / 101 * 100}%, ${OFFSET / 64 * 100}%); }
    html.lcd-depth .lcd-shadow { display: block; }
    html.lcd-depth .screen .overlay, html.lcd-depth .lcd .soft { text-shadow: 0.1em 0.13em 0.02em rgba(20, 28, 14, .38); }
    html.lcd-depth .screen .overlay .hdr, html.lcd-depth .screen .overlay li.sel { box-shadow: 0.1em 0.13em 0.02em rgba(20, 28, 14, .36); }
    html.lcd-depth .screen .overlay .hdr, html.lcd-depth .screen .overlay li.sel { text-shadow: none; }
    .lcd-depth-toggle { margin-top: 10px; font-size: 12px; color: var(--muted, #777); display: flex; gap: 6px; align-items: center; cursor: pointer; user-select: none; }`;
  document.head.appendChild(css);

  const sh = document.createElement('canvas');
  sh.className = 'lcd-shadow';
  sh.setAttribute('aria-hidden', 'true');
  src.after(sh);                                     // above the game canvas, below the text overlay
  const sx = src.getContext('2d', {willReadFrequently: true}), dx = sh.getContext('2d');
  let on = load(), img = null;

  function frame() {
    if (on) {
      const w = src.width, h = src.height;
      if (sh.width !== w || sh.height !== h || !img) { sh.width = w; sh.height = h; img = dx.createImageData(w, h); }
      const s = sx.getImageData(0, 0, w, h).data, d = img.data;
      // reference for "empty": the lightest pixel of the frame (the LCD background colour)
      let bg = 0;
      for (let i = 0; i < s.length; i += 4) { const l = s[i] * 0.3 + s[i + 1] * 0.59 + s[i + 2] * 0.11; if (l > bg) bg = l; }
      for (let i = 0; i < s.length; i += 4) {
        const l = s[i] * 0.3 + s[i + 1] * 0.59 + s[i + 2] * 0.11;
        const dark = bg > 0 ? Math.max(0, Math.min(1, (bg - l) / (bg * 0.6))) : 0;
        d[i] = 20; d[i + 1] = 28; d[i + 2] = 14; d[i + 3] = Math.round(dark * ALPHA * 255);
      }
      dx.putImageData(img, 0, 0);
    }
    requestAnimationFrame(frame);
  }

  const box = document.createElement('label');
  box.className = 'lcd-depth-toggle';
  box.innerHTML = '<input type="checkbox"> LCD depth (pixel shadow)';
  const cb = box.querySelector('input');
  // keep the checkbox from stealing the game keys (Enter/Space would toggle it)
  cb.addEventListener('keydown', e => e.preventDefault());
  cb.addEventListener('change', () => { set(cb.checked); cb.blur(); });
  (document.querySelector('.phone') || src.parentElement).after(box);

  function set(v) {
    on = !!v; save(on); cb.checked = on;
    document.documentElement.classList.toggle('lcd-depth', on);
    dispatchEvent(new CustomEvent('lcddepthchange', {detail: on}));
  }
  window.LcdDepth = { get: () => on, set, toggle: () => set(!on) };
  addEventListener('storage', e => { if (e.key === KEY) set(load()); });
  set(on);
  requestAnimationFrame(frame);
})();
