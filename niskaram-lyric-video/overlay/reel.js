/* Deterministic overlay renderer for the 9:16 reels (same idea as overlay.js: everything is a pure function of time).
 *   window.setup(reel, cues)  – reel: {duration, capY, capSize, hook:{text,start,end,y,size}, endStart, shadeY, ...}
 *                               cues: lyric cues whose word times are already in reel time
 *   window.renderAt(t)        – pose every element for time t
 */
(() => {
  const W = 1080, H = 1920;
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, p) => a + (b - a) * p;
  const eOut3 = p => 1 - Math.pow(1 - p, 3);
  const eIn3 = p => p * p * p;
  const easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const $ = id => document.getElementById(id);

  let R = null, runs = [], chunks = [], hookWords = [];

  async function setup(reel, cueList) {
    R = reel;
    const root = document.documentElement.style;
    root.setProperty('--capSize', (R.capSize || 128) + 'px');
    root.setProperty('--capY', (R.capY || 1470) + 'px');
    root.setProperty('--capX', (R.capX || 64) + 'px');
    if (R.hook && R.hook.size) root.setProperty('--hookSize', R.hook.size + 'px');
    const cues = cueList.slice().sort((a, b) => a.start - b.start);

    // caption chunks: every word on its own; a very short word is paired with the next one (same rule as the film)
    chunks = [];
    cues.forEach((c, ci) => {
      const ws = c.words, n = ws.length;
      const dur = i => (i + 1 < n ? ws[i + 1].t0 : ws[i].t1) - ws[i].t0;
      let k = 0;
      while (k < n) {
        let b = k;
        if (b + 1 < n && (dur(b) < 0.42 || [...ws[b].w].length <= 2)) b++;
        chunks.push({ ci, text: ws.slice(k, b + 1).map(w => w.w).join(' '), t0: ws[k].t0, t1: b + 1 < n ? ws[b + 1].t0 : ws[b].t1, last: b + 1 >= n });
        k = b + 1;
      }
    });
    chunks.forEach((ch, i) => {
      const nx = chunks[i + 1];
      ch.contig = !!nx && nx.t0 - ch.t1 < 0.15;
      ch.vis0 = ch.t0 - 0.16; ch.vis1 = ch.t1 + (ch.contig ? 0.14 : 0.42);
    });
    runs = [];
    chunks.forEach(ch => {
      const r = runs[runs.length - 1];
      if (r && ch.vis0 - r.vis1 <= 0.9) r.vis1 = Math.max(r.vis1, ch.vis1); else runs.push({ vis0: ch.vis0, vis1: ch.vis1 });
    });

    const lt = $('lt');
    chunks.forEach(ch => {
      const box = document.createElement('div'); box.className = 'cap';
      box.innerHTML = '<div class="t"></div><div class="u"><div class="track"></div><div class="fill"></div><div class="head"></div></div>';
      const tEl = box.firstChild;
      if (/[؀-ۿ]/.test(ch.text)) {
        if (/[ഀ-ൿ]/.test(ch.text)) {
          ch.text.split(/([؀-ۿ]+)/).filter(Boolean).forEach(part => {
            const sp = document.createElement('span'); sp.textContent = part;
            if (/[؀-ۿ]/.test(part)) sp.className = 'arw';
            tEl.appendChild(sp);
          });
        } else { tEl.textContent = ch.text; tEl.classList.add('ar'); }
      } else tEl.textContent = ch.text;
      lt.appendChild(box);
      ch.box = box; ch.tEl = tEl; ch.uEl = box.lastChild; ch.fill = ch.uEl.querySelector('.fill'); ch.head = ch.uEl.querySelector('.head');
    });

    // hook title: one span per word so a word's letters stay in one shaping run
    if (R.hook) {
      const h = $('hookText'); h.textContent = '';
      hookWords = R.hook.text.split(' ').map((w, i, a) => {
        const s = document.createElement('span'); s.textContent = w; s.style.display = 'inline-block'; if (i < a.length - 1) s.style.marginRight = '.28em';
        h.appendChild(s); return s;
      });
      $('hook').style.top = R.hook.y + 'px';
      $('hookShade').style.top = (R.hook.y - 120) + 'px';
      const hb = $('hook'); $('hookRule').style.top = (hb.offsetTop + hb.offsetHeight + 6) + 'px';
    }

    const fams = [`800 128px 'Uroob'`, "700 70px 'Amiri'", "600 40px 'Cinzel'", "700 40px 'Cinzel'"];
    await Promise.all(fams.map(f => document.fonts.load(f, 'നിസ്കരിച്ചോ ABC حي على ദുനിയാവിൻ')));
    await document.fonts.ready;

    // measure every caption chunk; centre it; very long chunks are scaled to fit the safe width
    chunks.forEach(ch => {
      ch.box.style.display = 'block';
      const tw = ch.tEl.offsetWidth;                      // natural text width (measured while visible)
      let w = tw;
      const maxW = R.capMaxW || 800;
      if (w > maxW) { ch.scale = maxW / w; w = maxW; } else ch.scale = 1;
      ch.w = w; ch.box.style.display = 'none';
      ch.box.style.left = (R.capX || 64) + 'px';           // left aligned (lower-left, above the reel interface)
      ch.uEl.style.width = (w + 16) + 'px';
      ch.uEl.style.left = '-8px';
    });

    const shade = $('capShade'); shade.style.top = (R.capY - 640) + 'px'; shade.style.height = (H - (R.capY - 640)) + 'px';
    $('endC1').style.top = (R.endY || 1130) + 'px'; $('endC2').style.top = ((R.endY || 1130) + 128) + 'px';
    window.__ready = true;
  }

  function updateHook(t) {
    const hk = R.hook; if (!hk) return;
    const a = hk.start, b = hk.end;
    const el = $('hook'), rule = $('hookRule');
    const hs = $('hookShade');
    if (t < a - 0.05 || t > b + 0.6) { el.style.opacity = 0; rule.style.opacity = 0; hs.style.opacity = 0; return; }
    el.style.opacity = 1;
    const out = eIn3(prog(t, b, b + 0.5));
    hs.style.opacity = hk.scrim ? (eOut3(prog(t, a - 0.05, a + 0.5)) * (1 - out)).toFixed(3) : 0;
    hookWords.forEach((s, i) => {
      const p = eOut3(prog(t, a + i * 0.16, a + i * 0.16 + 0.7));
      s.style.opacity = (p * (1 - out)).toFixed(3);
      s.style.transform = `translateY(${((1 - p) * 40 - out * 18).toFixed(1)}px) scale(${lerp(1.08, 1, p).toFixed(4)})`;
      s.style.filter = `blur(${((1 - p) * (1 - p) * 14 + out * 8).toFixed(2)}px)`;
    });
    const rp = eOut3(prog(t, a + 0.25, a + 1.1));
    rule.style.opacity = (rp * (1 - out)).toFixed(3); rule.style.width = (rp * (hk.rule_w || 560)) + 'px';
  }

  function updateLyrics(t) {
    const shade = $('capShade');
    const run = runs.find(r => t >= r.vis0 - 0.3 && t <= r.vis1 + 0.1);
    shade.style.opacity = run ? (eOut3(prog(t, run.vis0, run.vis0 + 0.45)) * (1 - eIn3(prog(t, run.vis1 - 0.5, run.vis1)))).toFixed(3) : 0;
    chunks.forEach(ch => {
      if (t < ch.vis0 - 0.02 || t > ch.vis1 + 0.02) { ch.box.style.display = 'none'; return; }
      ch.box.style.display = 'block';
      const tin = ch.t0 - 0.07;
      const e = prog(t, tin, tin + 0.26);
      const wipe = eOut3(prog(t, tin, tin + 0.24));
      const exitStart = ch.contig ? ch.t1 - 0.05 : ch.t1 + 0.12;
      const x = eIn3(prog(t, exitStart, exitStart + (ch.contig ? 0.13 : 0.26)));
      const sc = lerp(0.8, 1, easeOutBack(e)) * ch.scale * (1 + 0.02 * Math.sin(Math.PI * prog(t, ch.t0, ch.t1)));
      const el = ch.tEl;
      el.style.opacity = Math.min(1, e * 2.4) * (1 - x);
      el.style.transform = `translate(${-34 * x}px, ${(1 - eOut3(e)) * 46 + x * -10}px) scale(${sc.toFixed(4)})`;
      el.style.filter = `blur(${((1 - e) * (1 - e) * 16 + x * 10).toFixed(2)}px)`;
      el.style.clipPath = wipe >= 0.999 ? 'none' : `inset(-80px calc(${((1 - wipe) * 100).toFixed(2)}% - ${(wipe * 120).toFixed(1)}px) -80px -80px)`;
      const glow = Math.exp(-Math.pow((t - (ch.t0 + 0.1)) / 0.22, 2));
      el.style.textShadow = `0 4px 22px rgba(0,0,0,.72), 0 0 ${(20 + 34 * glow).toFixed(0)}px rgba(255,205,100,${(0.28 + 0.5 * glow).toFixed(2)})`;
      const p = prog(t, ch.t0, ch.t1);
      const w = ch.w + 16;
      const uIn = eOut3(prog(t, tin, tin + 0.2)), flick = 0.93 + 0.07 * Math.sin(t * 43) * Math.sin(t * 17);
      ch.uEl.style.opacity = (uIn * (1 - x) * flick).toFixed(3);
      ch.uEl.style.transform = `translateX(${-34 * x}px)`;
      ch.fill.style.width = (w * p).toFixed(1) + 'px';
      ch.head.style.left = (w * p).toFixed(1) + 'px';
      ch.head.style.opacity = (p < 0.999 ? 1 : 1 - prog(t, ch.t1, ch.t1 + 0.18)).toFixed(3);
    });
  }

  function updateBugAndEnd(t) {
    const es = R.endStart;
    $('bug').style.opacity = (0.72 * eOut3(prog(t, 0.9, 1.8)) * (1 - prog(t, es - 0.5, es))).toFixed(3);
    const sh = eOut3(prog(t, es, es + 0.9));
    $('endShade').style.opacity = sh.toFixed(3);
    const lp = eOut3(prog(t, es + 0.15, es + 1.1));
    $('endLogo').style.opacity = lp.toFixed(3); $('endLogo').style.transform = `scale(${lerp(0.92, 1, lp).toFixed(4)})`;
    const np = eOut3(prog(t, es + 0.5, es + 1.4));
    $('endName').style.opacity = np.toFixed(3); $('endName').style.transform = `translateY(${((1 - np) * 12).toFixed(1)}px)`;
    ['endC1', 'endC2'].forEach((id, k) => {
      const p = eOut3(prog(t, es + 0.8 + k * 0.35, es + 1.7 + k * 0.35));
      $(id).style.opacity = p.toFixed(3); $(id).style.transform = `translateY(${((1 - p) * 14).toFixed(1)}px)`;
    });
  }

  function renderAt(t) { updateHook(t); updateLyrics(t); updateBugAndEnd(t); }
  window.setup = setup; window.renderAt = renderAt;
})();
