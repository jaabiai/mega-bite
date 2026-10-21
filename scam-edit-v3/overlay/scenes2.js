/* key-point scenes, part 2 + headline chips for the speaker segments */
(function () {
  const V = window.V3;
  const { el, hide, ft, to, set, pop, fade, shakeEl, slam, flash, tw, te, kscene, card, phone, panzoom, mark, layerIn, layerOut, icon, C, TL, stage } = V;
  const ml = (txt, size, color = '#fff', extra = '') => `<div class="t-ml" style="font-size:${size}px;color:${color};${extra}">${txt}</div>`;
  const pill = (g, x, y, ic, txt, col, t0, t1, o = {}) => {
    const e = el(`abs glass ${o.kind || ''}`, `${icon(ic, o.is || 50, col)}${ml(txt, o.fs || 50, o.tc || '#fff')}`,
      `left:${x}px;top:${y}px;display:flex;align-items:center;gap:18px;padding:14px 38px 14px 24px;border-radius:999px`, g);
    pop(e, t0, t1, { y: -26, d: 0.45, x: o.x || 0, ease: 'back.out(1.6)' });
    return e;
  };
  const sub = (g, a, b) => { /* helper: shows a sub-group between a and b */
    const e = el('abs', '', 'left:0;top:0;width:1920px;height:1080px', g);
    hide(e);
    set(e, { autoAlpha: 1 }, a);
    to(e, { autoAlpha: 0, duration: 0.18 }, b - 0.18);
    set(e, { autoAlpha: 0 }, b);
    return e;
  };

  // ------------------------------------------------------------------ do NOT open / forward;  OTP & UPI PIN
  kscene('rules', (g, t0, t1) => {
    // A: open / forward
    const A = sub(g, t0, 62.72);
    pill(A, 980, 226, 'ban', 'ചെയ്യരുത്!', C.red, t0 + 0.2, 62.7, { kind: 'red', tc: '#FF8E98' });
    const a1 = card({ x: 980, y: 380, w: 860, h: 220, ic: 'link', title: 'ലിങ്ക് തുറക്കരുത്', sub: 'Open ചെയ്യരുത്', accent: C.red, kind: 'red', tsize: 76, isize: 110, parent: A });
    pop(a1, tw(18, 2) - 0.1, 62.6, { x: 150, d: 0.5, ox: 0 });
    const a2 = card({ x: 980, y: 650, w: 860, h: 220, ic: 'forward', title: 'ഫോർവേഡ് ചെയ്യരുത്', sub: 'Forward ചെയ്യരുത്', accent: C.red, kind: 'red', tsize: 76, isize: 110, parent: A });
    pop(a2, tw(18, 7) - 0.1, 62.6, { x: 150, d: 0.5 });
    shakeEl(a2, tw(18, 7) + 0.4, 8, 6, 0.3);
    // B: OTP / UPI PIN
    const Bg = sub(g, 62.72, 69.62);
    pill(Bg, 980, 226, 'hand', 'ആരോടും പറയരുത്', C.red, 62.9, 69.5, { kind: 'red', tc: '#FF8E98' });
    const o1 = el('abs glass red en', `${icon('lock-keyhole', 100, C.red)}<span style="font-weight:800;font-size:112px;letter-spacing:2px">OTP</span>`,
      'left:980px;top:372px;width:860px;height:200px;display:flex;align-items:center;gap:30px;padding:0 44px;box-sizing:border-box', Bg);
    pop(o1, tw(19, 2) - 0.1, 69.5, { x: 150, d: 0.5 });
    const o2 = el('abs glass red en', `${icon('key-round', 100, C.red)}<span style="font-weight:800;font-size:112px;letter-spacing:2px">UPI PIN</span>`,
      'left:980px;top:610px;width:860px;height:200px;display:flex;align-items:center;gap:30px;padding:0 44px;box-sizing:border-box', Bg);
    pop(o2, tw(19, 5) - 0.1, 69.5, { x: 150, d: 0.5 });
    const no = el('stamp t-ml', 'നൽകരുത്!', 'left:1130px;top:850px;font-size:90px;transform:rotate(-6deg)', Bg);
    hide(no);
    slam(no, tw(20, 6) - 0.05, 2.4, 0.16);
    flash(tw(20, 6) + 0.1, 0.3, 0.22, '#ff3a48');
    // C: receiving money needs no OTP / PIN
    const Cg = sub(g, 69.62, 75.22);
    pill(Cg, 980, 226, 'badge-indian-rupee', 'പണം സ്വീകരിക്കാൻ', C.green, 69.8, 75.1, { kind: 'green', tc: '#7BF0AE' });
    const c1 = el('abs glass red en', `${icon('lock-keyhole', 80, C.red)}<span style="font-weight:800;font-size:96px">OTP</span><span style="position:absolute;left:36px;right:36px;top:50%;height:10px;background:#FF4D5A;border-radius:5px;box-shadow:0 0 20px rgba(255,77,90,.8)"></span>`,
      'left:980px;top:372px;width:860px;height:170px;display:flex;align-items:center;gap:30px;padding:0 44px;box-sizing:border-box', Cg);
    pop(c1, tw(21, 6) - 0.1, 75.1, { x: 150, d: 0.5 });
    const c2 = el('abs glass red en', `${icon('key-round', 80, C.red)}<span style="font-weight:800;font-size:96px">PIN</span><span style="position:absolute;left:36px;right:36px;top:50%;height:10px;background:#FF4D5A;border-radius:5px;box-shadow:0 0 20px rgba(255,77,90,.8)"></span>`,
      'left:980px;top:572px;width:860px;height:170px;display:flex;align-items:center;gap:30px;padding:0 44px;box-sizing:border-box', Cg);
    pop(c2, tw(21, 8) - 0.1, 75.1, { x: 150, d: 0.5 });
    const c3 = el('abs glass green', `${icon('circle-check', 90, C.green)}${ml('ആവശ്യമില്ല', 84, '#7BF0AE')}`,
      'left:980px;top:775px;width:860px;height:170px;display:flex;align-items:center;gap:28px;padding:0 44px;box-sizing:border-box', Cg);
    pop(c3, tw(21, 10) - 0.1, 75.1, { s: 0.7, d: 0.5, ease: 'back.out(2.2)' });
    // D: only paying needs the PIN
    const Dg = sub(g, 75.22, t1);
    pill(Dg, 980, 226, 'send', 'പണം നൽകുമ്പോൾ മാത്രം', C.blue, 75.4, t1 - 0.1, { tc: '#fff' });
    const d1 = el('abs glass en', `${icon('key-round', 110, C.blue)}<span style="font-weight:800;font-size:120px">PIN</span><span class="t-ml" style="font-size:60px;color:#CFE0FF">ആവശ്യം</span>`,
      'left:980px;top:440px;width:860px;height:240px;display:flex;align-items:center;gap:34px;padding:0 44px;box-sizing:border-box', Dg);
    pop(d1, tw(22, 3) - 0.1, t1 - 0.1, { x: 150, d: 0.5 });
  });

  // ------------------------------------------------------------------ STEP 1: check the domain
  kscene('domain', (g, t0, t1) => {
    pill(g, 980, 214, 'list-checks', 'STEP 1', C.blue, t0 + 0.2, t1, { tc: '#fff', fs: 46 });
    const h = el('abs', ml('ഡൊമൈൻ പരിശോധിക്കുക', 58, '#fff', 'white-space:nowrap;text-shadow:0 8px 40px rgba(0,0,0,.6)'), 'left:984px;top:316px', g);
    pop(h, tw(24, 2) - 0.1, t1, { x: 80, d: 0.5, ease: 'power3.out' });
    const url = 'https://yubx.orcwk.xyz/FV1ziinym';
    const bar = el('urlbar glass red', `${icon('triangle-alert', 50, C.red)}<div class="u">https://<span class="dom">yubx.orcwk.xyz</span>/FV1ziinym</div>`,
      'left:980px;top:490px;width:860px', g);
    pop(bar, tw(24, 5) - 0.2, t1, { x: 120, d: 0.5 });
    const u = bar.querySelector('.u'), dom = bar.querySelector('.dom');
    const spans = [];
    // type the url
    const html = u.innerHTML;
    u.innerHTML = '';
    const mk = (txt, cls) => [...txt].forEach((chV) => { const s = document.createElement('span'); s.textContent = chV; if (cls) s.className = cls; u.appendChild(s); spans.push(s); });
    mk('https://'); const dm = document.createElement('span'); dm.className = 'dom'; u.appendChild(dm);
    [...'yubx.orcwk.xyz'].forEach((chV) => { const s = document.createElement('span'); s.textContent = chV; dm.appendChild(s); spans.push(s); });
    mk('/FV1ziinym');
    const tt = tw(24, 5);
    spans.forEach((s, i) => { set(s, { autoAlpha: 0 }, 0); set(s, { autoAlpha: 1 }, tt + 0.25 + i * 0.045); });
    // highlight the domain part
    const dRect = { l: 26 + 50 + 20 + 'https://'.length * 0, w: 0 };
    const dl = dm.offsetLeft, dw = dm.offsetWidth;
    const rr = el('abs', '', `left:${980 + dl - 14}px;top:${490 + 20}px;width:${dw + 28}px;height:76px;border:6px solid #FFE14D;border-radius:16px;box-shadow:0 0 34px rgba(255,225,77,.7)`, g);
    pop(rr, tw(24, 10) - 0.1, 92.0, { s: 1.15, d: 0.3, ease: 'back.out(2)', out: 0.12, os: 1 });
    const no = el('abs glass red', `${icon('circle-x', 52, C.red)}${ml('ഒഫീഷ്യൽ അല്ല!', 54, '#FF8E98')}`,
      'left:980px;top:652px;display:flex;align-items:center;gap:16px;padding:14px 34px 14px 22px;border-radius:26px', g);
    pop(no, tw(25, 5) - 0.1, 92.0, { y: 30, d: 0.45 });
    shakeEl(no, tw(25, 5) + 0.35, 8, 6, 0.3);
    // do not click
    const nc = el('abs glass red', `<div style="position:relative;display:flex">${icon('mouse-pointer-click', 80, C.red)}<span style="position:absolute;left:-6px;right:-6px;top:50%;height:9px;background:#FF4D5A;transform:rotate(-40deg);border-radius:5px"></span></div>${ml('ക്ലിക്ക് ചെയ്യരുത്!', 70, '#FF8E98')}`,
      'left:980px;top:780px;display:flex;align-items:center;gap:26px;padding:20px 40px 20px 30px;border-radius:30px', g);
    pop(nc, tw(26, 4) - 0.1, 94.45, { x: 120, d: 0.45 });
    shakeEl(nc, tw(26, 5), 9, 6, 0.3);
    // just read it
    const rd = el('abs glass green', `${icon('eye', 80, C.green)}${ml('വായിച്ച് നോക്കൂ', 70, '#7BF0AE')}`,
      'left:980px;top:780px;display:flex;align-items:center;gap:26px;padding:20px 40px 20px 30px;border-radius:30px', g);
    pop(rd, tw(27, 3) - 0.1, t1 - 0.05, { x: 120, d: 0.45 });
    const rr2 = el('abs', '', `left:${980 + dl - 14}px;top:${490 + 20}px;width:${dw + 28}px;height:76px;border:6px solid #3DDC84;border-radius:16px;box-shadow:0 0 34px rgba(61,220,132,.7)`, g);
    pop(rr2, tw(27, 3) - 0.1, t1 - 0.05, { s: 1.15, d: 0.3, ease: 'back.out(2)', os: 1 });
  });

  // ------------------------------------------------------------------ official links
  kscene('official', (g, t0, t1) => {
    pill(g, 980, 214, 'badge-check', 'ഒഫീഷ്യൽ ലിങ്ക്', C.green, t0 + 0.2, t1, { kind: 'green', tc: '#7BF0AE' });
    const b1 = el('urlbar glass green', `${icon('lock', 50, C.green)}<div class="u"><b>https://</b>google.com</div><span class="en" style="margin-left:auto;font-weight:800;font-size:26px;color:#58E79A;border:2px solid #3DDC84;border-radius:12px;padding:4px 14px">OFFICIAL</span>`,
      'left:980px;top:360px;width:860px', g);
    pop(b1, tw(28, 5) - 0.15, t1, { x: 120, d: 0.5 });
    const l1 = el('abs', ml('ഗൂഗിൾ പേ', 48, '#CFE0FF'), 'left:990px;top:300px', g);
    pop(l1, tw(28, 5) - 0.15, t1, { d: 0.3, y: 10 });
    const b2 = el('urlbar glass green', `${icon('lock', 50, C.green)}<div class="u"><b>https://</b>phonepe.com</div><span class="en" style="margin-left:auto;font-weight:800;font-size:26px;color:#58E79A;border:2px solid #3DDC84;border-radius:12px;padding:4px 14px">OFFICIAL</span>`,
      'left:980px;top:610px;width:860px', g);
    pop(b2, tw(29, 3) - 0.15, t1, { x: 120, d: 0.5 });
    const l2 = el('abs', ml('ഫോൺ പേ', 48, '#CFE0FF'), 'left:990px;top:550px', g);
    pop(l2, tw(29, 3) - 0.15, t1, { d: 0.3, y: 10 });
    const ok = el('abs glass green', `${icon('circle-check', 70, C.green)}${ml('ഒഫീഷ്യൽ ലിങ്ക് മാത്രം', 56, '#7BF0AE')}`,
      'left:980px;top:820px;display:flex;align-items:center;gap:20px;padding:18px 40px 18px 28px;border-radius:28px', g);
    pop(ok, tw(29, 6), t1, { s: 0.8, d: 0.5, ease: 'back.out(2)' });
  });

  // ------------------------------------------------------------------ STEP 2: open the app yourself
  kscene('gpay', (g, t0, t1) => {
    pill(g, 980, 214, 'list-checks', 'STEP 2', C.blue, t0 + 0.2, t1 - 0.1, { fs: 46 });
    const h = el('abs', ml('ആപ്പ് നേരിട്ട്<br>തുറക്കൂ', 56, '#fff', 'text-shadow:0 8px 40px rgba(0,0,0,.6)'), 'left:984px;top:300px', g);
    pop(h, tw(32, 1) - 0.1, 127.1, { x: 80, d: 0.5, ease: 'power3.out' });
    const P = phone({ x: 1400, y: 150, w: 404, h: 860, imgs: ['gh', 'go'], parent: g });
    pop(P.ph, tw(32, 6) - 0.2, 127.05, { x: 170, s: 0.92, d: 0.7, ease: 'power3.out' });
    ft(P.ph, { rotationY: -24, transformPerspective: 1400 }, { rotationY: 0, duration: 0.8, ease: 'power3.out' }, tw(32, 6) - 0.2);
    layerIn(P, 1, tw(33, 4) - 0.1);
    mark(P, 0, 0.03, 0.49, 0.94, 0.17, tw(32, 6) + 0.5, tw(33, 4) - 0.1);
    mark(P, 1, 0.04, 0.18, 0.92, 0.22, tw(33, 4) + 0.5, 122.0);
    mark(P, 1, 0.04, 0.50, 0.92, 0.46, 121.0, 124.1);
    const st = [['smartphone', 'GPay തുറക്കൂ', tw(32, 6) - 0.1, C.blue], ['gift', 'Offers നോക്കൂ', tw(33, 4) - 0.1, C.amber], ['badge-check', 'ഇവിടെ വെരിഫൈ ചെയ്യൂ', tw(34, 5) - 0.1, C.green]];
    st.forEach(([ic, tx, t, col], i) => {
      const c = card({ x: 980, y: 470 + i * 170, w: 390, h: 148, ic, title: tx, accent: col, tsize: 38, isize: 76, parent: g });
      c.querySelector('.icb').style.marginLeft = '28px';
      pop(c, t, 127.05, { x: -80, d: 0.45, ox: 0 });
    });
    // no such offer
    const no = el('abs', `<div style="width:170px;height:170px;border-radius:50%;background:rgba(255,77,90,.92);display:flex;align-items:center;justify-content:center;box-shadow:0 0 60px rgba(255,77,90,.8)">${icon('x', 120, '#fff', 3)}</div>`, 'left:1517px;top:480px', g);
    pop(no, tw(35, 7) - 0.1, 127.05, { s: 0.2, d: 0.45, ease: 'back.out(2.4)' });
    const nl = el('abs glass red', ml('ഓഫർ ഇല്ല!', 52, '#FF8E98'), 'left:980px;top:690px;padding:16px 36px;border-radius:26px;width:390px;box-sizing:border-box;text-align:center', g);
    pop(nl, tw(35, 7) - 0.1, 127.05, { y: 30, d: 0.45 });
    // 100 % fake
    const bigW = el('abs', '', 'left:0;top:0;width:1920px;height:1080px', g);
    hide(bigW);
    set(bigW, { autoAlpha: 1 }, 127.1);
    const fk = el('stamp t-ml', `<span style="color:${C.amber}" class="en">100%</span> ഫേക്ക്`, 'left:990px;top:400px;font-size:104px;transform:rotate(-7deg);padding:6px 34px', bigW);
    hide(fk);
    slam(fk, tw(36, 4) - 0.05, 2.6, 0.2);
    shakeEl(fk, tw(36, 4) + 0.2, 12, 8, 0.4);
    flash(tw(36, 4) + 0.18, 0.4, 0.25, '#ff3a48');
    const lk = el('abs', `<span class="en" style="font-weight:700;font-size:44px;color:#FF8E98;text-decoration:line-through">yubx.orcwk.xyz</span>`, 'left:1250px;top:650px', bigW);
    pop(lk, tw(36, 4) + 0.5, t1, { y: 20, d: 0.4 });
  });

  // ------------------------------------------------------------------ one careless click
  kscene('careful', (g, t0, t1) => {
    el('abs', '', 'left:0;top:0;width:1150px;height:1080px;background:linear-gradient(90deg,rgba(2,8,22,.78),rgba(2,8,22,.45) 70%,rgba(2,8,22,0))', g);
    const h = el('abs', ml('ചെറിയ ഒരു<br>അശ്രദ്ധ മതി!', 112, '#fff', 'line-height:1.18;text-shadow:0 8px 44px rgba(0,0,0,.65)'), 'left:984px;top:240px', g);
    pop(h, t0 + 0.2, t1, { x: 100, d: 0.55, ease: 'power3.out' });
    const bal = el('abs glass', `<div style="display:flex;align-items:center;gap:18px">${icon('landmark', 50, C.blue)}<span class="t-ml" style="font-size:42px;color:#B9D0FF">അക്കൗണ്ട് ബാലൻസ്</span></div><div class="en bv" style="font-weight:800;font-size:128px;line-height:1.1;margin-top:8px;color:#fff">₹48,250</div>`,
      'left:980px;top:610px;width:860px;box-sizing:border-box;padding:30px 44px 34px', g);
    pop(bal, tw(41, 5) - 0.2, t1, { y: 50, d: 0.5 });
    const bv = bal.querySelector('.bv');
    const o = { v: 48250 };
    TL.to(o, { v: 0, duration: 1.25, ease: 'power2.in', immediateRender: false, onUpdate: () => { bv.textContent = '₹' + Math.round(o.v).toLocaleString('en-IN'); } }, tw(41, 6));
    to(bv, { color: C.red, duration: 0.3 }, tw(41, 6) + 0.9);
    shakeEl(bal, tw(41, 6) + 1.2, 12, 8, 0.4);
    const m = el('abs glass red', `${icon('user-x', 56, C.red)}${ml('മാനവും പോകും!', 60, '#FF8E98')}`,
      'left:980px;top:880px;display:flex;align-items:center;gap:20px;padding:14px 40px 14px 26px;border-radius:999px', g);
    pop(m, tw(42, 3) - 0.1, t1, { y: 40, d: 0.5 });
  });

  // ------------------------------------------------------------------ recap
  kscene('recap', (g, t0, t1) => {
    pill(g, 980, 214, 'lightbulb', 'ഓർക്കുക!', C.amber, t0 + 0.2, t1, { kind: 'amber', tc: '#FFD27A' });
    const rows = [
      ['ban', 'ലിങ്ക് തുറക്കരുത്', C.red, 'red', tw(43, 3) - 0.1],
      ['forward', 'ഷെയർ ചെയ്യരുത്', C.red, 'red', tw(44, 5) - 0.1],
      ['key-round', 'OTP / PIN നൽകരുത്', C.red, 'red', tw(44, 7) + 0.2],
      ['badge-check', 'ഡൊമൈൻ പരിശോധിക്കുക', C.green, 'green', tw(44, 7) + 0.7],
    ];
    rows.forEach(([ic, tx, col, kind, t], i) => {
      const c = card({ x: 980, y: 320 + i * 170, w: 860, h: 148, ic, title: tx, accent: col, kind, tsize: 64, isize: 86, tc: kind === 'green' ? '#7BF0AE' : '#fff', parent: g });
      c.querySelector('.icb').style.marginLeft = '30px';
      pop(c, t, t1, { x: 150, d: 0.45, ox: 60 });
    });
  });

  kscene('share', (g, t0, t1) => {
    const sh = el('abs glass', `<div style="width:130px;height:130px;border-radius:50%;background:${C.blue};display:flex;align-items:center;justify-content:center;flex:none;box-shadow:0 0 50px rgba(45,140,255,.7)">${icon('share-2', 76, '#fff', 2.4)}</div>${ml('ഈ വീഡിയോ<br>ഷെയർ ചെയ്യൂ', 74)}`,
      'left:980px;top:260px;width:860px;box-sizing:border-box;display:flex;align-items:center;gap:36px;padding:34px 44px', g);
    pop(sh, tw(45, 1) - 0.2, t1, { x: 140, d: 0.55, ease: 'back.out(1.5)' });
    const ring = el('abs', '', 'left:1024px;top:294px;width:130px;height:130px;border-radius:50%;border:6px solid #4DA3FF', g);
    hide(ring);
    ft(ring, { autoAlpha: 0.9, scale: 1 }, { autoAlpha: 0, scale: 2.4, duration: 0.8, repeat: 3, ease: 'power2.out' }, tw(45, 3));
    const n = el('abs glass amber', `${icon('users', 80, C.amber)}${ml('നാലാൾ അറിയട്ടെ!', 70, '#FFD27A')}`,
      'left:980px;top:560px;width:860px;box-sizing:border-box;display:flex;align-items:center;gap:28px;padding:30px 44px', g);
    pop(n, tw(46, 1) - 0.1, t1, { x: 140, d: 0.5 });
    [0, 1, 2, 3].forEach((i) => {
      const a = el('abs', icon(i % 2 ? 'user' : 'smile', 62, '#fff', 2.2), `left:${1020 + i * 130}px;top:780px;width:104px;height:104px;border-radius:50%;background:${[C.blue, C.green, C.amber, '#B77CFF'][i]};display:flex;align-items:center;justify-content:center;box-shadow:0 8px 30px rgba(0,0,0,.5)`, g);
      pop(a, tw(46, 2) + i * 0.2, t1, { s: 0.2, y: 40, d: 0.45, ease: 'back.out(2.4)' });
    });
  });

  // ------------------------------------------------------------------ subscribe + end card
  kscene('end', (g, t0, t1) => {
    const T_END = 170.8;
    const glow = el('abs', '', 'left:410px;top:-60px;width:1100px;height:1100px;border-radius:50%;background:radial-gradient(circle,rgba(45,140,255,.34),rgba(45,140,255,0) 66%)', g);
    fade(glow, 171.0, t1, 0.6);
    to(glow, { scale: 1.1, duration: 1.6, yoyo: true, repeat: 3, ease: 'sine.inOut' }, 171.4);
    // subscribe button + thanks (while he says it)
    const sbW = sub(g, t0, T_END - 0.05);
    const btn = el('abs', `<div class="sb" style="display:flex;align-items:center;gap:22px;border-radius:999px;background:#FF2E3E;padding:30px 60px 30px 46px;box-shadow:0 14px 54px rgba(255,46,62,.55)"><span class="bl">${icon('bell', 74, '#fff', 2.4)}</span>
        <span style="position:relative;display:inline-block;width:450px;height:84px"><span class="en t1s" style="position:absolute;left:0;top:0;font-weight:800;font-size:64px;letter-spacing:3px;line-height:84px;white-space:nowrap">SUBSCRIBE</span><span class="en t2s" style="position:absolute;left:0;top:0;font-weight:800;font-size:56px;line-height:84px;white-space:nowrap">SUBSCRIBED</span></span></div>`,
      'left:1010px;top:340px', sbW);
    pop(btn, tw(48, 2) - 0.3, T_END - 0.05, { s: 0.5, d: 0.55, ease: 'back.out(2.2)' });
    const sb = btn.querySelector('.sb'), t1s = btn.querySelector('.t1s'), t2s = btn.querySelector('.t2s'), bl = btn.querySelector('.bl');
    set(t2s, { autoAlpha: 0 }, 0);
    const cur = el('abs', icon('mouse-pointer-click', 96, '#fff', 2.2), 'left:1760px;top:520px;filter:drop-shadow(0 8px 16px rgba(0,0,0,.6))', sbW);
    hide(cur);
    ft(cur, { autoAlpha: 0, x: 90, y: 110 }, { autoAlpha: 1, x: -250, y: -110, duration: 0.8, ease: 'power2.inOut' }, tw(48, 3) - 0.3);
    const tc = tw(48, 4) + 0.05;
    to(cur, { scale: 0.8, duration: 0.1, yoyo: true, repeat: 1 }, tc);
    to(cur, { autoAlpha: 0, duration: 0.2 }, tc + 0.5);
    to(sb, { backgroundColor: '#3a4256', duration: 0.2 }, tc + 0.05);
    to(t1s, { autoAlpha: 0, duration: 0.12 }, tc + 0.05);
    to(t2s, { autoAlpha: 1, duration: 0.12 }, tc + 0.1);
    to(bl, { rotation: 18, duration: 0.08, yoyo: true, repeat: 7, ease: 'sine.inOut', transformOrigin: '50% 10%' }, tc + 0.2);
    const th = el('abs', `${ml('നന്ദി!', 120, '#fff', 'text-shadow:0 8px 44px rgba(0,0,0,.6)')}${ml('നമസ്കാരം 🙏', 76, '#CFE0FF')}`, 'left:1020px;top:590px', sbW);
    pop(th, tw(48, 6) - 0.1, T_END - 0.05, { y: 50, s: 0.8, d: 0.6, ease: 'back.out(1.8)' });
    // end card
    const logo = el('abs', '<img src="assets/logo.png" style="width:100%;height:100%;display:block;filter:drop-shadow(0 20px 50px rgba(0,0,0,.65))">', 'left:660px;top:70px;width:600px;height:600px', g);
    hide(logo);
    ft(logo, { autoAlpha: 0, scale: 0.5, rotation: -20 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: 0.9, ease: 'back.out(1.6)' }, T_END + 0.15);
    to(logo, { y: -12, duration: 1.6, yoyo: true, repeat: 3, ease: 'sine.inOut' }, T_END + 1.2);
    const th2 = el('abs', `<div class="en" style="font-weight:600;font-size:42px;color:#BFD6F5;letter-spacing:7px">THANKS FOR WATCHING</div>`, 'left:0;right:0;top:700px;text-align:center', g);
    pop(th2, T_END + 0.7, null, { y: 40, d: 0.7, ease: 'power3.out' });
    const sub2 = el('abs', `<div style="display:inline-flex;align-items:center;gap:18px;border-radius:999px;background:#FF2E3E;padding:20px 50px 20px 34px;box-shadow:0 14px 44px rgba(255,46,62,.5)">${icon('bell-ring', 52, '#fff', 2.4)}<span class="en" style="font-weight:800;font-size:46px;letter-spacing:2px">SUBSCRIBE</span></div>`, 'left:0;right:0;top:820px;text-align:center', g);
    pop(sub2, T_END + 1.3, null, { y: 40, s: 0.6, d: 0.6, ease: 'back.out(2)' });
    to(sub2, { scale: 1.06, duration: 0.6, yoyo: true, repeat: 5, ease: 'sine.inOut' }, T_END + 2.0);
  });

  // ------------------------------------------------------------------ headline chips in the left column (speaker segments)
  function headline(t0, t1, items) {
    const g = el('abs hl', '', 'left:0;top:0;width:1920px;height:1080px');
    hide(g);
    set(g, { autoAlpha: 1 }, Math.max(0, t0 - 0.01));
    set(g, { autoAlpha: 0 }, t1 + 0.01);
    items.forEach((it) => {
      const col = it.col || C.blue;
      const e = el(`abs glass ${it.kind || ''}`, `${icon(it.ic, it.is || 54, col)}${it.en ? `<span class="en" style="font-weight:800;font-size:${it.fs || 46}px;letter-spacing:1px">${it.text}</span>` : ml(it.text, it.fs || 50, it.tc || '#fff', 'white-space:nowrap')}${it.tag ? `<span class="en" style="margin-left:14px;font-weight:800;font-size:24px;color:#FF8E98;border:2px solid #FF4D5A;border-radius:10px;padding:2px 12px">${it.tag}</span>` : ''}`,
        `left:96px;top:${it.y}px;display:flex;align-items:center;gap:18px;padding:12px 34px 12px 22px;border-radius:${it.round ? 999 : 26}px;max-width:820px;box-sizing:border-box`, g);
      pop(e, it.t, it.t1 || t1, { x: -60, d: 0.45, ease: 'power3.out', out: 0.22, ox: -30 });
    });
  }
  const Y0 = 104;
  headline(0.0, 2.45, [
    { ic: 'triangle-alert', text: 'SCAM ALERT', en: true, col: '#fff', kind: 'red', y: Y0, t: 0.25, round: true, tc: '#fff', fs: 40 },
    { ic: 'link', text: 'വ്യാജ ഓഫർ ലിങ്കുകൾ', y: Y0 + 106, t: 0.55, col: C.amber, fs: 56 },
  ]);
  headline(21.17, 24.37, [
    { ic: 'shield-alert', text: 'ജാഗ്രത!', y: Y0, t: 21.45, col: C.amber, kind: 'amber', fs: 56, round: true },
    { ic: 'eye', text: 'ഏറ്റവും സൂക്ഷിക്കേണ്ട ഭാഗം', y: Y0 + 106, t: tw(7, 3), col: C.blue, fs: 46 },
  ]);
  headline(46.55, 57.95, [
    { ic: 'triangle-alert', text: 'പേരുകളിൽ വ്യാജ ലിങ്കുകൾ', y: Y0, t: 46.9, col: C.amber, kind: 'amber', fs: 46, round: true },
    { ic: 'link', text: 'Google Pay', en: true, tag: 'FAKE LINK', y: Y0 + 104, t: tw(15, 1), col: C.red, kind: 'red', fs: 40, is: 44 },
    { ic: 'link', text: 'PhonePe', en: true, tag: 'FAKE LINK', y: Y0 + 104 + 88, t: tw(15, 4), col: C.red, kind: 'red', fs: 40, is: 44 },
    { ic: 'link', text: 'Paytm', en: true, tag: 'FAKE LINK', y: Y0 + 104 + 176, t: tw(15, 7), col: C.red, kind: 'red', fs: 40, is: 44 },
  ]);
  headline(78.72, 82.38, [
    { ic: 'circle-help', text: 'ലിങ്ക് വന്നാൽ എന്ത് ചെയ്യും?', y: Y0, t: 78.95, col: C.blue, fs: 50, round: true },
  ]);
  headline(105.12, 113.7, [
    { ic: 'badge-check', text: 'ഒഫീഷ്യൽ ലിങ്ക് തന്നെയാണോ?', y: Y0, t: 105.3, col: C.green, kind: 'green', fs: 46, round: true, t1: 109.95 },
    { ic: 'eye', text: 'ഒഫീഷ്യൽ പോലെ തോന്നിയാലും', y: Y0, t: tw(31, 2) - 0.05, col: C.amber, kind: 'amber', fs: 46, round: true },
    { ic: 'ban', text: 'ഓപ്പൺ ചെയ്യരുത്!', y: Y0 + 106, t: tw(31, 8), col: C.red, kind: 'red', fs: 56 },
  ]);
  headline(130.58, 146.1, [
    { ic: 'layers', text: 'മറ്റ് ആപ്പുകളിലും ഇതുതന്നെ', y: Y0, t: 130.8, col: C.blue, fs: 42, round: true, t1: 139.0 },
    { ic: 'badge-check', text: 'ഒഫീഷ്യൽ വെബ്സൈറ്റ് / ആപ്പ്', y: Y0, t: tw(39, 8) - 0.05, col: C.green, kind: 'green', fs: 46, round: true },
    { ic: 'smartphone', text: 'PhonePe', en: true, y: Y0 + 104, t: tw(38, 1), col: '#A78BFA', fs: 40, is: 44 },
    { ic: 'smartphone', text: 'Paytm', en: true, y: Y0 + 104 + 88, t: tw(38, 4), col: C.blue, fs: 40, is: 44 },
    { ic: 'smartphone', text: 'CRED', en: true, y: Y0 + 104 + 176, t: tw(38, 8), col: '#C9CED8', fs: 40, is: 44 },
  ]);
  headline(163.72, 166.78, [
    { ic: 'calendar-check', text: 'വീണ്ടും കാണാം!', y: Y0, t: 164.0, col: C.cyan, fs: 56, round: true },
  ]);
})();
