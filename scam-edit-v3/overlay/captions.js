/* Malayalam captions in the left column: words appear as they are spoken, a glowing underline slides word to word. */
(function () {
  const { D, TL, el, hide, ft, to, set, C } = window.V3;
  const words = D.words;
  const LINE = 66 * 1.3, CENTER_Y = 650, MAXL = 3;
  const probe = el('cap-probe');
  const lines = (ws) => {
    probe.innerHTML = ws.map((w) => `<span class="w">${w}</span>`).join('');
    return Math.round(probe.getBoundingClientRect().height / LINE);
  };
  const strip = (w) => w.replace(/[.,?!"]/g, '');
  const AMBER = /^(6000|9000|10000|100%)$/;
  const RED = new Set(['ഒരിക്കലുമല്ല', 'ഫേക്ക്', 'നഷ്ടപ്പെടുകയോ', 'നഷ്ടപ്പെടാൻ', 'മാനം', 'മാനനഷ്ടം', 'ധനനഷ്ടം', 'ഒടിപി', 'ഒടിപിയോ', 'യുപിഐ', 'പിൻ', 'എംപിന്നോ',
    'സൂക്ഷിക്കേണ്ട', 'സൂക്ഷിക്കണം', 'നിൽക്കരുത്', 'ക്ലിക്ക്', 'ഫോർവേഡ്', 'ഡാറ്റ', 'അശ്രദ്ധ']);
  const GREEN = new Set(['ഒഫീഷ്യൽ', 'google.com', 'വെരിഫൈ', 'പരിശോധിക്കുക']);
  const base = (w) => {
    const s = strip(w);
    if (AMBER.test(s)) return C.amber;
    if (RED.has(s)) return '#FF7480';
    if (GREEN.has(s)) return '#59E89B';
    return '#FFFFFF';
  };

  // ---- phrases: <= 3 lines, break at pauses / sentence ends
  const phrases = [];
  let cur = [];
  const flush = () => { if (cur.length) { phrases.push(cur); cur = []; } };
  words.forEach((w) => {
    if (cur.length) {
      const prev = cur[cur.length - 1];
      let brk = w.t0 - prev.t1 > 0.5 || lines([...cur, w].map((x) => x.w)) > MAXL || w.t1 - cur[0].t0 > 5.4;
      if (!brk && /[.?!]$/.test(prev.w)) brk = true;              // a sentence always ends its phrase
      if (!brk && cur.length >= 4 && /,$/.test(prev.w)) brk = true;
      if (brk) flush();
    }
    cur.push(w);
  });
  flush();

  phrases.forEach((ph, pi) => {
    const nxt = phrases[pi + 1], prv = phrases[pi - 1];
    const tStart = Math.max(ph[0].t0 - 0.1, prv ? prv[prv.length - 1].t1 + 0.14 : 0);
    const lastEnd = ph[ph.length - 1].t1;
    let tEnd = lastEnd + 0.45;
    if (nxt) tEnd = Math.min(tEnd, Math.max(nxt[0].t0 - 0.12, lastEnd + 0.1));
    const n = lines(ph.map((w) => w.w));
    const top = Math.round(CENTER_Y - (n * LINE) / 2);
    const c = el('cap', '<div class="bar"></div>', `top:${top}px`);
    const spans = ph.map((w) => {
      const s = document.createElement('span');
      s.className = 'w';
      s.textContent = w.w;
      s.style.color = base(w.w);
      c.appendChild(s);
      return s;
    });
    const ul = document.createElement('div');
    ul.className = 'ul';
    c.appendChild(ul);
    // layout is known once the nodes are in the page
    const R = spans.map((s) => ({ l: s.offsetLeft, t: s.offsetTop, w: s.offsetWidth, h: s.offsetHeight }));
    hide(c);
    ft(c, { autoAlpha: 0, x: -44 }, { autoAlpha: 1, x: 0, duration: 0.3, ease: 'power3.out' }, tStart);
    to(c, { autoAlpha: 0, x: -24, duration: 0.2, ease: 'power2.in' }, tEnd - 0.2);
    ft(c.querySelector('.bar'), { scaleY: 0, transformOrigin: '50% 0%' }, { scaleY: 1, duration: 0.4, ease: 'power3.out' }, tStart);
    const UY = 73;                      // underline offset inside the line box
    const place = (r) => ({ left: r.l, top: r.t + UY, width: r.w - 8 });
    set(ul, Object.assign({ autoAlpha: 0 }, place(R[0])), 0);
    spans.forEach((s, k) => {
      const w = ph[k];
      const t0 = Math.max(w.t0 - 0.03, tStart);
      hide(s);
      set(s, { y: 22 }, 0);
      ft(s, { autoAlpha: 0, y: 24, scale: 0.94 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.2, ease: 'back.out(1.8)' }, t0);
      // current word: brighter + glow, the spoken ones settle back
      const b = base(w.w);
      const t1 = k + 1 < ph.length ? Math.max(ph[k + 1].t0 - 0.03, t0 + 0.1) : w.t1;
      ft(s, { textShadow: '0 4px 22px rgba(0,0,0,.7)' }, { textShadow: '0 0 26px rgba(90,200,255,.95),0 4px 22px rgba(0,0,0,.7)', duration: 0.08 }, t0);
      to(s, { textShadow: '0 4px 22px rgba(0,0,0,.7)', duration: 0.25 }, t1);
      if (b === '#FFFFFF') {
        ft(s, { color: '#FFFFFF' }, { color: '#FFFFFF', duration: 0.01 }, t0);
        to(s, { color: '#DDE8FF', duration: 0.3 }, t1 + 0.1);
      }
      // underline: slide along the line, fade across line breaks
      if (k === 0) {
        ft(ul, { autoAlpha: 0, scaleX: 0.2 }, { autoAlpha: 1, scaleX: 1, duration: 0.18, ease: 'power2.out' }, t0);
      } else {
        const p = R[k - 1], q = R[k];
        if (Math.abs(p.t - q.t) < 6) {
          ft(ul, { left: p.l, width: p.w - 8 }, { left: q.l, width: q.w - 8, duration: 0.15, ease: 'power2.out' }, t0);
        } else {
          to(ul, { autoAlpha: 0, duration: 0.05 }, t0 - 0.06);
          set(ul, place(q), t0 - 0.01);
          to(ul, { autoAlpha: 1, duration: 0.08 }, t0);
        }
      }
    });
    to(ul, { autoAlpha: 0, duration: 0.18 }, Math.max(lastEnd + 0.08, ph[ph.length - 1].t0 + 0.2));
  });
  window.V3.phrases = phrases;
})();
