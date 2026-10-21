/* Deterministic overlay timeline: every frame is rendered by seeking one paused GSAP timeline. */
(function () {
  const D = window.DATA;
  const stage = document.getElementById('stage');
  const TL = gsap.timeline({ paused: true });
  const C = { red: '#FF4D5A', amber: '#FFB020', green: '#3DDC84', blue: '#4DA3FF', yellow: '#FFE14D' };

  // ------------------------------------------------------------------ helpers
  const icon = (name, size = 48, color = 'currentColor', sw = 2.2) => {
    const svg = (D.icons[name] || '').replace('<svg', `<svg stroke-width="${sw}"`);
    return `<span class="ic" style="width:${size}px;height:${size}px;color:${color}">${svg}</span>`;
  };
  const el = (cls, html, css) => {
    const e = document.createElement('div');
    e.className = cls || '';
    if (html) e.innerHTML = html;
    if (css) e.style.cssText = css;
    stage.appendChild(e);
    return e;
  };
  const hide = (e) => TL.set(e, { autoAlpha: 0 }, 0);
  const ft = (e, from, to, t) => TL.fromTo(e, from, Object.assign({ immediateRender: false }, to), t);
  const to = (e, vars, t) => TL.to(e, Object.assign({ immediateRender: false }, vars), t);

  // pop a block in at t0 and out at t1 (t1 = null keeps it)
  function pop(e, t0, t1, o = {}) {
    const { x = 0, y = 0, s = 0.9, r = 0, d = 0.42, ease = 'back.out(1.6)', out = 0.22, ox = 0, oy = 0, os = 0.97 } = o;
    hide(e);
    ft(e, { autoAlpha: 0, x, y, scale: s, rotation: r }, { autoAlpha: 1, x: 0, y: 0, scale: 1, rotation: 0, duration: d, ease }, t0);
    if (t1 != null) to(e, { autoAlpha: 0, x: ox, y: oy, scale: os, duration: out, ease: 'power2.in' }, t1 - out);
  }
  // show again later (second appearance of the same element)
  function again(e, t0, t1, o = {}) {
    const { x = 0, y = 0, s = 0.9, d = 0.42, ease = 'back.out(1.6)', out = 0.22 } = o;
    ft(e, { autoAlpha: 0, x, y, scale: s }, { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: d, ease }, t0);
    if (t1 != null) to(e, { autoAlpha: 0, scale: 0.97, duration: out, ease: 'power2.in' }, t1 - out);
  }
  function fade(e, t0, t1, d = 0.25) {
    hide(e);
    ft(e, { autoAlpha: 0 }, { autoAlpha: 1, duration: d, ease: 'power1.out' }, t0);
    if (t1 != null) to(e, { autoAlpha: 0, duration: d, ease: 'power1.in' }, t1 - d);
  }

  function card(o) {
    const { x, y, w, h, ic, title, sub, accent = C.amber, kind = '' } = o;
    const c = el(`card glass abs ${kind}`, '', `left:${x}px;top:${y}px;width:${w}px;height:${h}px`);
    c.innerHTML = `<div class="bar" style="background:${accent}"></div>
      <div class="icb" style="background:${accent}2b;color:${accent}">${icon(ic, 52)}</div>
      <div><div class="t1" style="color:${o.tc || '#fff'}">${title}</div>${sub ? `<div class="t2">${sub}</div>` : ''}</div>`;
    return c;
  }
  function chip(o) {
    const { x, y, w, text, ic, color = C.amber, kind = '' } = o;
    const c = el(`chip glass abs ${kind}`, `${icon(ic, 46, color)}<span>${text}</span>`, `left:${x}px;top:${y}px;${w ? `width:${w}px;` : ''}`);
    return c;
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
  const flash = (t, a = 0.5, d = 0.22) => {
    const f = el('abs', '', 'left:0;top:0;width:1920px;height:1080px;background:#fff');
    hide(f);
    ft(f, { autoAlpha: a }, { autoAlpha: 0, duration: d, ease: 'power2.out' }, t);
    TL.set(f, { autoAlpha: 0 }, t + d + 0.02);
  };

  // ------------------------------------------------------------------ captions
  const kindColor = { amt: C.amber, bad: '#FF5C68', ok: C.green };
  const CAP_SHIFT = 84 / 30;            // welcome stinger: captions of pieces 8+ come after the inserted 2.8 s
  D.captions.forEach((g0) => {
    const sh = g0.piece >= 8 ? CAP_SHIFT : 0;
    const g = Object.assign({}, g0, { a: g0.a + sh, b: g0.b + sh, words: g0.words.map((w) => Object.assign({}, w, { t: w.t + sh })) });
    const c = el('cap');
    const ws = g.words.map((w) => {
      const s = document.createElement('span');
      s.className = 'w';
      s.textContent = w.s;
      if (w.k) s.style.color = kindColor[w.k];
      c.appendChild(s);
      return s;
    });
    hide(c);
    ft(c, { autoAlpha: 0, y: 16, scale: 0.94 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.14, ease: 'back.out(2)' }, g.a);
    to(c, { autoAlpha: 0, duration: 0.07, ease: 'none' }, g.b - 0.07);
    g.words.forEach((w, i) => {
      const s = ws[i];
      const base = w.k ? kindColor[w.k] : '#fff';
      const hi = w.k ? '#FFFFFF' : C.yellow;
      const t1 = i + 1 < g.words.length ? g.words[i + 1].t : g.b - 0.12;
      ft(s, { color: base, scale: 1 }, { color: hi, scale: 1.05, duration: 0.07, ease: 'power2.out' }, w.t);
      to(s, { color: base, scale: 1, duration: 0.08, ease: 'power1.in' }, Math.max(t1, w.t + 0.1));
    });
  });

  // ================================================================== SCENES
  // --- 0.3 - 6.6  title block ----------------------------------------------------------
  (function () {
    const g = el('abs', `<div class="pill red">${icon('triangle-alert', 36, '#fff', 2.6)}<span>SCAM ALERT</span></div>
      <div class="glass" style="margin-top:16px;padding:20px 34px 22px;border-radius:22px">
        <div style="font-weight:600;font-size:34px;color:#CBD2E0">WhatsApp-il varunna</div>
        <div style="font-weight:800;font-size:66px;line-height:1.05;letter-spacing:.5px">FAKE <span style="color:${C.amber}">OFFER</span> LINKS</div>
      </div>`, 'left:64px;top:60px');
    pop(g, 0.35, 6.6, { x: -80, s: 0.96, d: 0.55, ease: 'power3.out', ox: -60 });
    const dot = g.querySelector('.pill');
    to(dot, { scale: 1.05, duration: 0.5, yoyo: true, repeat: 9, ease: 'sine.inOut' }, 0.9);
  })();

  // --- fake message card (3.0 - 8.1, again 16.7 - 26.5) ---------------------------------
  let FM;
  (function () {
    const c = el('fmsg glass abs', `
      <div class="hd"><div class="av">${icon('gift', 30, '#fff')}</div><div><div style="color:#fff;font-size:26px">Special Offer</div><div style="font-weight:500;font-size:20px">unknown number • now</div></div></div>
      <div class="tt">Google Pay 9th Anniversary!</div>
      <div class="amtw"><span class="amt a1">₹6,000</span><span class="amt a2">₹9,000</span><span class="amt a3">₹10,000</span></div>
      <div class="sub">Cashback — claim now 👇</div>
      <div class="lnk">gpay-9th-offer.xyz/claim</div>
      <div class="stamp" style="left:130px;top:150px;font-size:112px;transform:rotate(-13deg)">FAKE</div>`, 'left:1300px;top:210px');
    FM = c;
    const a = [c.querySelector('.a1'), c.querySelector('.a2'), c.querySelector('.a3')];
    const st = c.querySelector('.stamp');
    a.forEach(hide); hide(st);
    pop(c, 3.0, 8.1, { x: 140, s: 0.92, d: 0.5, ease: 'back.out(1.5)', ox: 80 });
    ft(a[0], { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.25, ease: 'back.out(2)' }, 3.45);
    to(a[0], { autoAlpha: 0, y: -24, duration: 0.18 }, 5.0);
    ft(a[1], { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.25, ease: 'back.out(2)' }, 5.07);
    to(a[1], { autoAlpha: 0, y: -24, duration: 0.18 }, 6.08);
    ft(a[2], { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.25, ease: 'back.out(2)' }, 6.15);
    again(c, 16.7, 26.5, { x: 140, d: 0.5, s: 0.92 });
    // the stamp slams at "orikkalum alla"
    slam(st, 22.95, 3.2, 0.18);
    shakeEl(c, 23.12, 14, 8, 0.45);
    flash(23.1, 0.35, 0.2);
    to(st, { autoAlpha: 0, duration: 0.2 }, 26.3);
  })();

  // --- 8.2 - 12.3 / 12.4 - 16.5  cutaway labels -------------------------------------------
  (function () {
    const l1 = el('abs glass', `${icon('message-circle', 46, C.green)}<span style="font-weight:800;font-size:38px">WhatsApp message</span>`,
      'left:90px;top:96px;display:flex;align-items:center;gap:16px;padding:16px 30px 16px 22px;border-radius:999px');
    pop(l1, 8.35, 12.15, { y: -30, d: 0.4, ox: 0, oy: -20 });
    const l2 = el('abs glass', `${icon('thumbs-up', 46, C.blue)}<span style="font-weight:800;font-size:38px">Facebook post</span>`,
      'left:90px;top:96px;display:flex;align-items:center;gap:16px;padding:16px 30px 16px 22px;border-radius:999px');
    pop(l2, 12.55, 16.35, { y: -30, d: 0.4 });
    // floating notification toasts
    const toasts = [['Win ₹10,000 now!', 'gift', 9.0], ['Claim your cashback', 'ticket-percent', 10.2], ['Last chance — tap link', 'zap', 11.1]];
    toasts.forEach(([txt, ic, t], i) => {
      const x = el('abs glass', `${icon(ic, 40, C.amber)}<span style="font-weight:700;font-size:30px">${txt}</span>`,
        `left:1190px;top:${210 + i * 118}px;width:640px;height:92px;display:flex;align-items:center;gap:18px;padding:0 28px;box-sizing:border-box;border-radius:24px`);
      pop(x, t, 12.15, { x: 120, d: 0.45, ease: 'back.out(1.4)' });
    });
    const t2 = [['Mega Sale — 90% OFF', 'ticket-percent', 13.3], ['Free gift for you!', 'gift', 14.3], ['Share to claim reward', 'forward', 15.1]];
    t2.forEach(([txt, ic, t], i) => {
      const x = el('abs glass', `${icon(ic, 40, C.amber)}<span style="font-weight:700;font-size:30px">${txt}</span>`,
        `left:1190px;top:${210 + i * 118}px;width:640px;height:92px;display:flex;align-items:center;gap:18px;padding:0 28px;box-sizing:border-box;border-radius:24px`);
      pop(x, t, 16.35, { x: 120, d: 0.45, ease: 'back.out(1.4)' });
    });
  })();

  // --- 20.9 - 26.5  "sathyamaano?"  ->  "NEVER!" ------------------------------------------
  (function () {
    const q = el('big shadow-t', '?', `left:1420px;top:590px;font-size:250px;color:${C.amber};text-shadow:0 0 60px rgba(255,176,32,.55)`);
    pop(q, 21.0, 22.8, { s: 0.2, r: -25, d: 0.5, ease: 'back.out(2.2)', out: 0.12 });
    const n = el('big', 'NEVER!', `left:1290px;top:640px;font-size:140px;color:${C.red};letter-spacing:2px;text-shadow:0 8px 40px rgba(255,77,90,.55),0 0 0 #000;-webkit-text-stroke:8px rgba(10,0,2,.7);paint-order:stroke fill`);
    hide(n);
    slam(n, 22.8, 3, 0.2);
    shakeEl(n, 23.0, 10, 6, 0.35);
    to(n, { autoAlpha: 0, duration: 0.25 }, 26.2);
  })();

  // --- 26.7 - 35.3  panam / data / maanam -------------------------------------------------
  (function () {
    const rows = [['indian-rupee', 'PANAM', 'Money loss', 27.45, C.amber], ['smartphone', 'DATA', 'Phone / computer data', 30.2, C.blue], ['user-x', 'MAANAM', 'Reputation', 32.85, C.red]];
    rows.forEach(([ic, t, s, tt, col], i) => {
      const c = card({ x: 1290, y: 230 + i * 190, w: 570, h: 160, ic, title: t, sub: s, accent: col });
      pop(c, tt, 35.15, { x: 150, d: 0.5, ease: 'back.out(1.5)', ox: 60 });
    });
  })();

  // --- 43.2 - 46.8  message + link -> tap ---------------------------------------------------
  (function () {
    const c = el('abs glass', `<div style="font-weight:600;font-size:26px;color:#B9C0CE">New message</div>
      <div style="font-weight:700;font-size:34px;margin:8px 0 14px">Offer eduthu nokkoo 👇</div>
      <div class="lk" style="display:inline-block;font-weight:600;font-size:28px;color:#6BB7FF;text-decoration:underline;padding:10px 18px;border-radius:14px;background:rgba(77,163,255,.14)">gpay-9th-offer.xyz/claim</div>`,
      'left:1290px;top:260px;width:570px;box-sizing:border-box;padding:26px 30px');
    pop(c, 43.25, 46.7, { x: 120, d: 0.5 });
    const cur = el('abs', icon('mouse-pointer-click', 74, '#fff', 2.2), 'left:1750px;top:520px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))');
    hide(cur);
    ft(cur, { autoAlpha: 0, x: 80, y: 120 }, { autoAlpha: 1, x: -180, y: -110, duration: 1.1, ease: 'power2.inOut' }, 44.2);
    to(cur, { scale: 0.8, duration: 0.1, yoyo: true, repeat: 1 }, 45.4);
    to(cur, { autoAlpha: 0, duration: 0.2 }, 46.5);
    const rip = el('abs', '', 'left:1530px;top:370px;width:90px;height:90px;border-radius:50%;border:6px solid #FF4D5A;margin:-45px 0 0 -45px');
    hide(rip);
    ft(rip, { autoAlpha: 0.95, scale: 0.2 }, { autoAlpha: 0, scale: 3.2, duration: 0.6, ease: 'power2.out' }, 45.4);
    const warn = el('abs glass red', `${icon('triangle-alert', 52, C.red)}<span style="font-weight:800;font-size:40px;color:#FF7A84">TRAP!</span>`,
      'left:1290px;top:470px;display:flex;align-items:center;gap:18px;padding:18px 34px;border-radius:24px');
    pop(warn, 45.7, 46.7, { s: 0.6, d: 0.4, ease: 'back.out(2.4)' });
    shakeEl(warn, 45.9, 8, 6, 0.3);
  })();

  // --- 46.9 - 56.5  link open cheyyumbol ---------------------------------------------------
  (function () {
    const head = el('abs glass', `${icon('link', 40, C.red)}<span style="font-weight:800;font-size:31px;letter-spacing:.5px">LINK OPEN CHEYYUMBOL</span>`,
      'left:1290px;top:200px;width:570px;height:92px;box-sizing:border-box;display:flex;align-items:center;gap:16px;padding:0 26px;border-radius:24px');
    pop(head, 46.9, 56.4, { x: 120, d: 0.45 });
    const rows = [['database', 'DATA CHORI', 48.4], ['user-x', 'MAANANASHTAM', 49.35], ['indian-rupee', 'DHANANASHTAM', 50.35], ['skull', 'AND MORE…', 51.7]];
    rows.forEach(([ic, t, tt], i) => {
      const c = chip({ x: 1290, y: 315 + i * 112, w: 570, text: t, ic, color: C.red, kind: 'red' });
      pop(c, tt, 56.4, { x: 140, d: 0.42, ease: 'back.out(1.5)' });
    });
  })();

  // --- 56.9 - 65.9  trusted names -> fake links ------------------------------------------
  (function () {
    const head = el('abs glass', `${icon('badge-check', 40, C.amber)}<span style="font-weight:800;font-size:30px;letter-spacing:.5px">TRUSTED NAMES, FAKE LINKS</span>`,
      'left:1290px;top:200px;width:570px;height:92px;box-sizing:border-box;display:flex;align-items:center;gap:16px;padding:0 26px;border-radius:24px');
    pop(head, 56.9, 65.8, { x: 120, d: 0.45 });
    [['Google Pay', 57.0], ['PhonePe', 57.85], ['Paytm', 58.8]].forEach(([t, tt], i) => {
      const c = el('abs glass', `<span style="font-weight:800;font-size:40px">${t}</span><span class="tag red" style="margin-left:auto">${icon('unlink', 22, '#FF7A84')} FAKE LINK</span>`,
        `left:1290px;top:${315 + i * 108}px;width:570px;height:92px;box-sizing:border-box;display:flex;align-items:center;padding:0 26px;border-radius:24px`);
      pop(c, tt, 65.8, { x: 140, d: 0.42, ease: 'back.out(1.5)' });
    });
    const p = el('abs', `<span style="font-weight:700;font-size:30px;color:#E6EAF3">Aalukal pettennu vishwasikkum</span>`,
      'left:1290px;top:660px;width:570px;text-align:center');
    pop(p, 61.0, 65.6, { y: 20, d: 0.4 });
  })();

  // --- 66.3 - 71.4  open / forward cheyyaruthu ------------------------------------------
  (function () {
    const tiles = [['link', 'OPEN', 'CHEYYARUTHU', 66.5, 1290], ['forward', 'FORWARD', 'CHEYYARUTHU', 69.3, 1585]];
    tiles.forEach(([ic, a, b, tt, x]) => {
      const c = el('abs glass red', `<div style="position:relative;display:flex;justify-content:center">${icon(ic, 92, '#FF7A84', 2.4)}
        <div style="position:absolute;right:-34px;top:-34px;width:62px;height:62px;border-radius:50%;background:${C.red};display:flex;align-items:center;justify-content:center;box-shadow:0 6px 20px rgba(255,77,90,.6)">${icon('x', 40, '#fff', 3.6)}</div></div>
        <div style="font-weight:800;font-size:38px;margin-top:20px;text-align:center">${a}</div>
        <div style="font-weight:700;font-size:23px;color:#FF9AA2;text-align:center;letter-spacing:1px">${b}</div>`,
        `left:${x}px;top:330px;width:275px;height:300px;box-sizing:border-box;padding:46px 12px 0;border-radius:28px`);
      pop(c, tt, 71.35, { y: 60, s: 0.7, d: 0.5, ease: 'back.out(2)' });
    });
  })();

  // ============================================================ stock cutaways (the stock footage itself is composited by ffmpeg)
  // --- 71.6 - 75.0  scammers (glitch text) --------------------------------------------------
  (function () {
    const mk = (col, dx, a) => el('glitch abs', 'SCAMMERS', `left:${180 + dx}px;top:${380}px;font-size:170px;color:${col};mix-blend-mode:${a};text-shadow:none`);
    const base = mk('#fff', 0, 'normal');
    const r = mk('#FF2D55', 0, 'screen');
    const b = mk('#00E5FF', 0, 'screen');
    [base, r, b].forEach(hide);
    ft(base, { autoAlpha: 0, scale: 1.3 }, { autoAlpha: 1, scale: 1, duration: 0.25, ease: 'power3.out' }, 72.0);
    ft(r, { autoAlpha: 0 }, { autoAlpha: 0.9, duration: 0.05 }, 72.0);
    ft(b, { autoAlpha: 0 }, { autoAlpha: 0.9, duration: 0.05 }, 72.0);
    for (let k = 0; k < 14; k++) {
      const t = 72.05 + k * 0.2;
      to(r, { x: gsap.utils.random(-14, 14, 1), y: gsap.utils.random(-6, 6, 1), duration: 0.07 }, t);
      to(b, { x: gsap.utils.random(-14, 14, 1), y: gsap.utils.random(-6, 6, 1), duration: 0.07 }, t + 0.06);
    }
    [base, r, b].forEach((e) => to(e, { autoAlpha: 0, duration: 0.2 }, 74.75));
    const tag = el('abs glass red', `${icon('skull', 44, C.red)}<span style="font-weight:800;font-size:34px">THATTIPPUKAAR</span>`,
      'left:90px;top:96px;display:flex;align-items:center;gap:16px;padding:14px 28px 14px 20px;border-radius:999px');
    pop(tag, 71.8, 74.9, { y: -30, d: 0.4 });
  })();

  // --- 75.1 - 83.3  info chips over the hacker clips ---------------------------------------
  (function () {
    const items = [['user', 'PERSONAL INFO', 75.65, C.amber], ['landmark', 'BANK DETAILS', 77.9, C.amber], ['smartphone', 'MOBILE DATA', 80.8, C.amber]];
    items.forEach(([ic, t, tt, col], i) => {
      const c = chip({ x: 100, y: 300 + i * 140, w: 560, text: t, ic, color: col });
      pop(c, tt, 83.2, { x: -140, d: 0.45, ease: 'back.out(1.5)' });
    });
    const st = el('abs glass red', `${icon('siren', 50, C.red)}<span style="font-weight:800;font-size:44px;color:#FF7A84">DATA STOLEN!</span>`,
      'left:100px;top:735px;display:flex;align-items:center;gap:18px;padding:16px 34px 16px 24px;border-radius:24px');
    pop(st, 82.35, 83.2, { s: 0.6, d: 0.35, ease: 'back.out(2.4)' });
  })();

  // --- 83.5 - 87.2  OTP / UPI PIN -------------------------------------------------------------
  (function () {
    const a = el('big', `OTP<span style="color:${C.amber}">?</span>`, 'left:150px;top:300px;font-size:190px;text-shadow:0 10px 50px rgba(0,0,0,.7)');
    const b = el('big', `UPI PIN<span style="color:${C.amber}">?</span>`, 'left:150px;top:520px;font-size:190px;text-shadow:0 10px 50px rgba(0,0,0,.7)');
    pop(a, 83.75, 87.1, { x: -160, d: 0.5, ease: 'back.out(1.6)' });
    pop(b, 85.5, 87.1, { x: -160, d: 0.5, ease: 'back.out(1.6)' });
    const lk = el('abs', icon('lock', 120, C.amber, 2), 'left:1480px;top:380px;filter:drop-shadow(0 10px 30px rgba(255,176,32,.5))');
    pop(lk, 84.1, 87.1, { s: 0.3, d: 0.55, ease: 'back.out(2)' });
  })();

  // --- 87.3 - 90.6  never share -----------------------------------------------------------------
  (function () {
    const c = card({ x: 1290, y: 300, w: 570, h: 190, ic: 'shield-alert', title: 'NEVER SHARE', sub: 'OTP / UPI PIN', accent: C.red, kind: 'red', tc: '#FF7A84' });
    pop(c, 87.4, 90.6, { x: 150, d: 0.5, ease: 'back.out(1.6)', ox: 60 });
    shakeEl(c, 87.75, 9, 6, 0.35);
  })();

  // --- 91.4 - 100.5  receive money needs no pin ---------------------------------------------------
  (function () {
    const a = card({ x: 1290, y: 270, w: 570, h: 200, ic: 'hand-coins', title: 'RECEIVE MONEY', sub: 'No PIN • No OTP needed', accent: C.green, kind: 'green' });
    pop(a, 91.5, 100.4, { x: 150, d: 0.5, ox: 60 });
    const b = card({ x: 1290, y: 510, w: 570, h: 200, ic: 'wallet', title: 'PAY MONEY', sub: 'Only then PIN / OTP', accent: C.amber });
    pop(b, 96.65, 100.4, { x: 150, d: 0.5, ox: 60 });
  })();

  // --- 100.8 - 104.8  enthu cheyyum? --------------------------------------------------------------
  (function () {
    const l = card({ x: 1290, y: 300, w: 570, h: 150, ic: 'link', title: 'LINK VANNAAL…', accent: C.blue });
    pop(l, 100.9, 103.45, { x: 150, d: 0.5, ox: 60 });
    const q = el('big shadow-t', `ENTHU<br>CHEYYUM<span style="color:${C.amber}">?</span>`, `left:1300px;top:420px;font-size:92px;line-height:1.04;text-shadow:0 8px 40px rgba(0,0,0,.6)`);
    pop(q, 103.5, 104.85, { s: 0.6, d: 0.45, ease: 'back.out(2)', out: 0.15 });
  })();

  window.__build_part1 = true;
  window.TL = TL;
  window.el = el; window.pop = pop; window.again = again; window.fade = fade; window.card = card; window.chip = chip;
  window.icon = icon; window.hide = hide; window.ft = ft; window.to = to; window.shakeEl = shakeEl; window.flash = flash; window.slam = slam; window.C = C;
})();
window.seek = (f) => { window.TL.time(f / 30, false); };
