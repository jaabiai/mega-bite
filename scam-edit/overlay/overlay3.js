/* part 3: Megabyte welcome stinger, inserted after the hook.  Everything written above is on the "pre-insert" timeline;
   here the timeline is opened by DLT seconds at INS_T, and the stinger fills the gap. */
(function () {
  const { TL, el, hide, ft, to, flash, C } = window;
  const FPS = 30;
  const INS_T = 719 / FPS, DLT = 84 / FPS;          // 23.9667 s, 2.8 s
  const T = INS_T;                                   // stinger start

  // open the gap: everything that starts at/after the insertion point moves by DLT
  TL.getChildren(false, true, true).forEach((c) => {
    const tg = (c.targets && c.targets()) || [];
    if (tg.some((e) => e && e.closest && e.closest('.cap'))) return;      // captions are placed per piece in overlay.js
    const s = c.startTime();
    if (s >= INS_T - 1e-4) c.startTime(s + DLT);
  });
  window.__ins = { INS_T, DLT };

  // ---------------------------------------------------------------- stinger layer (opaque, on top of everything)
  const bg = el('abs', '', 'left:0;top:0;width:1920px;height:1080px;background:radial-gradient(ellipse 70% 75% at 50% 46%,#0B2A63 0%,#06173A 38%,#030A1C 72%,#02050F 100%)');
  hide(bg);
  const vig = el('abs', '', 'left:0;top:0;width:1920px;height:1080px;background:radial-gradient(ellipse 100% 100% at 50% 50%,rgba(0,0,0,0) 55%,rgba(0,0,0,.55) 100%)');
  hide(vig);
  const glow = el('abs', '', 'left:460px;top:90px;width:1000px;height:1000px;border-radius:50%;background:radial-gradient(circle,rgba(45,140,255,.55),rgba(45,140,255,0) 66%)');
  hide(glow);
  // horizontal light streaks
  const mkStreak = (top, h, w) => el('abs', '', `left:${(1920 - w) / 2}px;top:${top}px;width:${w}px;height:${h}px;background:linear-gradient(90deg,rgba(77,170,255,0),rgba(150,210,255,.95) 50%,rgba(77,170,255,0));border-radius:99px;filter:blur(1px)`);
  const st1 = mkStreak(538, 3, 1700), st2 = mkStreak(542, 14, 900);
  hide(st1); hide(st2);
  // rings
  const ring = (sz, bw, col) => el('abs', '', `left:${(1920 - sz) / 2}px;top:${540 - sz / 2 + 0}px;width:${sz}px;height:${sz}px;border-radius:50%;box-sizing:border-box;border:${bw}px solid ${col}`);
  const r1 = ring(640, 5, 'rgba(120,200,255,.9)'), r2 = ring(640, 2, 'rgba(255,255,255,.7)');
  hide(r1); hide(r2);
  // logo + shine
  const LS = 600;
  const logoBox = el('abs', `<img src="assets/logo.png" style="width:100%;height:100%;display:block;filter:drop-shadow(0 24px 60px rgba(0,0,0,.6))">
      <div class="shine" style="position:absolute;left:0;top:0;width:100%;height:100%;border-radius:50%;overflow:hidden"><div style="position:absolute;top:-10%;left:-40%;width:28%;height:120%;transform:rotate(18deg);background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.65),rgba(255,255,255,0))"></div></div>`,
    `left:${(1920 - LS) / 2}px;top:${540 - LS / 2 + 28}px;width:${LS}px;height:${LS}px`);
  hide(logoBox);
  const shine = logoBox.querySelector('.shine > div');
  const wt = el('abs', `<div style="font-weight:700;font-size:58px;letter-spacing:22px;text-indent:22px;color:#D7E8FF;text-shadow:0 0 28px rgba(77,170,255,.8)">WELCOME TO</div>`,
    'left:0;right:0;top:140px;text-align:center');
  hide(wt);
  const all = [bg, vig, glow, logoBox, wt];

  // timeline (stinger-relative seconds)
  const A = (s) => T + s;
  ft(bg, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2, ease: 'power1.out' }, A(0));
  ft(vig, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, A(0));
  ft(glow, { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.9, ease: 'power2.out' }, A(0.2));
  to(glow, { scale: 1.08, duration: 1.0, yoyo: true, repeat: 1, ease: 'sine.inOut' }, A(1.1));
  // streaks sweep out from the centre just before the logo hits
  ft(st1, { autoAlpha: 1, scaleX: 0 }, { autoAlpha: 1, scaleX: 1, duration: 0.32, ease: 'power3.out' }, A(0.12));
  ft(st2, { autoAlpha: 1, scaleX: 0 }, { autoAlpha: 1, scaleX: 1, duration: 0.3, ease: 'power3.out' }, A(0.14));
  to(st1, { autoAlpha: 0, duration: 0.3 }, A(0.55));
  to(st2, { autoAlpha: 0, duration: 0.25 }, A(0.5));
  // logo impact at A(0.5)
  ft(logoBox, { autoAlpha: 0, scale: 1.5, rotation: -6 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: 0.42, ease: 'power4.out' }, A(0.3));
  to(logoBox, { scale: 1.035, duration: 1.0, yoyo: true, repeat: 1, ease: 'sine.inOut' }, A(0.85));
  ft(r1, { autoAlpha: 0.9, scale: 0.9 }, { autoAlpha: 0, scale: 2.0, duration: 0.7, ease: 'power2.out' }, A(0.5));
  ft(r2, { autoAlpha: 0.8, scale: 0.9 }, { autoAlpha: 0, scale: 1.55, duration: 0.55, ease: 'power2.out' }, A(0.5));
  flash(A(0.48), 0.38, 0.28);
  // "WELCOME TO" tracks in as the voice starts
  ft(wt, { autoAlpha: 0, y: -26, letterSpacing: '46px' }, { autoAlpha: 1, y: 0, letterSpacing: '22px', duration: 0.55, ease: 'power3.out' }, A(0.62));
  // shine over the logo on "Mega Byte"
  ft(shine, { x: 0 }, { x: LS * 1.9, duration: 0.7, ease: 'power1.inOut' }, A(1.35));
  // exit: quick scale-up + fade, the speaker is revealed underneath
  to(logoBox, { scale: 1.12, duration: 0.3, ease: 'power2.in' }, A(2.5));
  to(wt, { autoAlpha: 0, duration: 0.2 }, A(2.5));
  to(glow, { autoAlpha: 0, duration: 0.3 }, A(2.5));
  to(bg, { autoAlpha: 0, duration: 0.3, ease: 'power1.in' }, A(2.5));
  to(vig, { autoAlpha: 0, duration: 0.3, ease: 'power1.in' }, A(2.5));
  to(logoBox, { autoAlpha: 0, duration: 0.22, ease: 'power1.in' }, A(2.58));
  flash(A(2.52), 0.18, 0.25);

  window.seek = (f) => { TL.time(f / FPS, false); };
})();
