/* 9:16 reel overlay - deterministic: renderAt(t) draws every graphic for reel-time t (seconds). */
(function () {
  const clamp = (x, a = 0, b = 1) => Math.min(Math.max(x, a), b);
  const lerp = (a, b, k) => a + (b - a) * k;
  const eo = (x) => 1 - Math.pow(1 - clamp(x), 3);
  const eio = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const back = (x) => { x = clamp(x); const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const sm = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
  const CREAM = [255, 246, 232], AMBERC = [255, 197, 61];
  const mix = (a, b, k) => `rgb(${Math.round(lerp(a[0], b[0], k))},${Math.round(lerp(a[1], b[1], k))},${Math.round(lerp(a[2], b[2], k))})`;
  const el = (cls, html, tag = 'div') => { const e = document.createElement(tag); e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
  const ICON = {
    check: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    play: '<svg viewBox="0 0 24 24" width="58" height="58"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>',
    bell: '<svg viewBox="0 0 24 24" width="62" height="62"><path fill="currentColor" d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>',
    cursor: '<svg viewBox="0 0 24 24"><path fill="#fff" stroke="#111" stroke-width="1.2" d="M4 2l15 9.5-6.3 1.4 3.6 6.6-2.9 1.6-3.6-6.6L5 18z"/></svg>',
  };
  let TL, layer, capsEl, EV = [], CAPS = [];
  const ctx = document.createElement('canvas').getContext('2d');
  function fit(text, family, weight, max, maxW, min) {
    ctx.font = `${weight} ${max}px ${family}`;
    const w = ctx.measureText(text).width;
    return Math.max(min, Math.floor(max * Math.min(1, maxW / w)));
  }
  function win(t, t0, t1, din = 0.38, dout = 0.28) {
    const en = eo((t - t0) / din), ex = eo((t - (t1 - dout)) / dout);
    return { a: Math.min(en, 1 - ex), en, ex };
  }
  function slide(node, w, dy = 36, blur = 12) {
    node.style.opacity = w.a;
    node.style.transform = `translateY(${dy * (1 - w.en) - 14 * w.ex}px)`;
    node.style.filter = `blur(${(1 - w.a) * blur}px)`;
  }
  function fitOnce(e, node, sel, text, max, min, family = 'Sora', weight = 800, maxW = 968) {
    if (e._fit) return;
    e._fit = true;
    node.querySelector(sel).style.fontSize = fit(text, family, weight, max, maxW, min) + 'px';
  }
  const B = {};

  B.hook = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">${e.kicker}</div>` +
      e.lines.map((t, i) => `<div class="big ${i ? 'grad' : 'w'}" data-i="${i}">${t}</div>`).join('');
    const lines = [...n.querySelectorAll('.big')];
    return { node: n, upd(t) {
      if (!e._fit) { e._fit = true; lines.forEach((l, i) => { l.style.fontSize = fit(e.lines[i], 'Sora', 800, 112, 968, 60) + 'px'; }); }
      const w = win(t, e.t0, e.t1, 0.4, 0.32);
      n.style.opacity = w.a > 0 ? 1 : 0;
      n.firstChild.style.opacity = w.a;
      lines.forEach((l, i) => {
        const ww = win(t, e.t0 + 0.10 * i, e.t1, 0.5, 0.32);
        const k = back((t - e.t0 - 0.10 * i) / 0.55);
        l.style.opacity = ww.a;
        l.style.transform = `translateY(${(1 - k) * 60 - 20 * ww.ex}px) scale(${lerp(0.92, 1, k)})`;
        l.style.transformOrigin = 'left center';
        l.style.filter = `blur(${(1 - ww.a) * 14}px)`;
      });
    } };
  };

  B.kp = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">${e.kicker}</div><div class="big grad">${e.text}</div><div class="sub">${e.sub}</div><div class="bar"></div>`;
    const bar = n.querySelector('.bar');
    return { node: n, upd(t) {
      fitOnce(e, n, '.big', e.text, 100, 54);
      slide(n, win(t, e.t0, e.t1, 0.4, 0.3));
      bar.style.transform = `scaleX(${eo((t - e.t0) / 0.8) * 0.4})`;
    } };
  };

  B.step = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">STEP ${e.n} OF ${e.total}<span class="dots">${[...Array(e.total)].map(() => '<i></i>').join('')}</span></div>` +
      `<div class="big grad">${e.text}</div><div class="sub">${e.sub}</div><div class="bar"></div>`;
    const dots = [...n.querySelectorAll('.dots i')];
    const bar = n.querySelector('.bar');
    return { node: n, upd(t) {
      fitOnce(e, n, '.big', e.text, 100, 54);
      slide(n, win(t, e.t0, e.t1, 0.35, 0.2), 30, 10);
      dots.forEach((d, i) => {
        const on = i < e.n ? 1 : 0;
        const cur = i === e.n - 1 ? eo((t - e.t0) / 0.4) : 1;
        d.style.background = on ? `rgba(255,178,31,${lerp(0.25, 1, cur)})` : 'rgba(255,255,255,.22)';
      });
      bar.style.transform = `scaleX(${eo((t - e.t0) / 0.7) * 0.4})`;
    } };
  };

  B.step_on = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">FINAL STEP</div><div style="margin-top:12px;display:flex;align-items:center"><span class="chk">${ICON.check}</span><span class="big grad" style="margin-top:0">${e.text}</span></div><div class="sub">${e.sub}</div><div class="bar"></div>`;
    const chk = n.querySelector('.chk');
    const bar = n.querySelector('.bar');
    return { node: n, upd(t) {
      fitOnce(e, n, '.big', e.text, 96, 54, 'Sora', 800, 800);
      slide(n, win(t, e.t0, e.t1 + 0.1, 0.35, 0.3), 30, 10);
      const k = back((t - e.t0 - 0.9) / 0.5);
      chk.style.transform = `scale(${t < e.t0 + 0.9 ? 0.55 : lerp(0.6, 1, k)}) rotate(${(1 - clamp(k)) * -25}deg)`;
      chk.style.opacity = t < e.t0 + 0.9 ? 0.5 : 1;
      bar.style.transform = `scaleX(${eo((t - e.t0) / 0.7) * 0.4})`;
    } };
  };

  B.voice = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">${e.kicker}<span class="wave">${[...Array(11)].map(() => '<i></i>').join('')}</span></div>` +
      `<div class="big grad">${e.text}</div><div class="sub">${e.sub}</div><div class="bar"></div>`;
    const bars = [...n.querySelectorAll('.wave i')];
    const bar = n.querySelector('.bar');
    return { node: n, upd(t) {
      fitOnce(e, n, '.big', e.text, 100, 54);
      slide(n, win(t, e.t0, e.t1, 0.4, 0.3));
      bars.forEach((b, i) => { b.style.height = (8 + 34 * Math.abs(Math.sin(t * 7.5 + i * 0.9) * Math.cos(t * 3.1 + i * 0.5))) + 'px'; });
      bar.style.transform = `scaleX(${eo((t - e.t0) / 0.8) * 0.4})`;
    } };
  };

  B.recap = (e) => {
    const n = el('abs title');
    n.innerHTML = `<div class="kicker">${e.kicker}</div><div class="pill">${e.lines.map((l) => `<div>${l}</div>`).join('')}</div>`;
    const rows = [...n.querySelectorAll('.pill div')];
    return { node: n, upd(t) {
      slide(n, win(t, e.t0, e.t1, 0.4, 0.3));
      rows.forEach((r, i) => { const k = eo((t - e.t0 - 0.25 - 0.18 * i) / 0.4); r.style.opacity = k; r.style.transform = `translateX(${(1 - k) * 30}px)`; });
    } };
  };

  B.endcard = (e) => {
    const n = el('abs endcard');
    n.appendChild(el('scrim'));
    const big = el('abs'); big.innerHTML = '<img src="../assets/logo_megabyte.png" style="width:100%;height:100%;filter:drop-shadow(0 0 40px rgba(40,120,255,.65)) drop-shadow(0 12px 28px rgba(0,0,0,.6))">';
    big.style.cssText = 'left:390px;top:250px;width:300px;height:300px';
    n.appendChild(big);
    const t1 = el('t', e.lines[0]); t1.style.top = '640px'; t1.style.color = '#fff';
    const t2 = el('t grad', e.lines[1]); t2.style.top = '756px';
    n.appendChild(t1); n.appendChild(t2);
    n.appendChild(el('small', 'iPHONE TIPS • EVERY WEEK'));
    const bw = 470, bh = 124, bx = 190, by = 996;
    const sb = el('sub-btn', `<span class="ic" style="display:inline-flex;width:58px;height:58px">${ICON.play}</span><span class="tx">SUBSCRIBE</span>`);
    sb.style.left = bx + 'px'; sb.style.top = by + 'px';
    const bell = el('btn', ICON.bell); bell.style.cssText = `left:${bx + bw + 120}px;top:${by}px;width:${bh}px;height:${bh}px;color:#FFF6E8`;
    const cur = el('abs', ICON.cursor); cur.style.cssText = 'width:84px;height:84px;left:0;top:0;opacity:0;filter:drop-shadow(0 6px 10px rgba(0,0,0,.6))';
    const ring = el('ring'); n.appendChild(ring);
    n.appendChild(sb); n.appendChild(bell); n.appendChild(cur);
    const tx = sb.querySelector('.tx'), ic = sb.querySelector('.ic');
    return { node: n, upd(t) {
      const w = win(t, e.t0, 1e9, 0.45, 0.01);
      n.style.opacity = w.a > 0 ? 1 : 0;
      n.querySelector('.scrim').style.opacity = eo((t - e.t0) / 0.5);
      [t1, t2].forEach((x, i) => { const k = back((t - e.t0 - 0.12 * i) / 0.55); x.style.opacity = clamp((t - e.t0 - 0.12 * i) / 0.2); x.style.transform = `translateY(${(1 - k) * 50}px) scale(${lerp(0.9, 1, k)})`; });
      n.querySelector('.small').style.opacity = clamp((t - e.t0 - 0.4) / 0.3);
      const kl = back((t - e.t0 - 0.05) / 0.6);
      big.style.opacity = clamp((t - e.t0) / 0.25);
      big.style.transform = `scale(${lerp(0.55, 1, kl)}) rotate(${(1 - clamp(kl)) * -14}deg) translateY(${Math.sin(t * 2.6) * 5}px)`;
      const pop = back((t - e.t0 - 0.3) / 0.5);
      const k = t - e.at;
      const on = k >= 0 ? eo(k / 0.18) : 0;
      let sc = pop; if (k >= 0) sc = pop * (k < 0.1 ? lerp(1, 0.92, k / 0.1) : lerp(0.92, 1, eo((k - 0.1) / 0.3)));
      sb.style.transform = `scale(${sc})`; sb.style.opacity = clamp((t - e.t0 - 0.3) / 0.2);
      sb.style.background = on > 0.5 ? 'rgba(14,16,24,.88)' : 'linear-gradient(95deg,#FF5A2A,#FF2E7E)';
      sb.style.border = on > 0.5 ? '2px solid rgba(255,255,255,.3)' : '2px solid transparent';
      tx.textContent = on > 0.5 ? 'SUBSCRIBED' : 'SUBSCRIBE'; ic.innerHTML = on > 0.5 ? ICON.check : ICON.play;
      ic.style.color = on > 0.5 ? '#FFB21F' : '#fff';
      const bk = t - (e.at + 0.2);
      const rot = bk > 0 && bk < 1.1 ? Math.sin(bk * 28) * 26 * Math.exp(-bk * 3.2) : 0;
      bell.style.transform = `scale(${pop}) rotate(${rot}deg)`; bell.style.opacity = clamp((t - e.t0 - 0.3) / 0.2);
      bell.style.color = on > 0.5 ? '#FFB21F' : '#FFF6E8'; bell.style.borderColor = on > 0.5 ? 'rgba(255,178,31,.9)' : 'rgba(255,255,255,.28)';
      const ck = (t - (e.at - 0.85)) / 0.8;
      const cx = lerp(bx + bw + 160, bx + bw * 0.5, eo(ck)), cy = lerp(by + 330, by + bh * 0.55, eo(ck));
      const cc = t - e.at;
      cur.style.opacity = (ck > 0 && cc < 0.7) ? Math.min(1, ck * 2) * (1 - sm((cc - 0.35) / 0.35)) : 0;
      cur.style.transform = `translate(${cx}px,${cy}px) scale(${cc > 0 && cc < 0.12 ? 0.82 : 1})`;
      const rk = (t - e.at) / 0.6;
      if (rk < 0 || rk > 1) ring.style.opacity = 0; else {
        const rad = lerp(70, 250, eo(rk)); ring.style.opacity = (1 - rk) * 0.95;
        ring.style.width = ring.style.height = rad * 2 + 'px'; ring.style.left = bx + bw / 2 - rad + 'px'; ring.style.top = by + bh / 2 - rad + 'px'; ring.style.borderWidth = lerp(9, 2, rk) + 'px';
      }
    } };
  };

  /* captions */
  function buildCaptions() {
    CAPS = TL.captions.map((p) => {
      const c = el('cap'); const line = el('line'); c.appendChild(line);
      const ws = p.words.map((w) => { const s = el('w'); s.textContent = w.t; line.appendChild(s); line.appendChild(document.createTextNode(' ')); return s; });
      capsEl.appendChild(c);
      return { p, c, ws };
    });
  }
  function captionsStep(t) {
    let act = null;
    for (const o of CAPS) {
      const on = t >= o.p.t0 && t < o.p.t1;
      o.c.style.display = on ? 'flex' : 'none';
      if (on) act = o;
    }
    if (!act) return;
    const p = act.p;
    if (!act.fitted) {                      // shrink the page if its longest word would overflow the caption box
      act.fitted = true;
      let mx = 0; p.words.forEach((w) => { ctx.font = '700 64px Poppins'; mx = Math.max(mx, ctx.measureText(w.t).width); });
      const k = Math.min(1, (860 / 1.18) / (mx + 8));
      if (k < 1) act.c.querySelector('.line').style.fontSize = Math.floor(64 * k) + 'px';
    }
    const fin = eo((t - p.t0) / 0.16), fout = 1 - eo((t - (p.t1 - 0.12)) / 0.12);
    act.c.style.opacity = Math.min(fin, fout);
    act.c.style.transform = `translateY(${(1 - fin) * 18}px)`;
    act.ws.forEach((s, i) => {
      const w = p.words[i];
      const f = sm((t - w.a) / 0.09) * (1 - sm((t - (w.b + 0.04)) / 0.16));
      const before = t < w.a;
      const rs = before ? 0.88 : 0.92, ro = before ? 0.62 : 0.70, rb = before ? 1.2 : 0;
      s.style.transform = `translateY(${-6 * f}px) scale(${lerp(rs, 1.14, f)})`;
      s.style.opacity = lerp(ro, 1, f);
      const bl = lerp(rb, 0, f);
      s.style.filter = bl > 0.05 ? `blur(${bl}px)` : 'none';
      s.style.color = mix(CREAM, AMBERC, f);
      s.style.textShadow = f > 0.02 ? `0 0 ${26 * f}px rgba(255,170,30,${0.6 * f}),0 4px 16px rgba(0,0,0,.65)` : '0 4px 16px rgba(0,0,0,.65)';
    });
  }

  window.setTimeline = function (tl) {
    TL = tl; layer = document.getElementById('layer'); capsEl = document.getElementById('captions');
    layer.innerHTML = ''; capsEl.innerHTML = ''; EV = [];
    TL.events.forEach((e) => { const o = B[e.type](e); o.e = e; o.node.style.display = 'none'; layer.appendChild(o.node); EV.push(o); });
    buildCaptions();
  };
  window.renderAt = function (t) {
    for (const o of EV) {
      const e = o.e;
      const on = t >= e.t0 - 0.02 && t <= e.t1 + 0.4;
      o.node.style.display = on ? 'block' : 'none';
      if (on) o.upd(t);
    }
    captionsStep(t);
    document.getElementById('progfill').style.width = (clamp(t / (TL.duration - 1.7)) * 100) + '%';
    const end = EV.find((o) => o.e.type === 'endcard');
    const ec = end && t >= end.e.t0 ? eo((t - end.e.t0) / 0.5) : 0;
    document.getElementById('captions').style.opacity = 1 - ec;
    document.getElementById('logo').style.opacity = 1 - ec * 0.0;
  };
})();
