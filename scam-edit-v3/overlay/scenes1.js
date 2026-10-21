/* key-point scenes, part 1 */
(function () {
  const V = window.V3;
  const { el, hide, ft, to, set, pop, fade, shakeEl, slam, flash, tw, te, kscene, card, phone, panzoom, mark, layerIn, icon, C, TL, SC } = V;
  const ml = (txt, size, color = '#fff', extra = '') => `<div class="t-ml" style="font-size:${size}px;color:${color};${extra}">${txt}</div>`;
  const shade = (g, t0, t1) => {
    const s = el('abs', '', 'left:0;top:0;width:1150px;height:1080px;background:linear-gradient(90deg,rgba(2,8,22,.78),rgba(2,8,22,.45) 70%,rgba(2,8,22,0))', g);
    return s;
  };
  const toast = (g, x, y, w, ic, txt, col, t0, t1, fs = 36) => {
    const e = el('abs glass', `${icon(ic, 52, col)}<span class="t-ml" style="font-size:${fs}px">${txt}</span>`,
      `left:${x}px;top:${y}px;width:${w}px;height:112px;display:flex;align-items:center;gap:20px;padding:0 28px;box-sizing:border-box;border-radius:26px`, g);
    pop(e, t0, t1, { x: 120, d: 0.45, ease: 'back.out(1.4)', out: 0.25 });
    return e;
  };

  // ------------------------------------------------------------------ the scam message (6000 / 9000 / 10000)
  kscene('wa', (g, t0, t1) => {
    const P = phone({ x: 1440, y: 150, w: 410, h: 780, imgs: ['wa'], parent: g });
    pop(P.ph, t0 + 0.12, null, { x: 170, s: 0.92, d: 0.7, ease: 'power3.out' });
    ft(P.ph, { rotationY: -24, transformPerspective: 1400 }, { rotationY: 0, duration: 0.8, ease: 'power3.out' }, t0 + 0.12);
    to(P.ph, { y: -8, duration: 1.8, yoyo: true, repeat: 3, ease: 'sine.inOut' }, t0 + 1);
    const lab = el('abs glass', `${icon('gift', 52, C.amber)}${ml('9-ാം വാർഷിക<br>സമ്മാനം', 40)}`,
      'left:980px;top:236px;display:flex;align-items:center;gap:18px;padding:16px 30px 16px 22px;border-radius:30px', g);
    pop(lab, t0 + 0.3, t1, { x: -60, d: 0.5, ease: 'power3.out' });
    const amts = ['₹6,000', '₹9,000', '₹10,000'];
    const times = [tw(1, 8), tw(2, 2), tw(2, 5)];
    amts.forEach((a, i) => {
      const e = el('big en', a, `left:984px;top:400px;font-weight:800;font-size:106px;line-height:1;color:${C.amber};text-shadow:0 0 60px rgba(255,176,32,.55),0 8px 30px rgba(0,0,0,.6)`, g);
      hide(e);
      ft(e, { autoAlpha: 0, y: 60, scale: 0.9 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.3, ease: 'back.out(1.8)' }, times[i] - 0.05);
      if (i < 2) to(e, { autoAlpha: 0, y: -50, duration: 0.2, ease: 'power2.in' }, times[i + 1] - 0.08);
    });
    const sub = el('abs', ml('ക്യാഷ്ബാക്ക്<br>ക്ലെയിം ചെയ്യൂ 👇', 44, '#CFE0FF'), 'left:988px;top:560px', g);
    pop(sub, tw(1, 8), t1, { y: 20, d: 0.4 });
    mark(P, 0, 0.43, 0.158, 0.30, 0.055, tw(1, 8) - 0.05, 5.0);
    mark(P, 0, 0.03, 0.648, 0.20, 0.046, tw(2, 2), 6.0);
    mark(P, 0, 0.03, 0.545, 0.46, 0.05, 6.9, null, C.red);
    const warn = el('abs glass red', `${icon('triangle-alert', 50, C.red)}${ml('വ്യാജ ലിങ്ക്!', 52, '#FF8E98')}`,
      'left:980px;top:760px;display:flex;align-items:center;gap:16px;padding:14px 34px 14px 24px;border-radius:26px', g);
    pop(warn, 7.1, t1, { x: -60, d: 0.45 });
    shakeEl(warn, 7.45, 8, 6, 0.3);
  });

  // ------------------------------------------------------------------ B-roll: WhatsApp messages / Facebook posts
  kscene('b1', (g, t0, t1) => {
    shade(g);
    const l = el('abs glass', `${icon('message-circle', 62, C.green)}${ml('WhatsApp സന്ദേശങ്ങൾ', 56)}`,
      'left:980px;top:226px;display:flex;align-items:center;gap:20px;padding:20px 40px 20px 28px;border-radius:999px', g);
    pop(l, t0 + 0.2, t1, { y: -30, d: 0.45 });
    toast(g, 980, 380, 860, 'gift', '₹10,000 ക്യാഷ്ബാക്ക് നേടൂ!', C.amber, 9.0, t1 - 0.1, 40);
    toast(g, 980, 516, 860, 'ticket-percent', 'നിങ്ങൾക്കായി ഒരു ഗിഫ്റ്റ്!', C.amber, 10.2, t1 - 0.1, 40);
    toast(g, 980, 652, 860, 'zap', 'അവസാന അവസരം — ലിങ്ക് തുറക്കൂ', C.amber, 11.1, t1 - 0.1, 40);
  });
  kscene('b2', (g, t0, t1) => {
    shade(g);
    const l = el('abs glass', `${icon('thumbs-up', 62, C.blue)}${ml('Facebook പോസ്റ്റുകൾ', 52)}`,
      'left:1000px;top:226px;display:flex;align-items:center;gap:20px;padding:20px 40px 20px 28px;border-radius:999px', g);
    pop(l, t0 + 0.2, t1, { y: -30, d: 0.45 });
    toast(g, 1470, 470, 400, 'ticket-percent', '90% OFF!', C.amber, 13.3, t1 - 0.1, 34);
    toast(g, 1470, 600, 400, 'gift', 'Free gift!', C.amber, 14.3, t1 - 0.1, 34);
    toast(g, 1470, 730, 400, 'forward', 'Share ചെയ്യൂ', C.amber, 15.0, t1 - 0.1, 34);
  });

  // ------------------------------------------------------------------ "sathyamaano?" -> "orikkalumalla!"
  kscene('never', (g, t0, t1) => {
    const q = el('big t-ml', `സത്യമാണോ<span style="color:${C.amber}">?</span>`, 'left:980px;top:340px;font-size:130px;text-shadow:0 8px 40px rgba(0,0,0,.6)', g);
    pop(q, tw(6, 3) - 0.12, tw(6, 4) - 0.02, { s: 0.7, d: 0.35, ease: 'back.out(2)', out: 0.1 });
    const n = el('big t-ml', 'ഒരിക്കലുമല്ല!', `left:972px;top:340px;font-size:116px;color:${C.red};-webkit-text-stroke:6px rgba(10,0,2,.72);paint-order:stroke fill;text-shadow:0 8px 50px rgba(255,77,90,.6)`, g);
    hide(n);
    slam(n, tw(6, 4) - 0.02, 2.6, 0.2);
    shakeEl(n, tw(6, 4) + 0.2, 12, 8, 0.4);
    flash(tw(6, 4) + 0.18, 0.4, 0.25, '#ff3a48');
    const st = el('stamp t-ml', 'തട്ടിപ്പ്!', 'left:1210px;top:600px;font-size:96px;transform:rotate(-8deg)', g);
    hide(st);
    slam(st, tw(6, 4) + 0.5, 2.2, 0.16);
    shakeEl(st, tw(6, 4) + 0.7, 8, 6, 0.3);
  });

  // ------------------------------------------------------------------ what can be lost
  kscene('loss', (g, t0, t1) => {
    shade(g);
    const h = el('abs glass', `${icon('triangle-alert', 52, C.amber)}${ml('നഷ്ടപ്പെടാവുന്നത്', 50)}`,
      'left:980px;top:226px;display:flex;align-items:center;gap:18px;padding:14px 38px 14px 24px;border-radius:999px', g);
    pop(h, t0 + 0.2, t1, { y: -30, d: 0.45 });
    const items = [
      ['banknote', 'പണം നഷ്ടം', 'Money', C.amber, tw(8, 2) - 0.1, 'amber'],
      ['smartphone', 'ഡാറ്റ നഷ്ടം', 'Phone / computer data', C.blue, tw(8, 9) - 0.1, ''],
      ['user-x', 'മാനഹാനി', 'Reputation', C.red, tw(9, 4) - 0.1, 'red'],
    ];
    items.forEach(([ic, title, sub, col, t, kind], i) => {
      const c = card({ x: 980, y: 336 + i * 232, w: 860, h: 206, ic, title, sub, accent: col, kind, tsize: 76, isize: 104, parent: g });
      pop(c, t, t1, { x: 150, d: 0.5, ease: 'back.out(1.5)', ox: 60 });
      to(c, { scale: 1.035, duration: 0.18, yoyo: true, repeat: 1 }, t + 0.5);
    });
    shakeEl(g.children[g.children.length - 1], tw(9, 4) + 0.1, 10, 6, 0.35);
  });

  // ------------------------------------------------------------------ the link
  kscene('link', (g, t0, t1) => {
    shade(g);
    const bub = el('abs glass', `<div style="display:flex;align-items:center;gap:16px">${icon('message-circle', 44, C.green)}<span class="en" style="font-weight:600;font-size:28px;color:#B9C8E6">അജ്ഞാത നമ്പർ • ഇപ്പോൾ</span></div>
      ${ml('Google Pay വാർഷിക സമ്മാനം ₹6,000', 40, '#fff', 'margin-top:14px')}
      <div class="en lnk" style="margin-top:16px;font-weight:600;font-size:36px;color:#6BB7FF;text-decoration:underline;word-break:break-all">https://yubx.orcwk.xyz/FV1ziinym/90d84096…</div>`,
      'left:980px;top:330px;width:850px;box-sizing:border-box;padding:30px 36px 34px', g);
    pop(bub, t0 + 0.2, 38.8, { x: 120, d: 0.5, ease: 'power3.out', out: 0.12, os: 1 });
    const lk = bub.querySelector('.lnk');
    const rr = el('abs', '', `left:${980 + lk.offsetLeft - 12}px;top:${330 + lk.offsetTop - 10}px;width:${lk.offsetWidth + 24}px;height:${lk.offsetHeight + 20}px;border:6px solid #FFE14D;border-radius:20px;box-shadow:0 0 34px rgba(255,225,77,.65)`, g);
    pop(rr, tw(11, 4) - 0.1, 38.8, { s: 1.12, d: 0.3, ease: 'back.out(2)', out: 0.1, os: 1 });
    const lab = el('abs glass red', `${icon('link', 46, C.red)}${ml('ഈ ലിങ്ക്', 50, '#FF8E98')}`,
      'left:980px;top:236px;display:flex;align-items:center;gap:16px;padding:14px 34px 14px 24px;border-radius:999px', g);
    pop(lab, tw(11, 4) - 0.1, 38.8, { y: -26, d: 0.4, out: 0.12 });
    // finger taps the link
    const cur = el('abs', icon('mouse-pointer-click', 96, '#fff', 2.2), 'left:1720px;top:760px;filter:drop-shadow(0 8px 16px rgba(0,0,0,.7))', g);
    hide(cur);
    ft(cur, { autoAlpha: 0, x: 80, y: 120 }, { autoAlpha: 1, x: -380, y: -230, duration: 0.7, ease: 'power2.inOut' }, 37.75);
    to(cur, { scale: 0.78, duration: 0.1, yoyo: true, repeat: 1 }, tw(12, 3) + 0.1);
    const rip = el('abs', '', 'left:1280px;top:490px;width:120px;height:120px;border-radius:50%;border:8px solid rgba(255,255,255,.9)', g);
    hide(rip);
    ft(rip, { autoAlpha: 0.9, scale: 0.2 }, { autoAlpha: 0, scale: 3.2, duration: 0.55, ease: 'power2.out' }, tw(12, 3) + 0.15);
    to(cur, { autoAlpha: 0, duration: 0.2 }, tw(12, 4) + 0.1);
    // hacked
    flash(38.82, 0.55, 0.3, '#ff2a3a');
    const hd = el('abs glass red', `${icon('shield-alert', 54, C.red)}${ml('ലിങ്ക് തുറന്നാൽ…', 56, '#FF8E98')}`,
      'left:980px;top:226px;display:flex;align-items:center;gap:18px;padding:14px 38px 14px 24px;border-radius:999px', g);
    pop(hd, 38.9, t1, { y: -30, d: 0.45 });
    const its = [['database', 'ഡാറ്റ ചോരും', 'Data leak', C.blue, tw(12, 10) - 0.1], ['user-x', 'മാനനഷ്ടം', 'Reputation', C.red, tw(13, 1) - 0.1], ['banknote', 'ധനനഷ്ടം', 'Money loss', C.amber, tw(13, 2) - 0.1]];
    its.forEach(([ic, title, sub, col, t], i) => {
      const c = card({ x: 980, y: 336 + i * 214, w: 860, h: 190, ic, title, sub, accent: col, kind: 'red', tsize: 70, isize: 96, parent: g });
      pop(c, t, t1, { x: 150, d: 0.45, ox: 60 });
      shakeEl(c, t + 0.3, 8, 6, 0.3);
    });
  });
})();
