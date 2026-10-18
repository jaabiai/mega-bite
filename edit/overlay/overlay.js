/* Deterministic overlay renderer: renderAt(t) draws every graphic for main-timeline time t (seconds). */
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
    like: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>',
    comment: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>',
    share: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>',
    bell: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>',
    check: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    play: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>',
    cursor: '<svg viewBox="0 0 24 24"><path fill="#fff" stroke="#111" stroke-width="1.2" d="M4 2l15 9.5-6.3 1.4 3.6 6.6-2.9 1.6-3.6-6.6L5 18z"/></svg>',
  };

  let TL = null, layer, capsEl, logo, logoHero, EV = [], CAPS = [], capPtr = 0;
  const bursts = [];

  // generic enter/exit window -> {a: visibility 0..1, en: enter 0..1, ex: exit 0..1}
  function win(t, t0, t1, din = 0.4, dout = 0.3) {
    const en = eo((t - t0) / din), ex = eo((t - (t1 - dout)) / dout);
    return { a: Math.min(en, 1 - ex), en, ex };
  }
  function setIn(node, w, dx = -70, dy = 0, blur = 10) {
    node.style.opacity = w.a;
    node.style.transform = `translate(${dx * (1 - w.en) + (-dx * 0.35) * w.ex}px,${dy * (1 - w.en)}px)`;
    node.style.filter = `blur(${(1 - w.a) * blur}px)`;
  }
  function ringBurst(parent, cx, cy, r0, r1, t, at, dur = 0.55, color) {
    const k = (t - at) / dur;
    const r = parent._ring;
    if (k < 0 || k > 1) { r.style.opacity = 0; return; }
    const rad = lerp(r0, r1, eo(k));
    r.style.opacity = (1 - k) * 0.95;
    r.style.width = r.style.height = rad * 2 + 'px';
    r.style.left = cx - rad + 'px'; r.style.top = cy - rad + 'px';
    r.style.borderWidth = lerp(9, 2, k) + 'px';
    if (color) r.style.borderColor = color;
  }
  function mkParticles(parent, n) {
    const ps = [];
    for (let i = 0; i < n; i++) {
      const p = el('abs'); p.style.cssText = 'width:16px;height:16px;border-radius:50%;opacity:0;background:var(--grad)';
      parent.appendChild(p); ps.push(p);
    }
    return ps;
  }
  function particles(ps, cx, cy, t, at, spread = 150) {
    const k = (t - at) / 0.7;
    ps.forEach((p, i) => {
      if (k < 0 || k > 1) { p.style.opacity = 0; return; }
      const ang = (i / ps.length) * Math.PI * 2 + 0.4, d = spread * eo(k * 1.1);
      p.style.opacity = 1 - k; const s = (1 - k) * (i % 2 ? 1 : 0.7);
      p.style.transform = `translate(${cx + Math.cos(ang) * d - 8}px,${cy + Math.sin(ang) * d - 8}px) scale(${s})`;
    });
  }

  /* ---------------------------------------------------------------- builders */
  const B = {};

  B.hero = (e) => {
    const n = el('abs hero' + (e.small ? ' small' : ''));
    const lines = e.lines || [e.l1, e.l2];
    n.innerHTML = `<div class="kicker">${e.kicker}</div>` + lines.map((tx, i) => `<div class="l${i >= lines.length - (e.grad || 1) ? ' g' : ''}">${tx}</div>`).join('');
    const kids = [...n.children];
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.5, 0.35);
      n.style.opacity = w.a > 0 ? 1 : 0;
      kids.forEach((k, i) => {
        const ww = win(t, e.t0 + 0.09 * i, e.t1, 0.5, 0.35);
        k.style.opacity = ww.a; k.style.transform = `translateX(${-80 * (1 - ww.en) + 40 * ww.ex * -1}px)`; k.style.filter = `blur(${(1 - ww.a) * 12}px)`;
      });
    } };
  };

  B.badge = (e) => {
    const n = el('abs badge');
    n.innerHTML = `<div class="kicker">${e.sub}</div><div class="big grad">${e.text}</div>`;
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.45, 0.3);
      n.style.opacity = w.a;
      n.style.transform = `translateX(${-60 * (1 - w.en)}px) scale(${lerp(0.82, 1, back(w.en))})`;
      n.style.transformOrigin = 'left center'; n.style.filter = `blur(${(1 - w.a) * 12}px)`;
    } };
  };

  B.kp = (e) => {
    const panel = e.scene != null;
    const n = el('abs kp ' + (panel ? 'panel-pos' : 'hero-pos'));
    n.innerHTML = `<div class="kicker">${panel ? 'NOW' : 'KEY POINT'}</div><div class="big grad">${e.text}</div>` +
      (e.sub ? `<div class="sub">${e.sub}</div>` : '') + '<div class="bar"></div>';
    const bar = n.querySelector('.bar');
    // fit long phrases
    if (e.size) n.querySelector('.big').style.fontSize = e.size + 'px';
    else if (e.text.length > 12) n.querySelector('.big').style.fontSize = (e.text.length > 16 ? 56 : 66) + 'px';
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.38, 0.28);
      setIn(n, w, -70, 0, 12);
      bar.style.transform = `scaleX(${eo((t - e.t0) / 0.7) * 0.35 + 0.0})`; bar.style.width = '100%';
    } };
  };

  B.scene = (e) => {
    const n = el('abs');
    n.style.cssText = 'left:0;top:0;width:1920px;height:1080px';
    const pre = el('abs prelabel', `<span>${e.pre_label || ''}</span>`);
    const card = el('abs fcard', `<div class="kicker" style="margin-bottom:22px">${e.kicker}</div>
      <div class="row"><div class="num">${e.num}</div><div><div class="t">${e.l1}</div><div class="t g">${e.l2}</div></div></div>`);
    n.appendChild(pre); n.appendChild(card);
    return { node: n, upd(t) {
      const cf = e.show_card_from;
      const wc = win(t, cf, e.t1, 0.5, 0.35);
      setIn(card, wc, -80, 0, 12);
      if (e.pre_label) {
        const wp = win(t, e.t0 + 0.25, cf, 0.35, 0.25);
        setIn(pre, wp, -60, 0, 8);
      } else pre.style.opacity = 0;
    } };
  };

  B.steps = (e) => {
    const n = el('abs steps');
    n.innerHTML = '<div class="hd">STEP BY STEP</div>';
    const rows = e.items.map(([label], i) => {
      const r = el('step', `<div class="n">${i + 1}</div><div class="lb">${label}</div>`);
      n.appendChild(r); return r;
    });
    return { node: n, upd(t) {
      const w = win(t, e.t0 + 0.2, e.t1, 0.5, 0.35);
      n.style.opacity = w.a; n.style.transform = `translateX(${70 * (1 - w.en)}px)`;
      rows.forEach((r, i) => {
        const ts = e.items[i][1], tn = i + 1 < e.items.length ? e.items[i + 1][1] : 1e9;
        const stag = eo((t - (e.t0 + 0.3 + i * 0.07)) / 0.35);
        const act = sm((t - ts) / 0.25) * (1 - sm((t - tn) / 0.25));
        const done = sm((t - tn) / 0.25);
        r.style.opacity = stag * (0.46 + 0.54 * Math.max(act, done * 0.6));
        r.style.transform = `translateX(${(1 - stag) * 40}px) scale(${1 + act * 0.035})`;
        r.style.transformOrigin = 'left center';
        r.style.background = `rgba(255,178,31,${0.95 * act})`;
        r.style.borderColor = `rgba(255,178,31,${0.35 * (1 - act) * (done > 0.5 ? 0.5 : 0)})`;
        r.style.color = act > 0.5 ? '#1c1109' : '#FFF6E8';
        r.style.boxShadow = act > 0.01 ? `0 8px 26px rgba(255,150,30,${0.4 * act})` : 'none';
        const nn = r.querySelector('.n');
        nn.style.background = act > 0.5 ? 'rgba(28,17,9,.16)' : (done > 0.5 ? 'rgba(255,178,31,.9)' : 'rgba(255,255,255,.14)');
        nn.style.color = done > 0.5 ? '#1c1109' : (act > 0.5 ? '#1c1109' : '#FFF6E8');
        nn.innerHTML = done > 0.5 ? ICON.check : String(i + 1);
      });
    } };
  };

  B.chip = (e) => {
    const n = el('abs chip');
    n.innerHTML = `<div class="box"><div class="big grad">${e.text}</div>${e.sub ? `<div class="sub">${e.sub}</div>` : ''}</div>`;
    return { node: n, upd(t) { setIn(n, win(t, e.t0, e.t1, 0.35, 0.28), -70, 0, 10); } };
  };

  B.recap = (e) => {
    const n = el('abs recap');
    const ps = e.items.map(([num, title]) => { const p = el('rpill', `<div class="n">${num}</div><div class="t">${title}</div>`); n.appendChild(p); return p; });
    return { node: n, upd(t) {
      const fade = 1 - eo((t - (e.t1 - 0.35)) / 0.35);
      n.style.opacity = fade;
      ps.forEach((p, i) => {
        const k = back((t - e.items[i][2] + 0.1) / 0.5);
        p.style.opacity = clamp((t - e.items[i][2] + 0.1) / 0.2);
        p.style.transform = `translateX(${-120 * (1 - k)}px) scale(${lerp(0.9, 1, k)})`;
        p.style.transformOrigin = 'left center';
      });
    } };
  };

  function circleBtn(parent, x, y, size, icon, label) {
    const b = el('btn'); b.style.cssText = `left:${x}px;top:${y}px;width:${size}px;height:${size}px`; b.innerHTML = icon; b.style.color = '#FFF6E8';
    const l = el('lab', label); l.style.cssText = `left:${x - 30}px;top:${y + size + 22}px;width:${size + 60}px;text-align:center;font-size:${Math.round(size * 0.22)}px`;
    parent.appendChild(b); parent.appendChild(l);
    return { b, l };
  }
  function pressAnim(b, l, size, x, y, t, at, tIn) {
    const pop = back((t - tIn) / 0.45);
    const k = t - at;
    let s = pop;
    if (k >= 0) s = pop * (k < 0.1 ? lerp(1, 0.86, k / 0.1) : k < 0.3 ? lerp(0.86, 1.14, eo((k - 0.1) / 0.2)) : lerp(1.14, 1, eo((k - 0.3) / 0.25)));
    const on = k >= 0 ? eo(k / 0.15) : 0;
    b.style.transform = `scale(${s})`; b.style.opacity = clamp((t - tIn) / 0.15);
    b.style.background = on > 0.01 ? `linear-gradient(135deg,rgba(255,${Math.round(lerp(30, 200, 1 - on))},${Math.round(lerp(60, 40, 1 - on))},${on}) , rgba(255,122,26,${on}))` : 'rgba(10,12,18,.72)';
    b.style.backgroundColor = on > 0.01 ? `rgba(255,150,30,${on})` : 'rgba(10,12,18,.72)';
    b.style.backgroundImage = 'none';
    b.style.borderColor = mix([255, 255, 255], AMBERC, on); b.style.color = on > 0.5 ? '#1c1109' : '#FFF6E8';
    l.style.opacity = clamp((t - tIn - 0.1) / 0.2);
    l.style.color = mix(CREAM, AMBERC, on);
  }

  B.cta_like = B.cta_share = (e, isShare) => {
    const share = e.type === 'cta_share';
    const n = el('abs');
    n.style.cssText = 'left:0;top:0;width:1920px;height:1080px';
    const x = 1420, y = 300, size = 200;
    const { b, l } = circleBtn(n, x, y, size, share ? ICON.share : ICON.like, share ? 'SHARE' : 'LIKE');
    n._ring = el('ring'); n.appendChild(n._ring);
    const ps = mkParticles(n, 10);
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.3, 0.3);
      n.style.opacity = w.a > 0 ? 1 : 0;
      pressAnim(b, l, size, x, y, t, e.at, e.t0 + 0.05);
      if (t > e.t1 - 0.3) { const k = 1 - eo((t - (e.t1 - 0.3)) / 0.3); b.style.opacity = k; l.style.opacity = k; }
      ringBurst(n, x + size / 2, y + size / 2, size * 0.5, size * 1.0, t, e.at, 0.55);
      particles(ps, x + size / 2, y + size / 2, t, e.at, 170);
    } };
  };

  B.cta_trio = (e) => {
    const n = el('abs'); n.style.cssText = 'left:0;top:0;width:1920px;height:1080px';
    const defs = [['LIKE', ICON.like], ['COMMENT', ICON.comment], ['SHARE', ICON.share]];
    const size = 150, gap = 60, x0 = 1330, y = 330;
    const items = defs.map(([lab, ic], i) => {
      const x = x0 + i * (size + gap);
      const o = circleBtn(n, x, y, size, ic, lab); o.l.style.fontSize = '27px'; o.x = x;
      o.ring = el('ring'); n.appendChild(o.ring); o.ps = mkParticles(n, 8);
      return o;
    });
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.3, 0.3);
      n.style.opacity = w.a > 0 ? 1 : 0;
      items.forEach((o, i) => {
        const at = e.at[i];
        pressAnim(o.b, o.l, size, o.x, y, t, at, e.t0 + 0.15 * i + 0.05);
        if (t > e.t1 - 0.3) { const k = 1 - eo((t - (e.t1 - 0.3)) / 0.3); o.b.style.opacity = k; o.l.style.opacity = k; }
        const holder = { _ring: o.ring };
        ringBurst(holder, o.x + size / 2, y + size / 2, size * 0.5, size, t, at, 0.5);
        particles(o.ps, o.x + size / 2, y + size / 2, t, at, 130);
      });
    } };
  };

  B.cta_sub = (e) => {
    const n = el('abs'); n.style.cssText = 'left:0;top:0;width:1920px;height:1080px';
    const bx = 1250, by = 330, bw = 450, bh = 118;
    const sb = el('sub-btn', `<span style="display:inline-flex;width:56px;height:56px">${ICON.play}</span><span class="tx">SUBSCRIBE</span>`);
    sb.style.cssText += `;left:${bx}px;top:${by}px;width:${bw - 74}px;`;
    const bell = el('btn', ICON.bell); bell.style.cssText = `left:${bx + bw + 14}px;top:${by}px;width:${bh}px;height:${bh}px;color:#FFF6E8`;
    const cur = el('abs', ICON.cursor); cur.style.cssText = 'width:74px;height:74px;left:0;top:0;opacity:0;filter:drop-shadow(0 6px 10px rgba(0,0,0,.6))';
    n._ring = el('ring'); n.appendChild(n._ring);
    const ps = mkParticles(n, 12);
    n.appendChild(sb); n.appendChild(bell); n.appendChild(cur);
    const tx = sb.querySelector('.tx'), ic = sb.querySelector('span');
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.end ? 1e9 : e.t1, 0.4, 0.3);
      n.style.opacity = w.a > 0 ? 1 : 0;
      const pop = back((t - e.t0) / 0.5);
      const k = t - e.at;
      let sc = pop;
      if (k >= 0) sc = pop * (k < 0.1 ? lerp(1, 0.92, k / 0.1) : lerp(0.92, 1, eo((k - 0.1) / 0.3)));
      const on = k >= 0 ? eo(k / 0.2) : 0;
      sb.style.transform = `scale(${sc})`; sb.style.opacity = clamp((t - e.t0) / 0.2) * (e.end ? 1 : (1 - eo((t - (e.t1 - 0.3)) / 0.3)));
      sb.style.background = on > 0.5 ? 'rgba(14,16,24,.86)' : 'linear-gradient(95deg,#FF5A2A,#FF2E7E)';
      sb.style.color = '#fff'; sb.style.border = on > 0.5 ? '2px solid rgba(255,255,255,.3)' : '2px solid transparent';
      tx.textContent = on > 0.5 ? 'SUBSCRIBED' : 'SUBSCRIBE'; ic.innerHTML = on > 0.5 ? ICON.check : ICON.play;
      ic.style.color = on > 0.5 ? '#FFB21F' : '#fff';
      // bell ring after click
      const bk = t - (e.at + 0.2);
      const rot = bk > 0 && bk < 1.1 ? Math.sin(bk * 28) * 26 * Math.exp(-bk * 3.2) : 0;
      bell.style.transform = `scale(${pop}) rotate(${rot}deg)`; bell.style.opacity = clamp((t - e.t0) / 0.2) * (e.end ? 1 : (1 - eo((t - (e.t1 - 0.3)) / 0.3)));
      bell.style.color = on > 0.5 ? '#FFB21F' : '#FFF6E8'; bell.style.borderColor = on > 0.5 ? 'rgba(255,178,31,.9)' : 'rgba(255,255,255,.28)';
      // cursor glides in, clicks at e.at
      const ck = (t - (e.at - 0.95)) / 0.85;
      const cx = lerp(bx + bw + 150, bx + bw * 0.42, eo(ck)), cy = lerp(by + 330, by + bh * 0.52, eo(ck));
      const cclick = t - e.at;
      cur.style.opacity = (ck > 0 && cclick < 0.9) ? Math.min(1, ck * 2) * (1 - sm((cclick - 0.5) / 0.4)) : 0;
      cur.style.transform = `translate(${cx}px,${cy}px) scale(${cclick > 0 && cclick < 0.12 ? 0.82 : 1})`;
      ringBurst(n, bx + (bw - 74) / 2, by + bh / 2, 60, 210, t, e.at, 0.6);
      particles(ps, bx + (bw - 74) / 2, by + bh / 2, t, e.at, 220);
    } };
  };

  B.thanks = (e) => {
    const n = el('abs thanks', `<div class="tt"><span class="grad">${e.text}</span></div>`);
    return { node: n, upd(t) { const w = win(t, e.t0, e.t1 + 5, 0.5, 0.01); n.style.opacity = w.a; n.style.transform = `translateY(${-30 * (1 - w.en)}px) scale(${lerp(0.9, 1, back(w.en))})`; } };
  };

  B.stinger = (e) => {
    const n = el('abs stinger');
    const vig = el('vig'); n.appendChild(vig);
    const words = el('words'); n.appendChild(words);
    const wds = e.words.map(([w], i) => { const s = el('wd' + (i >= 2 ? ' g' : ''), w); words.appendChild(s); return s; });
    const tag = el('tag', 'TECH &nbsp;•&nbsp; AI &nbsp;•&nbsp; FUTURE'); n.appendChild(tag);
    return { node: n, upd(t) {
      const w = win(t, e.t0, e.t1, 0.35, 0.45);
      vig.style.opacity = w.a * 0.9;
      wds.forEach((s, i) => {
        const at = e.words[i][1];
        const k = back((t - at + 0.05) / 0.45);
        s.style.opacity = clamp((t - at + 0.05) / 0.15) * (1 - eo((t - (e.t1 - 0.35)) / 0.35));
        s.style.transform = `translateY(${(1 - k) * 50}px) scale(${lerp(0.7, 1, k)})`;
      });
      tag.style.opacity = clamp((t - (e.words[3][1] + 0.35)) / 0.4) * (1 - eo((t - (e.t1 - 0.35)) / 0.35));
      tag.style.letterSpacing = lerp(0.9, 0.5, eo((t - e.words[3][1]) / 1.4)) + 'em';
    } };
  };

  /* ---------------------------------------------------------------- captions */
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
    for (let i = 0; i < CAPS.length; i++) {
      const o = CAPS[i];
      const on = t >= o.p.t0 && t < o.p.t1;
      o.c.style.display = on ? 'block' : 'none';
      if (on) act = o;
    }
    if (!act) return;
    const p = act.p;
    const fin = eo((t - p.t0) / 0.18), fout = 1 - eo((t - (p.t1 - 0.14)) / 0.14);
    act.c.style.opacity = Math.min(fin, fout);
    act.c.style.transform = `translateY(${(1 - fin) * 16}px)`;
    act.ws.forEach((s, i) => {
      const w = p.words[i];
      const f = sm((t - w.a) / 0.09) * (1 - sm((t - (w.b + 0.04)) / 0.16));
      const before = t < w.a;
      // resting state: upcoming (smaller, faded, soft blur) vs spoken (small, faded)
      const rs = before ? 0.86 : 0.9, ro = before ? 0.58 : 0.66, rb = before ? 1.4 : 0;
      const sc = lerp(rs, 1.17, f), op = lerp(ro, 1, f), bl = lerp(rb, 0, f);
      s.style.transform = `translateY(${-5 * f}px) scale(${sc})`;
      s.style.opacity = op;
      s.style.filter = bl > 0.05 ? `blur(${bl}px)` : 'none';
      s.style.color = mix(CREAM, AMBERC, f);
      s.style.textShadow = f > 0.02 ? `0 0 ${24 * f}px rgba(255,170,30,${0.55 * f}),0 4px 16px rgba(0,0,0,.6)` : '0 4px 16px rgba(0,0,0,.6)';
      s.style.webkitTextStroke = '5px rgba(6,7,12,.55)';
    });
  }

  /* ---------------------------------------------------------------- logo + stinger hero */
  function logoStep(t) {
    const L = TL.logo_hero;
    const inHero = t >= L.t0 && t < L.t1;
    logo.style.display = inHero ? 'none' : 'block';
    logoHero.style.display = inHero ? 'block' : 'none';
    if (!inHero) return;
    const appear = back((t - L.t0) / 0.6);
    const land = eio((t - (L.t1 - 0.8)) / 0.8);
    const size = lerp(lerp(120, 560, appear), 100, land);
    const cx = lerp(960, 1796 + 50, land), cy = lerp(330, 26 + 50, land);
    const bob = Math.sin((t - L.t0) * 3) * 6 * (1 - land);
    logoHero.style.width = logoHero.style.height = size + 'px';
    logoHero.style.left = cx - size / 2 + 'px'; logoHero.style.top = cy - size / 2 + bob + 'px';
    logoHero.style.opacity = clamp((t - L.t0) / 0.2);
    logoHero.style.transform = `rotate(${(1 - appear) * -18}deg)`;
  }

  /* ---------------------------------------------------------------- public API */
  window.setTimeline = function (tl) {
    TL = tl; layer = document.getElementById('layer'); capsEl = document.getElementById('captions');
    logo = document.getElementById('logo'); logoHero = document.getElementById('logoHero');
    layer.innerHTML = ''; capsEl.innerHTML = ''; EV = [];
    // z-order: scene panels < steps < kp < others
    const order = { scene: 0, steps: 1, kp: 2, hero: 2, badge: 2, chip: 2, recap: 2, stinger: 3, cta_like: 4, cta_share: 4, cta_trio: 4, cta_sub: 4, thanks: 4 };
    TL.events.slice().sort((a, b) => order[a.type] - order[b.type]).forEach((e) => {
      const o = B[e.type](e); o.e = e; o.node.style.display = 'none'; layer.appendChild(o.node); EV.push(o);
    });
    buildCaptions();
  };
  window.renderAt = function (t) {
    for (const o of EV) {
      const e = o.e;
      const on = t >= e.t0 - 0.02 && t <= (e.end ? 1e9 : e.t1 + 0.4);
      o.node.style.display = on ? 'block' : 'none';
      if (on) o.upd(t);
    }
    captionsStep(t);
    logoStep(t);
  };
})();
