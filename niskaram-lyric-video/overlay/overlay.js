/* Deterministic overlay renderer.
 *
 * Everything on screen is a pure function of the video time `t` (seconds), so a
 * headless browser can screenshot any frame in any order:
 *   window.setup(project, cues)  – build DOM from project.json + lyric cues (video time)
 *   window.renderAt(t)           – pose every element for time t
 *   window.intervals()           – [[a,b],...] seconds in which anything is visible
 */
(() => {
  const W = 1920, H = 804;
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, p) => a + (b - a) * p;
  const eOut3 = p => 1 - Math.pow(1 - p, 3);
  const eOut5 = p => 1 - Math.pow(1 - p, 5);
  const eIn3 = p => p * p * p;
  const eIO3 = p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  // calligraphy pen: mostly steady, with a gentle start and settle
  const ePen = p => 0.45 * p + 0.55 * eIO3(p);
  const $ = id => document.getElementById(id);

  let P = null, cues = [], runs = [], lines = [], endItems = [], particles = [];
  let titleW = 0;

  // small deterministic PRNG so particles are identical on every render
  function mulberry32(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const gauss = r => (r() + r() + r() + r() - 2) / 2;

  const isArabic = s => { const a = (s.match(/[؀-ۿ]/g) || []).length, m = (s.match(/[ഀ-ൿ]/g) || []).length; return a > m; };

  async function setup(project, cueList) {
    P = project; cues = cueList.slice().sort((a, b) => a.start - b.start);

    // ---- lyric runs (contiguous cues share one animated plate) ----
    runs = [];
    cues.forEach(c => {
      const r = runs[runs.length - 1];
      if (r && c.start - r.end <= 1.0) { r.cues.push(c); r.end = c.end; } else runs.push({ start: c.start, end: c.end, cues: [c] });
    });
    const lt = $('lt');
    lines = [];
    cues.forEach((c, i) => {
      const el = document.createElement('div');
      el.className = 'ltLine' + (isArabic(c.text) ? ' ar' : '');
      if (isArabic(c.text)) el.dir = 'rtl';
      const words = c.text.trim().split(/\s+/);
      const spans = words.map(w => { const s = document.createElement('span'); s.className = 'w'; s.textContent = w; el.appendChild(s); return s; });
      const ul = document.createElement('div'); ul.className = 'ltUline';
      lt.appendChild(el); lt.appendChild(ul);
      lines.push({ cue: c, el, spans, ul });
    });

    // ---- end credit items ----
    const ec = P.end_credits, ei = $('endItems');
    endItems = ec.items.map(it => {
      const d = document.createElement('div'); d.className = 'eItem';
      d.innerHTML = `<div class="l"></div><div class="n"></div>`;
      d.firstChild.textContent = it.label; d.lastChild.textContent = it.name;
      ei.appendChild(d); return { d };
    });

    ['titleShadow', 'titleGlow', 'titleText', 'titleSheen'].forEach(id => { $(id).textContent = P.title_arabic; });

    const fams = ["800 60px 'Anek Malayalam'", "700 60px 'Anek Malayalam'", "700 70px 'Noto Naskh Arabic'", "700 200px 'Aref Ruqaa'",
      "600 60px 'Cinzel'", "400 24px 'Cinzel'", "italic 500 36px 'Cormorant Garamond'"];
    await Promise.all(fams.map(f => document.fonts.load(f, 'നിസ്കരിച്ചോ ABC حي على')));
    await document.fonts.ready;
    await new Promise(r => { const i = $('endLogoImg'); if (i.complete) r(); else i.onload = r; });

    // measure & position lyric lines (bottom aligned, left anchored)
    const baseBottom = H - 96;
    lines.forEach(L => {
      L.h = L.el.offsetHeight; L.w = L.el.offsetWidth;
      L.el.style.top = (baseBottom - L.h) + 'px';
      L.ul.style.top = (baseBottom + 4) + 'px';
    });
    runs.forEach(r => { r.h = Math.max(...r.cues.map(c => lines[cues.indexOf(c)].h)); });

    // end items layout: vertically centred stack
    const gap = 118, n = endItems.length, top0 = H / 2 - (n * gap) / 2 + 14;
    endItems.forEach((it, k) => { it.d.style.top = (top0 + k * gap) + 'px'; });

    // title geometry + particles
    titleW = $('titleText').getBoundingClientRect().width - 88;
    const t0 = P.title_card.start, t1 = P.title_card.end, r = mulberry32(20241019);
    const penX = tt => (960 + titleW / 2) - ePen(prog(tt, t0 + 0.9, t0 + 3.3)) * titleW;
    particles = [];
    for (let i = 0; i < 170; i++) {
      const tb = t0 + 0.9 + r() * 2.5;
      particles.push({ tb, x0: penX(tb) + gauss(r) * 18, y0: 402 + (r() - 0.5) * 200, vx: (r() - 0.5) * 46 - 10, vy: -(18 + r() * 78), life: 1.5 + r() * 2.3, r: 0.8 + r() * 2.2, ph: r() * 6.28 });
    }
    for (let i = 0; i < 110; i++) {
      const tb = t0 + 3.0 + r() * Math.max(1, (t1 - t0 - 5.2));
      particles.push({ tb, x0: 960 + (r() - 0.5) * titleW * 1.05, y0: 402 + 60 + r() * 150, vx: (r() - 0.5) * 12, vy: -(8 + r() * 28), life: 3 + r() * 2.5, r: 0.7 + r() * 1.6, ph: r() * 6.28 });
    }
    window.__ready = true;
  }

  // ------------------------------------------------------------------ opening credit
  function updateCredit(t) {
    const el = $('credit'), shade = $('cardShade');
    const c = P.opening_credits.find(c => t >= c.start - 0.05 && t <= c.end + 0.05);
    if (!c) { el.style.display = 'none'; return 0; }
    el.style.display = 'block';
    const inP = prog(t, c.start, c.start + 1.25), outP = prog(t, c.end - 0.75, c.end);
    const vis = 1 - eIn3(outP);
    const label = el.querySelector('.label'), name = el.querySelector('.name');
    const rule = el.querySelector('.rule'), dia = el.querySelector('.dia');
    label.textContent = c.label; name.textContent = c.name;

    const ls = lerp(1.15, 0.5, eOut3(inP)) + outP * 0.12;
    label.style.letterSpacing = ls + 'em'; label.style.paddingLeft = ls + 'em';
    label.style.opacity = eOut3(prog(t, c.start, c.start + 0.9)) * vis;
    label.style.transform = `translateY(${(1 - eOut3(inP)) * 12}px)`;

    const rp = eOut5(prog(t, c.start + 0.2, c.start + 1.2));
    rule.style.width = (360 * rp) + 'px'; rule.style.opacity = vis;
    dia.style.opacity = prog(t, c.start + 0.15, c.start + 0.6) * vis;
    dia.style.transform = `rotate(45deg) scale(${lerp(0.2, 1, eOut3(prog(t, c.start + 0.15, c.start + 0.9)))})`;

    const np = prog(t, c.start + 0.3, c.start + 1.5);
    const nls = lerp(0.42, 0.14, eOut3(np)) + outP * 0.08;
    name.style.letterSpacing = nls + 'em'; name.style.paddingLeft = nls + 'em';
    name.style.opacity = eOut3(np) * vis;
    name.style.filter = `blur(${(1 - eOut3(np)) * 12 + outP * 6}px) drop-shadow(0 0 20px rgba(227,189,98,.30)) drop-shadow(0 4px 16px rgba(0,0,0,.65))`;
    name.style.transform = `scale(${lerp(1.07, 1, eOut3(np)) + outP * 0.02})`;
    name.style.backgroundPosition = `${lerp(110, -10, prog(t, c.start + 1.1, c.start + 2.7))}% 0`;
    return Math.min(inP * 1.2, 1) * vis;
  }

  // ------------------------------------------------------------------ Arabic title
  function updateTitle(t) {
    const el = $('title'), T = P.title_card, t0 = T.start, t1 = T.end;
    if (t < t0 - 0.05 || t > t1 + 0.05) { el.style.display = 'none'; return 0; }
    el.style.display = 'block';
    const ex = prog(t, t1 - 1.1, t1);
    const root = el; root.style.opacity = 1 - eIn3(ex);

    // light line
    const ll = $('lightLine'), lp = eOut5(prog(t, t0, t0 + 0.85));
    ll.style.width = (1180 * lp) + 'px';
    ll.style.opacity = (1 - prog(t, t0 + 1.0, t0 + 1.9)) * prog(t, t0, t0 + 0.15);
    ll.style.transform = `translateX(-50%) scaleY(${lerp(1, 0.4, prog(t, t0 + 0.9, t0 + 1.9))})`;

    // calligraphy reveal (right -> left)
    const rv = ePen(prog(t, t0 + 0.9, t0 + 3.3)), wrap = $('titleWrap'), gl = $('titleGlow'), sh = $('titleSheen');
    const mask = `linear-gradient(to left, #000 ${rv * 114 - 14}%, transparent ${rv * 114 + 2}%)`;
    const rise = 1 - eOut3(prog(t, t0 + 0.9, t0 + 3.8));
    const bump = Math.exp(-Math.pow((t - (t0 + 3.3)) / 0.45, 2));
    const pulse = 0.5 + 0.5 * Math.sin((t - t0) * 1.9);
    const glow = 12 + 14 * pulse + 40 * bump + 60 * ex;
    wrap.style.webkitMaskImage = mask; wrap.style.maskImage = mask;
    wrap.style.transform = `translate(-50%, -50%) translateY(${rise * 28}px) scale(${lerp(0.965, 1, 1 - rise) + ex * 0.05})`;
    wrap.style.filter = `blur(${rise * 12}px) brightness(${1 + 0.35 * bump + 0.9 * ex})`;
    gl.style.textShadow = `0 0 ${glow}px rgba(240,200,110,${0.5 + 0.3 * bump + 0.3 * ex})`;
    const sp = prog(t, t0 + 3.4, t0 + 5.6);
    sh.style.backgroundPosition = `${lerp(15, 85, sp)}% 0`;
    sh.style.opacity = sp > 0 && sp < 1 ? 1 : 0;

    // pen light
    const pen = $('pen'), px = (960 + titleW / 2) - rv * titleW;
    pen.style.left = px + 'px';
    pen.style.opacity = Math.min(prog(t, t0 + 0.9, t0 + 1.2), 1 - prog(t, t0 + 3.1, t0 + 3.6));
    pen.style.transform = `scaleY(${lerp(0.6, 1, Math.sin(rv * Math.PI))})`;

    // ornaments: eight-pointed star + hairlines, base rule
    const sp1 = prog(t, t0 + 0.35, t0 + 1.8), ang = (t - t0) * 6;
    const st = $('ornTop'); const sc = lerp(0.2, 1, eOut3(sp1));
    const dash = 208;
    ['sqA', 'sqB'].forEach((id, i) => {
      const r = $(id); r.setAttribute('stroke-dasharray', dash); r.setAttribute('stroke-dashoffset', dash * (1 - eOut3(sp1)));
      r.setAttribute('transform', `rotate(${(i ? 45 : 0)})`);
    });
    st.setAttribute('transform', `translate(960 196) rotate(${ang}) scale(${sc})`);
    $('cc').setAttribute('r', 7 * eOut3(sp1));
    const L = 420 * eOut5(prog(t, t0 + 0.8, t0 + 2.3));
    // lines are outside the rotating group's scale, so set absolute coordinates in a counter-transform
    const lnL = $('lnL'), lnR = $('lnR');
    const inv = `rotate(${-ang}) scale(${1 / Math.max(sc, 0.001)})`;
    [lnL, lnR].forEach(n => n.setAttribute('transform', inv));
    lnL.setAttribute('x1', -62); lnL.setAttribute('x2', -62 - L); lnR.setAttribute('x1', 62); lnR.setAttribute('x2', 62 + L);
    st.style.opacity = prog(t, t0 + 0.35, t0 + 0.6);

    const bt = $('ornBottom'), bp = eOut5(prog(t, t0 + 2.9, t0 + 4.2));
    bt.setAttribute('transform', 'translate(960 596)');
    const bl = $('blL'), br = $('blR');
    bl.setAttribute('x1', -26); bl.setAttribute('x2', -26 - 330 * bp); br.setAttribute('x1', 26); br.setAttribute('x2', 26 + 330 * bp);
    [bl, br].forEach(n => { n.setAttribute('y1', 0); n.setAttribute('y2', 0); });
    $('bd').setAttribute('transform', `rotate(45) scale(${eOut3(prog(t, t0 + 2.9, t0 + 3.6))})`);
    bt.style.opacity = prog(t, t0 + 2.9, t0 + 3.2);

    // particles
    const cv = $('particles'), ctx = cv.getContext('2d');
    ctx.clearRect(0, 0, W, H); ctx.globalCompositeOperation = 'lighter';
    for (const p of particles) {
      const age = t - p.tb; if (age < 0 || age > p.life) continue;
      const u = age / p.life;
      const a = Math.min(age / 0.25, 1) * Math.pow(1 - u, 1.4) * (0.65 + 0.35 * Math.sin(age * 7 + p.ph));
      const x = p.x0 + p.vx * age + Math.sin(age * 1.7 + p.ph) * 7, y = p.y0 + p.vy * age;
      const g = ctx.createRadialGradient(x, y, 0, x, y, p.r * 5);
      g.addColorStop(0, `rgba(255,236,170,${0.95 * a})`); g.addColorStop(0.25, `rgba(240,200,110,${0.45 * a})`); g.addColorStop(1, 'rgba(240,200,110,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, p.r * 5, 0, 6.2832); ctx.fill();
    }
    return Math.min(prog(t, t0, t0 + 1.2), 1 - ex);
  }

  // ------------------------------------------------------------------ lyric lower-third
  function updateLyrics(t) {
    const plate = $('ltPlate'), bar = $('ltBar');
    const run = runs.find(r => t >= r.start - 0.45 && t <= r.end + 0.75);
    lines.forEach(L => { L.el.style.display = 'none'; L.ul.style.display = 'none'; });
    if (!run) { plate.style.opacity = 0; bar.style.opacity = 0; return; }
    const inP = prog(t, run.start - 0.4, run.start + 0.35), outP = prog(t, run.end + 0.05, run.end + 0.65);
    plate.style.opacity = eOut3(inP) * (1 - eIn3(outP));
    plate.style.transform = `scaleX(${lerp(0.55, 1, eOut3(inP))})`;
    const bh = run.h - 18, bottom = H - 96;
    bar.style.top = (bottom - run.h + 10) + 'px'; bar.style.height = bh + 'px';
    const bp = eOut5(prog(t, run.start - 0.35, run.start + 0.3));
    bar.style.transform = `scaleY(${bp * (1 - eIn3(outP))})`;
    bar.style.opacity = bp > 0 ? 1 : 0;

    run.cues.forEach((c, k) => {
      const L = lines[cues.indexOf(c)];
      const nextContig = k < run.cues.length - 1;
      const prevContig = k > 0;
      const tin = c.start - (prevContig ? 0.1 : 0.22);
      const tout = nextContig ? c.end - 0.38 : c.end + 0.05;
      const dOut = nextContig ? 0.3 : 0.55;
      if (t < tin - 0.02 || t > tout + dOut + 0.02) return;
      L.el.style.display = 'block'; L.ul.style.display = 'block';
      const xp = eIn3(prog(t, tout, tout + dOut));
      L.spans.forEach((s, j) => {
        const wp = eOut3(prog(t, tin + j * 0.085, tin + j * 0.085 + 0.62));
        s.style.opacity = wp * (1 - xp);
        s.style.transform = `translate(${(-38 * (1 - wp)) * (L.el.dir === 'rtl' ? -1 : 1)}px, ${-22 * xp}px)`;
        s.style.filter = `blur(${(1 - wp) * 10 + xp * 7}px)`;
      });
      const up = eOut3(prog(t, tin + 0.12, tin + 0.95));
      L.ul.style.width = (Math.min(L.w, 760) * 0.62 * up) + 'px';
      L.ul.style.opacity = 0.9 * (1 - xp) * Math.min(1, up * 3);
    });
  }

  // ------------------------------------------------------------------ end credits
  function updateEnd(t) {
    const ec = P.end_credits, es = ec.start, ls = ec.logo_card_start;
    const shade = $('endShade'), items = $('endItems'), logo = $('endLogo'), thanks = $('thanks');
    if (t < es - 0.05) { shade.style.opacity = 0; items.style.display = 'none'; logo.style.opacity = 0; thanks.style.opacity = 0; return 0; }
    const fadeAll = prog(t, ls - 0.8, ls - 0.1);
    shade.style.opacity = eOut3(prog(t, es, es + 1.4)) * (1 - fadeAll);
    items.style.display = 'block';
    endItems.forEach((it, k) => {
      const a = es + 0.9 + k * 0.75, p = eOut3(prog(t, a, a + 1.0));
      it.d.style.opacity = p * (1 - fadeAll);
      it.d.style.transform = `translateX(${(1 - p) * 70}px)`;
      it.d.style.filter = `blur(${(1 - p) * 8}px)`;
    });
    const lp = eOut3(prog(t, ls, ls + 1.9));
    logo.style.opacity = lp; logo.style.transform = `scale(${lerp(0.93, 1, lp)})`;
    thanks.style.opacity = eOut3(prog(t, ls + 1.0, ls + 2.4));
    thanks.style.transform = `translateY(${(1 - eOut3(prog(t, ls + 1.0, ls + 2.4))) * 10}px)`;
    return Math.max(eOut3(prog(t, es, es + 1.4)) * (1 - fadeAll), lp * 0.8);
  }

  function renderAt(t) {
    const a = updateCredit(t), b = updateTitle(t);
    const sh = $('cardShade');
    const ec = P.end_credits;
    const logoShade = 0.55 * eOut3(prog(t, ec.logo_card_start, ec.logo_card_start + 1.6));
    sh.style.opacity = Math.max(a * 0.9, b * 0.95, logoShade);
    updateLyrics(t); updateEnd(t);
  }

  function intervals() {
    const iv = [];
    P.opening_credits.forEach(c => iv.push([c.start - 0.1, c.end + 0.1]));
    iv.push([P.title_card.start - 0.1, P.title_card.end + 0.1]);
    runs.forEach(r => iv.push([r.start - 0.5, r.end + 0.8]));
    iv.push([P.end_credits.start - 0.1, P.total_duration]);
    iv.sort((x, y) => x[0] - y[0]);
    const m = [];
    iv.forEach(x => { const l = m[m.length - 1]; if (l && x[0] <= l[1] + 0.001) l[1] = Math.max(l[1], x[1]); else m.push(x.slice()); });
    return m;
  }

  window.setup = setup; window.renderAt = renderAt; window.intervals = intervals;
})();
