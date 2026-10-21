/* part 2: split-screen explainers, phone demos, recap, outro, end card */
(function () {
  const { TL, el, pop, again, fade, card, chip, icon, hide, ft, to, shakeEl, flash, slam, C } = window;
  const stage = document.getElementById('stage');
  const PANEL = { x: 60, y: 70, w: 700, h: 800 };     // speaker panel in split scenes (matches the ffmpeg layout)
  const IMG = { gh: 'assets/gpay_home.jpg', go: 'assets/gpay_offers.jpg', ph: 'assets/phonepe_home.jpg', po: 'assets/phonepe_offerzone.jpg' };

  function panelFrame(t0, t1) {
    const f = el('abs', '', `left:${PANEL.x}px;top:${PANEL.y}px;width:${PANEL.w}px;height:${PANEL.h}px;border-radius:40px;box-sizing:border-box;border:3px solid rgba(255,255,255,.35);box-shadow:0 30px 80px rgba(0,0,0,.55)`);
    fade(f, t0, t1, 0.3);
    const tag = el('abs glass', `<span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#2D8CFF;box-shadow:0 0 12px #2D8CFF;margin-right:12px"></span><span style="font-weight:800;font-size:26px;letter-spacing:2px">MEGA BYTE</span>`,
      `left:${PANEL.x + 26}px;top:${PANEL.y + PANEL.h - 76}px;padding:12px 24px;border-radius:999px;display:flex;align-items:center`);
    fade(tag, t0 + 0.15, t1, 0.3);
  }
  function heading(text, ic, t0, t1, col = C.amber, w = 1030, fs = 44) {
    const h = el('abs glass', `${icon(ic, 50, col)}<span style="font-weight:800;font-size:${fs}px;letter-spacing:.6px">${text}</span>`,
      `left:820px;top:80px;width:${w}px;height:104px;box-sizing:border-box;display:flex;align-items:center;gap:20px;padding:0 34px;border-radius:26px`);
    pop(h, t0, t1, { y: -40, d: 0.5, ease: 'power3.out', oy: -20 });
    return h;
  }
  function typeText(host, text, t0, per = 0.045) {
    host.innerHTML = '';
    const spans = [...text].map((ch) => { const s = document.createElement('span'); s.textContent = ch; host.appendChild(s); return s; });
    spans.forEach((s, i) => { TL.set(s, { autoAlpha: 0 }, 0); TL.set(s, { autoAlpha: 1 }, t0 + i * per); });
    return spans;
  }
  function urlBar(o) {
    const { x, y, w, text, good, t0, t1, label } = o;
    const col = good ? C.green : C.red;
    const bar = el(`url glass abs ${good ? 'green' : 'red'}`, `${icon(good ? 'lock' : 'triangle-alert', 44, col)}<div class="u"></div>`, `left:${x}px;top:${y}px;width:${w}px`);
    const u = bar.querySelector('.u');
    pop(bar, t0, t1, { x: 80, d: 0.45 });
    const spans = typeText(u, text, t0 + 0.4, o.per || 0.04);
    let lab = null;
    if (label) {
      lab = el('abs', `<span style="font-weight:700;font-size:24px;letter-spacing:1.5px;color:#AEB6C6">${label}</span>`, `left:${x + 6}px;top:${y - 40}px`);
      pop(lab, t0, t1, { d: 0.3, y: 10 });
    }
    return { bar, u, spans, col };
  }
  function badge(parent, text, ic, good, t0, t1) {
    const b = el('abs', `<span class="tag ${good ? 'green' : 'red'}" style="font-size:26px;padding:8px 18px">${icon(ic, 26, good ? '#58E79A' : '#FF7A84', 3)} ${text}</span>`,
      `right:22px;top:36px`);
    parent.appendChild(b);
    ft(b, { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(2.4)' }, t0);
    TL.set(b, { autoAlpha: 0 }, 0);
    return b;
  }
  function note(x, y, w, text, sub, ic, col, t0, t1, kind = '') {
    const c = card({ x, y, w, h: 150, ic, title: text, sub, accent: col, kind });
    pop(c, t0, t1, { x: 110, d: 0.45 });
    return c;
  }

  // ================================================================ SP1: STEP 1 - DOMAIN CHECK  (105.0 - 129.2)
  (function () {
    const T0 = 104.95, T1 = 129.1;
    panelFrame(105.25, T1);
    // step badge (full frame, just before the split)
    const sb = el('abs glass', `<span style="font-weight:800;font-size:40px;color:${C.amber};letter-spacing:3px">STEP</span><span style="font-weight:800;font-size:150px;line-height:1">1</span>`,
      'left:1330px;top:380px;display:flex;align-items:center;gap:26px;padding:22px 52px;border-radius:34px');
    pop(sb, 104.85, 105.6, { s: 0.4, d: 0.4, ease: 'back.out(2.4)', out: 0.2 });
    heading('DOMAIN CHECK', 'scan-search', 105.4, T1, C.amber, 880);

    // fake link
    const f = urlBar({ x: 820, y: 250, w: 1030, text: 'https://gpay-9th-offer.xyz/claim', good: false, t0: 106.6, t1: T1, label: 'EXAMPLE — FAKE LINK', per: 0.055 });
    // highlight the domain part (measured from the real glyph positions)
    const r0 = f.spans[8].getBoundingClientRect(), r1 = f.spans[25].getBoundingClientRect();
    const hl = el('abs', '', `left:${r0.left - 10}px;top:${r0.top - 6}px;width:${r1.right - r0.left + 20}px;height:${r0.height + 12}px;border:5px solid #FFE14D;border-radius:14px;box-shadow:0 0 30px rgba(255,225,77,.6);transform-origin:0 50%`);
    hide(hl);
    ft(hl, { autoAlpha: 0, scaleX: 0.3 }, { autoAlpha: 1, scaleX: 1, duration: 0.45, ease: 'power3.out' }, 109.35);
    to(hl, { autoAlpha: 0, duration: 0.25 }, 113.0);
    const b1 = badge(f.bar, 'NOT OFFICIAL', 'circle-x', false, 112.9, T1);
    shakeEl(f.bar, 113.0, 8, 6, 0.35);

    // do not click - just read
    const t1_ = el('abs glass red', `<div style="position:relative;display:flex;justify-content:center">${icon('hand', 84, '#FF7A84', 2.2)}
        <div style="position:absolute;right:-22px;top:-22px;width:52px;height:52px;border-radius:50%;background:${C.red};display:flex;align-items:center;justify-content:center">${icon('x', 34, '#fff', 3.6)}</div></div>
        <div style="font-weight:800;font-size:34px;margin-top:16px;text-align:center">TAP CHEYYARUTHU</div>
        <div style="font-weight:500;font-size:22px;color:#FF9AA2;text-align:center">Click cheythu pariksha vendaa</div>`,
      'left:820px;top:430px;width:495px;height:260px;box-sizing:border-box;padding:34px 10px 0;border-radius:28px');
    pop(t1_, 115.35, 119.3, { y: 60, s: 0.7, d: 0.5, ease: 'back.out(2)' });
    const t2_ = el('abs glass green', `<div style="display:flex;justify-content:center">${icon('eye', 90, '#58E79A', 2.2)}</div>
        <div style="font-weight:800;font-size:34px;margin-top:16px;text-align:center">VAAYICHU NOKKUKA</div>
        <div style="font-weight:500;font-size:22px;color:#8FEBB8;text-align:center">Just read the link</div>`,
      'left:1355px;top:430px;width:495px;height:260px;box-sizing:border-box;padding:34px 10px 0;border-radius:28px');
    pop(t2_, 117.3, 119.3, { y: 60, s: 0.7, d: 0.5, ease: 'back.out(2)' });

    // official links
    const g = urlBar({ x: 820, y: 530, w: 1030, text: 'https://google.com', good: true, t0: 119.55, t1: T1, label: 'GOOGLE PAY', per: 0.06 });
    badge(g.bar, 'OFFICIAL', 'badge-check', true, 122.6, T1);
    const p = urlBar({ x: 820, y: 700, w: 1030, text: 'https://phonepe.com', good: true, t0: 126.4, t1: T1, label: 'PHONEPE', per: 0.06 });
    badge(p.bar, 'OFFICIAL', 'badge-check', true, 128.0, T1);
    // push the fake example back once the real ones show up
    to(f.bar, { opacity: 0.55, duration: 0.4 }, 119.6);
  })();

  // ================================================================ 129.3 - 138.4  official? / do not open
  (function () {
    const a = card({ x: 1290, y: 300, w: 570, h: 190, ic: 'scan-search', title: 'OFFICIAL LINK AANO?', sub: 'Website-inte peru check cheyyuka', accent: C.blue });
    pop(a, 130.8, 133.9, { x: 150, d: 0.5, ox: 60 });
    const b = card({ x: 1290, y: 300, w: 570, h: 230, ic: 'ban', title: 'OFFICIAL POLE<br>THONNIYAALUM', sub: 'OPEN CHEYYARUTHU', accent: C.red, kind: 'red', tc: '#FF7A84' });
    pop(b, 134.0, 138.3, { x: 150, d: 0.5, ox: 60 });
    shakeEl(b, 136.7, 9, 6, 0.35);
  })();

  // ================================================================ phone demo helper
  function phone(o) {
    const { x, y, t0, t1 } = o;
    const ph = el('phone', `<div class="notch"></div><div class="scr"></div>`, `left:${x}px;top:${y}px;width:374px;height:783px;border-radius:60px`);
    const scr = ph.querySelector('.scr');
    scr.style.cssText = 'left:12px;top:12px;right:12px;bottom:12px;border-radius:48px';
    pop(ph, t0, t1, { x: 160, s: 0.9, d: 0.7, ease: 'power3.out', ox: 120 });
    // slight 3D settle
    ft(ph, { rotationY: -22, transformPerspective: 1200 }, { rotationY: 0, duration: 0.8, ease: 'power3.out' }, t0);
    const SW = 350, SH = 759;
    const layers = {};
    const mkLayer = (key, src, tin, tout, dir) => {
      const zw = document.createElement('div');
      zw.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;transform-origin:0 0';
      zw.innerHTML = `<img src="${src}">`;
      const wrap = document.createElement('div');
      wrap.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;overflow:hidden';
      wrap.appendChild(zw);
      scr.appendChild(wrap);
      layers[key] = { wrap, zw };
      // slide in from the right (or just appear for the first layer)
      TL.set(wrap, { xPercent: dir === 0 ? 0 : 100 }, 0);
      if (dir !== 0) ft(wrap, { xPercent: 100 }, { xPercent: 0, duration: 0.55, ease: 'power3.inOut' }, tin);
      if (tout != null) to(wrap, { xPercent: -100, duration: 0.55, ease: 'power3.inOut' }, tout);
      return layers[key];
    };
    const zoom = (key, fx, fy, s, ta, tb, back) => {
      const L = layers[key];
      let tx = SW / 2 - fx * SW * s, ty = SH * 0.45 - fy * SH * s;
      tx = Math.min(0, Math.max(SW - SW * s, tx)); ty = Math.min(0, Math.max(SH - SH * s, ty));
      ft(L.zw, { x: 0, y: 0, scale: 1 }, { x: tx, y: ty, scale: s, duration: 0.7, ease: 'power3.inOut' }, ta);
      if (back != null) to(L.zw, { x: 0, y: 0, scale: 1, duration: 0.6, ease: 'power3.inOut' }, tb);
    };
    const mark = (key, kind, fx, fy, fw, fh, ta, tb) => {
      const L = layers[key];
      const r = document.createElement('div');
      r.className = kind === 'ring' ? 'ring' : 'rrect';
      const w = fw * SW, h = fh * SH;
      r.style.cssText = `left:${fx * SW - w / 2}px;top:${fy * SH - h / 2}px;width:${w}px;height:${h}px`;
      L.zw.appendChild(r);
      TL.set(r, { autoAlpha: 0 }, 0);
      ft(r, { autoAlpha: 0, scale: 1.6 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'back.out(2)' }, ta);
      to(r, { scale: 1.12, duration: 0.45, yoyo: true, repeat: 3, ease: 'sine.inOut' }, ta + 0.4);
      to(r, { autoAlpha: 0, duration: 0.25 }, tb);
    };
    return { ph, mkLayer, zoom, mark };
  }

  // ================================================================ SP2: GPay demo (138.7 - 152.4)
  (function () {
    const T0 = 138.8, T1 = 152.35;
    panelFrame(139.0, T1);
    const P = phone({ x: 1340, y: 78, t0: 139.3, t1: T1 });
    P.mkLayer('h', IMG.gh, 0, 143.95, 0);
    P.mkLayer('o', IMG.go, 143.95, null, 1);
    P.zoom('h', 0.375, 0.595, 1.55, 142.0, 143.35, true);
    P.mark('h', 'ring', 0.375, 0.595, 0.215, 0.1, 142.15, 143.8);
    P.mark('o', 'rect', 0.5, 0.348, 0.93, 0.185, 145.0, 147.0);
    P.mark('o', 'rect', 0.5, 0.75, 0.93, 0.44, 147.0, 149.2);
    const steps = [
      ['1', 'GPay app direct open cheyyuka', 140.45, C.blue, ''],
      ['2', 'Offers section nokkuka', 142.85, C.blue, ''],
      ['3', 'Avide thanne verify cheyyaam', 147.15, C.green, 'green'],
      ['✖', 'Offer illenkil → FAKE', 149.1, C.red, 'red'],
    ];
    steps.forEach(([n, txt, tt, col, kind], i) => {
      const s = el(`step glass abs ${kind}`, `<div class="n" style="background:${col}2e;color:${col}">${n}</div><div>${txt}</div>`,
        `left:820px;top:${190 + i * 128}px;width:470px`);
      pop(s, tt, T1, { x: -100, d: 0.45, ease: 'back.out(1.5)' });
    });
    heading('GPay OFFERS', 'smartphone', 139.0, T1, C.blue, 470, 38);
  })();

  // ================================================================ 152.4 - 155.6  100% FAKE (full-screen dim handled by ffmpeg)
  (function () {
    const a = el('big shadow-t', `<span style="color:${C.amber}">100%</span>`, 'left:430px;top:170px;font-size:250px;letter-spacing:-4px;text-shadow:0 12px 60px rgba(0,0,0,.7)');
    pop(a, 153.45, 155.5, { s: 0.3, d: 0.5, ease: 'back.out(2.2)', out: 0.2 });
    const st = el('stamp', 'FAKE', 'left:330px;top:420px;font-size:230px;border-width:16px;border-radius:30px;padding:0 50px;transform:rotate(-8deg)');
    hide(st);
    slam(st, 154.4, 3, 0.2);
    shakeEl(st, 154.62, 18, 8, 0.5);
    flash(154.6, 0.45, 0.25);
    to(st, { autoAlpha: 0, duration: 0.2 }, 155.4);
    const lk = card({ x: 1290, y: 180, w: 570, h: 130, ic: 'link', title: 'EE LINK', accent: C.red, kind: 'red', tc: '#FF7A84' });
    pop(lk, 152.55, 155.4, { x: 150, d: 0.45, ox: 60 });
  })();

  // ================================================================ SP3: PhonePe / Paytm / CRED (155.9 - 171.0)
  (function () {
    const T1 = 170.95;
    panelFrame(156.1, T1);
    heading('MATTU PLATFORMUKAL', 'layers', 156.0, T1, C.blue, 470, 30);
    const P = phone({ x: 1340, y: 78, t0: 157.9, t1: T1 });
    P.mkLayer('h', IMG.ph, 0, 160.55, 0);
    P.mkLayer('o', IMG.po, 160.55, null, 1);
    P.zoom('h', 0.141, 0.436, 1.6, 158.4, 160.0, true);
    P.mark('h', 'ring', 0.141, 0.436, 0.27, 0.12, 158.6, 160.5);
    P.mark('o', 'rect', 0.5, 0.425, 0.93, 0.22, 161.3, 164.0);
    P.mark('o', 'rect', 0.5, 0.65, 0.93, 0.17, 165.0, 167.8);
    // platform pills
    [['PhonePe', 158.05, C.blue], ['Paytm', 159.0, C.blue], ['CRED', 160.05, C.blue]].forEach(([t, tt, col], i) => {
      const s = el('chip glass abs', `${icon('badge-check', 38, col)}<span>${t}</span>`, `left:820px;top:${204 + i * 100}px;width:470px;height:84px;font-size:34px`);
      pop(s, tt, T1, { x: -100, d: 0.45, ease: 'back.out(1.5)' });
    });
    const o1 = el('step glass green abs', `<div class="n" style="background:#3DDC842e;color:${C.green}">${icon('globe', 32, C.green)}</div><div>Official website</div>`, 'left:820px;top:520px;width:470px');
    pop(o1, 164.2, T1, { x: -100, d: 0.45, ease: 'back.out(1.5)' });
    const o2 = el('step glass green abs', `<div class="n" style="background:#3DDC842e;color:${C.green}">${icon('smartphone', 32, C.green)}</div><div>Official app</div>`, 'left:820px;top:636px;width:470px');
    pop(o2, 165.6, T1, { x: -100, d: 0.45, ease: 'back.out(1.5)' });
    const o3 = el('step glass abs', `<div class="n" style="background:#FFB0202e;color:${C.amber}">${icon('ticket-percent', 32, C.amber)}</div><div>Offers avar thanne list cheyyum</div>`, 'left:820px;top:752px;width:470px');
    pop(o3, 167.9, T1, { x: -100, d: 0.45, ease: 'back.out(1.5)' });
  })();

  // ================================================================ 171.0 - 174.4  check official source
  (function () {
    const c = card({ x: 1290, y: 300, w: 570, h: 200, ic: 'badge-check', title: 'OFFICIAL SOURCE-IL', sub: 'Parishodhikkuka', accent: C.green, kind: 'green' });
    pop(c, 171.15, 174.35, { x: 150, d: 0.5, ox: 60 });
  })();

  // ================================================================ 174.6 - 181.7  oru cheriya ashraddha mathi
  (function () {
    const t = el('big glass', `<div style="font-size:60px;color:#fff">ORU CHERIYA</div><div style="font-size:78px;color:#FF6B76;margin-top:6px">ASHRADDHA<br>MATHI</div>`, 'left:1290px;top:200px;width:570px;box-sizing:border-box;padding:22px 30px;line-height:1.05;white-space:normal');
    pop(t, 174.7, 181.6, { x: 120, d: 0.55, ox: 50 });
    const bal = el('abs glass', `<div style="font-weight:600;font-size:23px;color:#B9C0CE;letter-spacing:1.5px">ACCOUNT BALANCE <span style="color:#7E879A">(example)</span></div>
      <div style="position:relative;height:104px;margin-top:8px">
        <span class="b b0" style="position:absolute;left:0;top:0;font-weight:800;font-size:90px;color:${C.green};white-space:nowrap">₹25,000</span>
        <span class="b b1" style="position:absolute;left:0;top:0;font-weight:800;font-size:90px;color:${C.amber};white-space:nowrap">₹11,400</span>
        <span class="b b2" style="position:absolute;left:0;top:0;font-weight:800;font-size:90px;color:${C.red};white-space:nowrap">₹2,300</span>
        <span class="b b3" style="position:absolute;left:0;top:0;font-weight:800;font-size:90px;color:${C.red};white-space:nowrap">₹0</span></div>`,
      'left:1290px;top:600px;width:570px;box-sizing:border-box;padding:24px 30px');
    pop(bal, 175.5, 181.6, { y: 60, d: 0.5, ox: 40 });
    const b = [0, 1, 2, 3].map((i) => bal.querySelector('.b' + i));
    b.forEach(hide);
    ft(b[0], { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, 175.7);
    to(b[0], { autoAlpha: 0, duration: 0.12 }, 176.9);
    ft(b[1], { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.15 }, 176.92);
    to(b[1], { autoAlpha: 0, duration: 0.12 }, 177.4);
    ft(b[2], { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.15 }, 177.42);
    to(b[2], { autoAlpha: 0, duration: 0.12 }, 177.9);
    slam(b[3], 177.92, 1.6, 0.2);
    shakeEl(bal, 178.1, 10, 6, 0.4);
    const m = chip({ x: 1290, y: 800, w: 570, text: 'MAANAM POKUM', ic: 'heart-crack', color: C.red, kind: 'red' });
    m.style.height = '84px';
    pop(m, 178.65, 181.6, { x: 140, d: 0.45, ox: 50 });
  })();

  // ================================================================ 181.8 - 187.6  recap checklist
  (function () {
    const h = el('abs glass', `${icon('list-checks', 44, C.amber)}<span style="font-weight:800;font-size:33px;letter-spacing:.6px">ORKKUKA</span>`,
      'left:1290px;top:210px;width:570px;height:92px;box-sizing:border-box;display:flex;align-items:center;gap:16px;padding:0 26px;border-radius:24px');
    pop(h, 182.0, 187.5, { x: 120, d: 0.45 });
    const rows = [['x', 'LINK CLICK CHEYYARUTHU', 183.3, C.red, 'red'], ['x', 'SHARE CHEYYARUTHU', 185.1, C.red, 'red'], ['check', 'OFFICIAL APP-IL VERIFY', 186.75, C.green, 'green']];
    rows.forEach(([ic, t, tt, col, kind], i) => {
      const c = el(`chip glass ${kind} abs`, `<div style="width:52px;height:52px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;flex:none">${icon(ic, 34, '#fff', 3.6)}</div><span style="font-size:29px">${t}</span>`,
        `left:1290px;top:${330 + i * 120}px;width:570px;height:98px;padding:0 22px`);
      pop(c, tt, 187.5, { x: 140, d: 0.45, ease: 'back.out(1.5)' });
    });
  })();

  // ================================================================ 187.8 - 193.3  share this video
  (function () {
    const c = el('abs glass', `<div style="position:relative;width:96px;height:96px;border-radius:50%;background:${C.blue};display:flex;align-items:center;justify-content:center;flex:none">${icon('share-2', 54, '#fff', 2.4)}</div>
      <div><div style="font-weight:800;font-size:40px;line-height:1.05">SHARE THIS<br>VIDEO</div></div>`,
      'left:1290px;top:260px;width:570px;height:170px;box-sizing:border-box;display:flex;align-items:center;gap:26px;padding:0 30px;border-radius:28px');
    pop(c, 189.35, 193.25, { x: 140, d: 0.5, ease: 'back.out(1.6)', ox: 60 });
    const ring = el('abs', '', 'left:1316px;top:297px;width:96px;height:96px;border-radius:50%;border:6px solid #4DA3FF');
    hide(ring);
    ft(ring, { autoAlpha: 0.9, scale: 1 }, { autoAlpha: 0, scale: 2.4, duration: 0.8, repeat: 3, ease: 'power2.out' }, 189.9);
    const n = card({ x: 1290, y: 470, w: 570, h: 150, ic: 'users', title: 'NAALAAL ARIYATTE', accent: C.amber });
    pop(n, 190.3, 193.25, { x: 140, d: 0.5, ox: 60 });
    // little avatars popping
    [0, 1, 2, 3].forEach((i) => {
      const a = el('abs', icon(i % 2 ? 'user' : 'smile', 52, '#fff', 2.2), `left:${1330 + i * 120}px;top:670px;width:92px;height:92px;border-radius:50%;background:${[C.blue, C.green, C.amber, '#B77CFF'][i]};display:flex;align-items:center;justify-content:center`);
      pop(a, 191.3 + i * 0.22, 193.2, { s: 0.2, y: 40, d: 0.45, ease: 'back.out(2.4)' });
    });
  })();

  // ================================================================ 193.5 - 200  subscribe + nandi
  (function () {
    const btn = el('abs', `<div class="sb" style="display:flex;align-items:center;gap:18px;border-radius:999px;background:#FF2E3E;padding:22px 44px 22px 34px;box-shadow:0 14px 44px rgba(255,46,62,.5)"><span class="bl">${icon('bell', 52, '#fff', 2.4)}</span>
        <span style="position:relative;display:inline-block;width:330px;height:56px"><span class="t1s" style="position:absolute;left:0;top:0;font-weight:800;font-size:46px;letter-spacing:2px;line-height:56px;white-space:nowrap">SUBSCRIBE</span><span class="t2s" style="position:absolute;left:0;top:0;font-weight:800;font-size:40px;letter-spacing:1px;line-height:56px;white-space:nowrap">SUBSCRIBED</span></span></div>`,
      'left:1290px;top:300px');
    pop(btn, 196.65, 199.95, { s: 0.5, d: 0.5, ease: 'back.out(2.2)', ox: 40 });
    const sb = btn.querySelector('.sb'), t1s = btn.querySelector('.t1s'), t2s = btn.querySelector('.t2s'), bl = btn.querySelector('.bl');
    TL.set(t2s, { autoAlpha: 0 }, 0);
    const cur = el('abs', icon('mouse-pointer-click', 70, '#fff', 2.2), 'left:1720px;top:430px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.6))');
    hide(cur);
    ft(cur, { autoAlpha: 0, x: 80, y: 90 }, { autoAlpha: 1, x: -140, y: -70, duration: 0.8, ease: 'power2.inOut' }, 196.7);
    to(cur, { scale: 0.8, duration: 0.1, yoyo: true, repeat: 1 }, 197.45);
    to(cur, { autoAlpha: 0, duration: 0.2 }, 197.95);
    to(sb, { backgroundColor: '#3a3f4b', duration: 0.2 }, 197.5);
    to(t1s, { autoAlpha: 0, duration: 0.12 }, 197.5);
    to(t2s, { autoAlpha: 1, duration: 0.12 }, 197.55);
    to(bl, { rotation: 18, duration: 0.08, yoyo: true, repeat: 7, ease: 'sine.inOut', transformOrigin: '50% 10%' }, 197.65);
    const n = el('big glass', `NANDI<div style="font-size:46px;font-weight:700;color:#E6EAF3;margin-top:8px;letter-spacing:2px">NAMASKAARAM 🙏</div>`, 'left:1290px;top:520px;width:570px;box-sizing:border-box;padding:22px 30px;font-size:110px;line-height:1.02');
    pop(n, 198.3, 199.95, { y: 40, s: 0.8, d: 0.55, ease: 'back.out(1.8)', ox: 0, os: 1 });
  })();

  // ================================================================ end card (200.0 - 206.6)
  (function () {
    const T0 = 200.0, T1 = 206.6;
    const glow = el('abs', '', 'left:610px;top:20px;width:700px;height:700px;border-radius:50%;background:radial-gradient(circle,rgba(45,140,255,.34),rgba(45,140,255,0) 68%)');
    fade(glow, T0 + 0.1, T1, 0.6);
    to(glow, { scale: 1.12, duration: 1.6, yoyo: true, repeat: 3, ease: 'sine.inOut' }, T0 + 1.0);
    const logo = el('abs', `<img src="assets/logo.png" style="width:100%;height:100%;display:block;filter:drop-shadow(0 20px 50px rgba(0,0,0,.65))">`, 'left:710px;top:70px;width:500px;height:500px');
    hide(logo);
    ft(logo, { autoAlpha: 0, scale: 0.5, rotation: -20 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: 0.9, ease: 'back.out(1.6)' }, T0 + 0.15);
    to(logo, { y: -10, duration: 1.6, yoyo: true, repeat: 3, ease: 'sine.inOut' }, T0 + 1.2);
    to(logo, { autoAlpha: 0, duration: 0.4 }, T1 - 0.4);
    const name = el('abs', `<div style="font-weight:600;font-size:36px;color:#BFD6F5;letter-spacing:6px">THANKS FOR WATCHING</div>`, 'left:0;right:0;top:612px;text-align:center');
    pop(name, T0 + 0.7, T1 - 0.1, { y: 40, d: 0.7, ease: 'power3.out', out: 0.4 });
    const sub = el('abs', `<div style="display:inline-flex;align-items:center;gap:16px;border-radius:999px;background:#FF2E3E;padding:18px 44px 18px 30px;box-shadow:0 14px 44px rgba(255,46,62,.5)">${icon('bell-ring', 44, '#fff', 2.4)}<span style="font-weight:800;font-size:40px;letter-spacing:2px">SUBSCRIBE</span></div>`,
      'left:0;right:0;top:780px;text-align:center');
    pop(sub, T0 + 1.3, T1 - 0.1, { y: 40, s: 0.6, d: 0.6, ease: 'back.out(2)', out: 0.4 });
    to(sub, { scale: 1.06, duration: 0.6, yoyo: true, repeat: 5, ease: 'sine.inOut' }, T0 + 2.0);
  })();

  window.seek = (f) => { TL.time(f / 30, false); };
})();
