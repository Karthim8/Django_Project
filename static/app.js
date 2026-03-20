/* ═══════════════════════════════════════
   app.js — shared across all NexusLink pages
   ═══════════════════════════════════════ */

// ── Custom cursor ─────────────────────────────
(function(){
  const cur   = document.getElementById('cursor');
  const trail = document.getElementById('cursorTrail');
  if (!cur || !trail) return;

  let mx=0, my=0, tx=0, ty=0;
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    cur.style.left = mx + 'px';
    cur.style.top  = my + 'px';
  });
  (function anim(){
    tx += (mx - tx) * 0.1;
    ty += (my - ty) * 0.1;
    trail.style.left = tx + 'px';
    trail.style.top  = ty + 'px';
    requestAnimationFrame(anim);
  })();

  document.querySelectorAll('button, a, .feat-card, .profile-card, .room-card, .peer-card, .res-item, .res-card-full, .room-page-card, .chat-item, .step, .how-step, .dropdown-item, .user-avatar-nav').forEach(el => {
    el.addEventListener('mouseenter', () => {
      cur.style.transform   = 'translate(-50%,-50%) scale(2)';
      trail.style.width     = '56px';
      trail.style.height    = '56px';
      trail.style.opacity   = '0.3';
    });
    el.addEventListener('mouseleave', () => {
      cur.style.transform   = 'translate(-50%,-50%) scale(1)';
      trail.style.width     = '36px';
      trail.style.height    = '36px';
      trail.style.opacity   = '0.5';
    });
  });
})();

// ── Avatar Dropdown Toggle ───────────────────
document.addEventListener('DOMContentLoaded', function() {
  var containers = document.querySelectorAll('.avatar-dropdown-container');
  
  containers.forEach(function(container) {
    var avatar = container.querySelector('.user-avatar-nav');
    var dropdown = container.querySelector('.avatar-dropdown');
    
    if (!avatar || !dropdown) return;
    
    avatar.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      dropdown.classList.toggle('active');
    });
  });
  
  document.addEventListener('click', function(e) {
    document.querySelectorAll('.avatar-dropdown').forEach(function(dropdown) {
      if (!dropdown.closest('.avatar-dropdown-container').contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  });
});

// ── Scroll reveal ─────────────────────────────
(function(){
  const obs = new IntersectionObserver(entries => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 80);
      }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
})();

// ── Counter animation ─────────────────────────
(function(){
  const counterObs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.querySelectorAll('[data-count]').forEach(el => {
        const target = +el.dataset.count;
        let cur = 0;
        const step = target / 60;
        const timer = setInterval(() => {
          cur += step;
          if (cur >= target) { cur = target; clearInterval(timer); }
          el.textContent = target >= 1000
            ? Math.floor(cur).toLocaleString()
            : Math.floor(cur);
        }, 16);
      });
      counterObs.unobserve(entry.target);
    });
  }, { threshold: 0.5 });
  const sb = document.querySelector('.stats-bar');
  if (sb) counterObs.observe(sb);
})();

// ── Navbar scroll shrink ──────────────────────
(function(){
  const nav = document.getElementById('navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  });
})();

// ── Follow button toggle ──────────────────────
document.querySelectorAll('.follow-btn').forEach(btn => {
  if (btn.dataset.bound) return;
  btn.dataset.bound = '1';
  btn.addEventListener('click', () => {
    if (btn.textContent.trim() === 'Follow') {
      btn.textContent = '✓ Requested';
      btn.classList.add('requested');
    } else {
      btn.textContent = 'Follow';
      btn.classList.remove('requested');
    }
  });
});
