/* Shared page chrome for the port pages: site header with navigation, footer, page title.
 * Game names come from out/games/menu.json (the phone's own Games menu, extracted from your dump);
 * the fallbacks are my own wording, used only when that file is missing. */
(() => {
  'use strict';
  const PAGES = [
    {file: 'games.html',   fallback: 'Games'},
    {file: 'stack.html',   fallback: 'Crate Stack'},
    {file: 'balloon.html', fallback: 'Balloons'},
    {file: 'index.html',   fallback: 'Box Pusher'},
    {file: 'wacko.html',   fallback: 'Whack'},
  ];
  const here = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  const site = document.getElementById('site');
  const foot = document.getElementById('foot');
  const title = document.getElementById('title');

  function draw(names) {
    const name = f => names[f] || PAGES.find(p => p.file === f).fallback;
    if (site) site.innerHTML = `<div class="site-in">
      <a class="brand" href="games.html" title="Games menu"><span class="brand-mark">A55</span>
        <span class="brand-text"><b>A55 Games</b><span>rebuilt from the phone firmware</span></span></a>
      <nav class="nav" aria-label="Pages">${PAGES.map(p =>
        `<a href="${p.file}"${p.file === here ? ' aria-current="page"' : ''}>${esc(name(p.file))}</a>`).join('')}</nav></div>`;
    if (foot) foot.innerHTML = `<div>Personal preservation project. No firmware or original assets are included:
      graphics, levels and texts are loaded from <code>out/</code>, which the scripts in <code>scripts/extract/</code>
      build from your own dump. Reverse-engineering notes: <code>NOTES.md</code>, pseudo-C in <code>docs/</code>.</div>`;
    const me = PAGES.find(p => p.file === here);
    if (me) {
      const n = here === 'games.html' ? `${name(here)} menu` : name(here);
      if (title) title.textContent = n;
      document.title = `${n} · A55 Games`;
    }
  }
  draw({});
  fetch(new URL('../out/games/menu.json', location.href)).then(r => r.json()).then(m => {
    const names = {'games.html': m.header};
    for (const it of m.items || []) if (it.port) names[it.port] = it.title;
    draw(names);
  }).catch(() => {});
})();
