/* Deterministic overlay timeline (v3): one paused GSAP timeline, every frame rendered by seeking it. */
(function () {
  const D = window.DATA;
  const stage = document.getElementById('stage');
  const TL = gsap.timeline({ paused: true });
  const C = { red: '#FF4D5A', amber: '#FFB020', green: '#3DDC84', blue: '#2D8CFF', cyan: '#5BD6FF', yellow: '#FFE14D', ink: '#071a42' };
  const FPS = 30;

  const icon = (name, size = 48, color = 'currentColor', sw = 2.2) => {
    const svg = (D.icons[name] || '').replace('<svg', `<svg stroke-width="${sw}"`);
    return `<span class="ic" style="width:${size}px;height:${size}px;color:${color}">${svg}</span>`;
  };
  const el = (cls, html, css, parent) => {
    const e = document.createElement('div');
    e.className = cls || '';
    if (html) e.innerHTML = html;
    if (css) e.style.cssText = css;
    (parent || stage).appendChild(e);
    return e;
  };
  const hide = (e) => TL.set(e, { autoAlpha: 0 }, 0);
  const ft = (e, from, to, t) => TL.fromTo(e, from, Object.assign({ immediateRender: false }, to), t);
  const to = (e, vars, t) => TL.to(e, Object.assign({ immediateRender: false }, vars), t);
  const set = (e, vars, t) => TL.set(e, vars, t);

  // pop in at t0, out at t1 (t1 = null keeps it)
  function pop(e, t0, t1, o = {}) {
    const { x = 0, y = 0, s = 0.9, r = 0, d = 0.42, ease = 'back.out(1.6)', out = 0.2, ox = 0, oy = 0, os = 0.97 } = o;
    hide(e);
    ft(e, { autoAlpha: 0, x, y, scale: s, rotation: r }, { autoAlpha: 1, x: 0, y: 0, scale: 1, rotation: 0, duration: d, ease }, t0);
    if (t1 != null) to(e, { autoAlpha: 0, x: ox, y: oy, scale: os, duration: out, ease: 'power2.in' }, t1 - out);
  }
  function fade(e, t0, t1, d = 0.25) {
    hide(e);
    ft(e, { autoAlpha: 0 }, { autoAlpha: 1, duration: d, ease: 'power1.out' }, t0);
    if (t1 != null) to(e, { autoAlpha: 0, duration: d, ease: 'power1.in' }, t1 - d);
  }
  const shakeEl = (e, t, amp = 12, n = 8, dur = 0.5) => {
    const step = dur / n;
    for (let i = 0; i < n; i++) {
      const a = amp * (1 - i / n);
      to(e, { x: (i % 2 ? -1 : 1) * a, y: (i % 3 ? 1 : -1) * a * 0.5, duration: step, ease: 'none' }, t + i * step);
    }
    to(e, { x: 0, y: 0, duration: step, ease: 'none' }, t + dur);
  };
  const slam = (e, t, s0 = 3, d = 0.2) => {
    ft(e, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.03 }, t);
    ft(e, { scale: s0 }, { scale: 1, duration: d, ease: 'power4.in' }, t);
  };
  const flash = (t, a = 0.5, d = 0.22, col = '#fff') => {
    const f = el('abs fx', '', `left:0;top:0;width:1920px;height:1080px;background:${col}`);
    hide(f);
    ft(f, { autoAlpha: a }, { autoAlpha: 0, duration: d, ease: 'power2.out' }, t);
    set(f, { autoAlpha: 0 }, t + d + 0.02);
  };

  // ---------------------------------------------------------------- word times of the aligned SRT
  const cueWords = {};
  D.words.forEach((w) => { (cueWords[w.cue + 1] = cueWords[w.cue + 1] || []).push(w); });
  const tw = (cue, k) => cueWords[cue][k - 1].t0;        // start of the k-th word (1-based) of SRT cue `cue`
  const te = (cue, k) => cueWords[cue][k - 1].t1;

  // ---------------------------------------------------------------- scene frame / transitions
  const SC = {};
  D.scenes.forEach((s) => { SC[s.id] = s; });
  const BAR_W = 3900, SKEW = 14, OFF = Math.tan(SKEW * Math.PI / 180) * 1480;
  /* light-blue "glass" bar that sweeps across; the screen is fully covered around tc (the ffmpeg layer toggles there) */
  function wipe(tc) {
    const bar = el('abs fx', `<div style="position:absolute;right:0;top:0;bottom:0;width:14px;background:linear-gradient(180deg,#bfeaff,#4fb6ff);box-shadow:0 0 50px 10px rgba(80,180,255,.9)"></div>
      <div style="position:absolute;left:0;top:0;bottom:0;width:8px;background:#6fc4ff;box-shadow:0 0 40px 6px rgba(80,180,255,.8)"></div>`,
      `left:0;top:-200px;width:${BAR_W}px;height:1480px;transform:skewX(-${SKEW}deg);background:linear-gradient(90deg,#0a3b97 0%,#082a73 35%,#06194a 100%);`);
    const x0 = -BAR_W - OFF - 40, xc = -900, x1 = 1920 + OFF + 40;
    set(bar, { x: x0, autoAlpha: 0 }, 0);
    set(bar, { autoAlpha: 1 }, tc - 0.045 - 0.27);
    ft(bar, { x: x0 }, { x: xc, duration: 0.27, ease: 'power2.in' }, tc - 0.045 - 0.27);
    ft(bar, { x: xc }, { x: x1, duration: 0.3, ease: 'power2.out' }, tc + 0.045);
    set(bar, { autoAlpha: 0 }, tc + 0.045 + 0.3);
    return bar;
  }
  /* full-screen key-point scene: speaker is hidden by ffmpeg for [t0,t1); content lives in the returned group */
  function kscene(id, build) {
    const s = SC[id];
    const g = el('kscene');
    hide(g);
    set(g, { autoAlpha: 1 }, s.t0);
    set(g, { autoAlpha: 0 }, s.t1);
    if (s.wipeIn) wipe(s.t0);
    if (s.wipeOut) wipe(s.t1);
    build(g, s.t0, s.t1, s);
    return g;
  }

  // ---------------------------------------------------------------- reusable pieces
  function card(o) {
    const { x, y, w, h, ic, title, sub, accent = C.amber, kind = '', tsize = 64, isize = 92, parent } = o;
    const c = el(`card glass abs ${kind}`, '', `left:${x}px;top:${y}px;width:${w}px;height:${h}px`, parent);
    c.innerHTML = `<div class="bar" style="background:${accent}"></div>
      <div class="icb" style="width:${isize + 22}px;height:${isize + 22}px;background:${accent}2b;color:${accent};margin-left:34px">${icon(ic, isize - 12)}</div>
      <div style="min-width:0"><div class="t-ml" style="font-size:${tsize}px;color:${o.tc || '#fff'}">${title}</div>${sub ? `<div class="en" style="font-weight:500;font-size:28px;color:#B9C8E6;margin-top:6px">${sub}</div>` : ''}</div>`;
    return c;
  }
  const IMG = {
    wa: { src: 'assets/wa_scam.jpg', ar: 1704 / 921 },
    gh: { src: 'assets/gpay_home.jpg', ar: 2576 / 1186 },
    go: { src: 'assets/gpay_offers.jpg', ar: 2576 / 1186 },
    ph: { src: 'assets/phonepe_home.jpg', ar: 2576 / 1186 },
    po: { src: 'assets/phonepe_offerzone.jpg', ar: 2576 / 1186 },
  };
  /* phone frame with screenshot layers; every layer is {wrap(overflow hidden) > zw(zoom/pan) > img + marks} */
  function phone(o) {
    const { x, y, w, h, imgs, parent } = o;
    const ph = el('phone', '<div class="scr"></div>', `left:${x}px;top:${y}px;width:${w}px;height:${h}px`, parent);
    const scr = ph.querySelector('.scr');
    const SW = w - 24, SH = h - 24;
    const layers = imgs.map((k) => {
      const I = IMG[k];
      const wrap = document.createElement('div');
      wrap.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;overflow:hidden';
      const zw = document.createElement('div');
      zw.style.cssText = `position:absolute;left:0;top:0;width:${SW}px;height:${SW * I.ar}px;transform-origin:0 0`;
      zw.innerHTML = `<img src="${I.src}" style="position:absolute;left:0;top:0;width:${SW}px;height:${SW * I.ar}px">`;
      wrap.appendChild(zw);
      scr.appendChild(wrap);
      return { wrap, zw, iw: SW, ih: SW * I.ar };
    });
    return { ph, scr, layers, SW, SH };
  }
  // pan / zoom layer `li` so that image point (fx,fy) (fractions) sits at (cx,cy) of the screen
  function panzoom(P, li, fx, fy, s, t, dur = 0.7, o = {}) {
    const L = P.layers[li];
    const cx = o.cx != null ? o.cx : 0.5, cy = o.cy != null ? o.cy : 0.45;
    let tx = P.SW * cx - fx * L.iw * s, ty = P.SH * cy - fy * L.ih * s;
    tx = Math.min(0, Math.max(P.SW - L.iw * s, tx));
    ty = Math.min(0, Math.max(P.SH - L.ih * s, ty));
    ft(L.zw, { x: o.fromX != null ? o.fromX : 0, y: o.fromY != null ? o.fromY : 0, scale: o.from != null ? o.from : 1 }, { x: tx, y: ty, scale: s, duration: dur, ease: o.ease || 'power3.inOut' }, t);
    return { tx, ty, s };
  }
  // highlight rectangle on image fractions; moves with the zoom of its layer
  function mark(P, li, fx, fy, fw, fh, t0, t1, col) {
    const L = P.layers[li];
    const r = document.createElement('div');
    r.className = 'rrect';
    r.style.cssText = `left:${fx * L.iw}px;top:${fy * L.ih}px;width:${fw * L.iw}px;height:${fh * L.ih}px;${col ? `border-color:${col};box-shadow:0 0 34px ${col}` : ''}`;
    L.zw.appendChild(r);
    hide(r);
    ft(r, { autoAlpha: 0, scale: 1.25 }, { autoAlpha: 1, scale: 1, duration: 0.3, ease: 'back.out(2)' }, t0);
    if (t1 != null) to(r, { autoAlpha: 0, duration: 0.2 }, t1 - 0.2);
    return r;
  }
  // slide a layer in from the right at t (first layer is just there)
  function layerIn(P, li, t, dir = 100) {
    const L = P.layers[li];
    TL.set(L.wrap, { xPercent: dir }, 0);
    ft(L.wrap, { xPercent: dir }, { xPercent: 0, duration: 0.55, ease: 'power3.inOut' }, t);
  }
  function layerOut(P, li, t) { to(P.layers[li].wrap, { xPercent: -100, duration: 0.55, ease: 'power3.inOut' }, t); }
  window.V3 = { D, stage, TL, C, FPS, icon, el, hide, ft, to, set, pop, fade, shakeEl, slam, flash, tw, te, SC, wipe, kscene, card, phone, panzoom, mark, layerIn, layerOut, IMG, cueWords };
})();
