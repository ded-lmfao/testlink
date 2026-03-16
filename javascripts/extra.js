/**
 * RevvLink Documentation — Custom JavaScript
 * Parallax · Particle System · Scroll Triggers · Stat Counters
 */

(function () {
  'use strict';

  // ─── Utility ────────────────────────────────────────────────────────────────
  const qs = (sel, ctx = document) => ctx.querySelector(sel);
  const qsa = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  // ─── Parallax Hero Background ────────────────────────────────────────────────
  function initParallax() {
    const bg = qs('#revvParallaxBg');
    if (!bg) return;

    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          const maxScroll = window.innerHeight;
          const progress = clamp(scrollY / maxScroll, 0, 1);
          bg.style.transform = `translateY(${scrollY * 0.35}px)`;
          bg.style.opacity = (1 - progress * 0.6).toString();
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  // ─── Particle System ────────────────────────────────────────────────────────
  function initParticles() {
    const canvas = qs('#revvParticles');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let w, h, particles;
    const COUNT = window.innerWidth < 768 ? 40 : 80;

    function resize() {
      w = canvas.width = canvas.offsetWidth;
      h = canvas.height = canvas.offsetHeight;
    }

    function createParticle() {
      // Orange/amber hues: 25 (orange), 38 (amber), 15 (deep orange)
      const hues = [25, 38, 15, 30, 42];
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.5 + 0.5,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        a: Math.random(),
        da: (Math.random() - 0.5) * 0.005,
        hue: hues[Math.floor(Math.random() * hues.length)],
      };
    }

    function init() {
      resize();
      particles = Array.from({ length: COUNT }, createParticle);
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);

      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.a += p.da;
        p.a = clamp(p.a, 0.05, 0.8);
        if (p.a <= 0.05 || p.a >= 0.8) p.da *= -1;

        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, 90%, 65%, ${p.a})`;
        ctx.fill();
      });

      // Draw connections between close particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            const alpha = (1 - dist / 120) * 0.15;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(249, 115, 22, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize, { passive: true });
    init();
    draw();
  }

  // ─── Scroll Reveal (Intersection Observer) ───────────────────────────────────
  function initScrollReveal() {
    const elements = qsa('.revv-scroll-reveal');
    if (!elements.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const delay = parseFloat(el.dataset.delay || '0');

          setTimeout(() => {
            el.classList.add('revv-revealed');
          }, delay * 1000);

          observer.unobserve(el);
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    elements.forEach(el => observer.observe(el));
  }

  // ─── Animated Stat Counters ──────────────────────────────────────────────────
  function initCounters() {
    const stats = qsa('[data-target]');
    if (!stats.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseInt(el.dataset.target, 10);
          const duration = 1400;
          const start = performance.now();

          function step(now) {
            const progress = clamp((now - start) / duration, 0, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(eased * target).toLocaleString();
            if (progress < 1) requestAnimationFrame(step);
          }

          requestAnimationFrame(step);
          observer.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );

    stats.forEach(el => observer.observe(el));
  }

  // ─── Nav scroll state ────────────────────────────────────────────────────────
  function initNavScroll() {
    const header = qs('.md-header');
    if (!header) return;

    window.addEventListener('scroll', () => {
      if (window.scrollY > 60) {
        header.setAttribute('data-md-state', 'shadow');
      } else {
        header.removeAttribute('data-md-state');
      }
    }, { passive: true });
  }

  // ─── Smooth anchor scroll ────────────────────────────────────────────────────
  function initSmoothAnchors() {
    document.addEventListener('click', e => {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;
      const id = link.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.pushState(null, '', `#${id}`);
    });
  }

  // ─── Feature card tilt effect ────────────────────────────────────────────────
  function initCardTilt() {
    const cards = qsa('.revv-feature-card');
    cards.forEach(card => {
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `translateY(-6px) rotateX(${-y * 5}deg) rotateY(${x * 5}deg)`;
        card.style.transition = 'transform .05s';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        card.style.transition = 'transform .35s ease';
      });
    });
  }

  // ─── Code window reveal ───────────────────────────────────────────────────
  function initCodeReveal() {
    const window_ = qs('.revv-code-window');
    if (!window_) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          window_.style.animation = 'revv-code-reveal .6s ease both';
          observer.unobserve(window_);
        });
      },
      { threshold: 0.3 }
    );
    observer.observe(window_);
  }

  // ─── Active nav section highlighting ─────────────────────────────────────────
  function initActiveSectionTracking() {
    const headings = qsa('h2[id], h3[id]');
    if (!headings.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const id = entry.target.id;
          qsa('.md-nav__link--active').forEach(l => l.classList.remove('md-nav__link--active'));
          const link = qs(`.md-nav__link[href="#${id}"]`);
          if (link) link.classList.add('md-nav__link--active');
        });
      },
      { rootMargin: '-20% 0px -75% 0px' }
    );

    headings.forEach(h => observer.observe(h));
  }

  // ─── TOC & Sidebar Tag Injection ───────────────────────────────────────────
  function initTOCTags() {
    // Target both secondary TOC and primary sidebar links
    const navLinks = qsa('.md-nav--secondary .md-nav__link, .md-nav--primary .md-nav__link');
    if (!navLinks.length) return;

    navLinks.forEach(link => {
      // Check if tag already exists to prevent duplicates
      if (qs('.revv-toc-tag', link)) return;

      const href = link.getAttribute('href');
      if (!href || !href.startsWith('#')) return;

      const targetId = href.slice(1);
      const targetHeading = document.getElementById(targetId);
      if (!targetHeading) return;

      // mkdocstrings headers often contain a code block or span with the type
      // We look for clues in the text content or child elements
      const fullText = targetHeading.textContent.toLowerCase();
      
      let type = '';
      let label = '';

      if (fullText.includes('class')) {
        type = 'class';
        label = 'CLASS';
      } else if (fullText.includes('property')) {
        type = 'pro';
        label = 'PRO';
      } else if (fullText.includes('async')) {
        type = 'asy';
        label = 'ASY';
      } else if (fullText.includes('method')) {
        type = 'meth';
        label = 'METH';
      } else if (fullText.includes('exception')) {
        type = 'exc';
        label = 'EXC';
      } else if (fullText.includes('enum')) {
        type = 'enum';
        label = 'ENUM';
      }

      if (type) {
        const tag = document.createElement('span');
        tag.className = `revv-toc-tag revv-toc-tag--${type}`;
        tag.textContent = label;
        link.appendChild(tag);
      }
    });
  }

  // ─── Copy feedback flash ──────────────────────────────────────────────────────
  function initCopyFlash() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('.md-clipboard');
      if (!btn) return;
      const pre = btn.closest('.highlight, .md-code__inner');
      if (!pre) return;
      pre.style.transition = 'box-shadow .15s';
      pre.style.boxShadow = '0 0 0 2px rgba(249,115,22,0.5)';
      setTimeout(() => { pre.style.boxShadow = ''; }, 600);
    });
  }

  // ─── Inject CSS keyframes for code reveal ────────────────────────────────────
  function injectKeyframes() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes revv-code-reveal {
        from { opacity: 0; transform: translateY(20px) scale(0.98); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
      }
    `;
    document.head.appendChild(style);
  }

  // ─── Page-transition progress bar ────────────────────────────────────────────
  let _progressBar = null;
  let _progressRaf = null;

  function createProgressBar() {
    if (_progressBar) return;
    _progressBar = document.createElement('div');
    _progressBar.id = 'revv-nav-bar';
    Object.assign(_progressBar.style, {
      position: 'fixed',
      top: '0',
      left: '0',
      height: '2.5px',
      width: '0%',
      background: 'linear-gradient(90deg, #ea580c, #f97316, #fdba74)',
      boxShadow: '0 0 10px rgba(249,115,22,0.7)',
      zIndex: '99999',
      transition: 'none',
      pointerEvents: 'none',
      borderRadius: '0 2px 2px 0',
    });
    document.body.appendChild(_progressBar);
  }

  function runProgressBar() {
    createProgressBar();
    const bar = _progressBar;
    if (_progressRaf) cancelAnimationFrame(_progressRaf);

    // Phase 1: rush to ~80% (150 ms)
    const start = performance.now();
    const phase1 = 220;

    bar.style.opacity = '1';
    bar.style.width = '0%';

    function step(now) {
      const t = clamp((now - start) / phase1, 0, 1);
      const eased = 1 - Math.pow(1 - t, 3);          // ease-out cubic
      bar.style.width = (eased * 78) + '%';
      if (t < 1) _progressRaf = requestAnimationFrame(step);
    }

    _progressRaf = requestAnimationFrame(step);
  }

  function finishProgressBar() {
    if (!_progressBar) return;
    const bar = _progressBar;
    if (_progressRaf) { cancelAnimationFrame(_progressRaf); _progressRaf = null; }

    bar.style.transition = 'width 180ms cubic-bezier(.4,0,.2,1), opacity 300ms 100ms';
    bar.style.width = '100%';
    setTimeout(() => {
      bar.style.opacity = '0';
      setTimeout(() => { bar.style.width = '0%'; bar.style.transition = 'none'; }, 400);
    }, 180);
  }

  // ─── Smooth scroll-to-top (custom eased, not CSS smooth) ─────────────────────
  function scrollToTopAnimated() {
    const startY = window.scrollY;
    if (startY < 1) return;                            // already at top

    const duration = clamp(startY * 0.35, 220, 600); // scale with distance
    const startTime = performance.now();

    function easeOutQuart(t) { return 1 - Math.pow(1 - t, 4); }

    function step(now) {
      const t = clamp((now - startTime) / duration, 0, 1);
      const eased = easeOutQuart(t);
      window.scrollTo(0, startY * (1 - eased));
      if (t < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  // ─── MkDocs Material SPA navigation ──────────────────────────────────────────
  function onNavigate() {
    initScrollReveal();
    initCounters();
    initCardTilt();
    initParallax();
    initParticles();
    initCodeReveal();
    initTOCTags();
  }

  // ─── Boot ────────────────────────────────────────────────────────────────────
  function boot() {
    injectKeyframes();
    initNavScroll();
    initSmoothAnchors();
    initCopyFlash();
    onNavigate();
  }

  let _firstNav = true;
  if (typeof document$ !== 'undefined') {
    document$.subscribe(() => {
      if (_firstNav) { _firstNav = false; boot(); return; }
      finishProgressBar();
      scrollToTopAnimated();
      onNavigate();
    });

    // Hook navigation start (before new page loads) for the progress bar
    if (typeof location$ !== 'undefined') {
      location$.subscribe(() => { if (!_firstNav) runProgressBar(); });
    }

    boot();
  } else {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', boot);
    } else {
      boot();
    }
  }

})();
