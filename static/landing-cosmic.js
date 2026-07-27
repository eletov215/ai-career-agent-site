(() => {
  const body = document.body;
  if (!body || !body.classList.contains('landing-body')) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  let ticking = false;
  const updateParallax = () => {
    const maxShift = window.innerWidth > 1024 ? 120 : window.innerWidth > 767 ? 72 : 34;
    const shift = Math.min(window.scrollY * 0.12, maxShift);
    body.style.setProperty('--site-cosmic-shift', `${shift}px`);
    ticking = false;
  };
  const requestTick = () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(updateParallax);
  };
  updateParallax();
  window.addEventListener('scroll', requestTick, { passive: true });
  window.addEventListener('resize', requestTick);
})();
