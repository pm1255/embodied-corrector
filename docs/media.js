'use strict';

// A dropped image request must not leave a permanent empty figure.
document.querySelectorAll('main .figure-button img[data-fallback]').forEach(image => {
  const button = image.closest('.figure-button');
  const originalLabel = button.getAttribute('aria-label');
  const primary = image.getAttribute('src');
  const networkSource = image.dataset.source || primary;
  const fallback = image.dataset.fallback;
  const sources = [primary, fallback, networkSource + '?media_retry=1'];
  const status = document.createElement('span');
  status.className = 'figure-load-status';
  status.setAttribute('role', 'status');
  button.append(status);
  let attempt = 0;
  let timer;

  function ready() {
    if (!image.complete || !image.naturalWidth) return false;
    clearTimeout(timer);
    button.dataset.mediaState = 'ready';
    button.setAttribute('aria-busy', 'false');
    button.setAttribute('aria-label', originalLabel);
    status.hidden = true;
    return true;
  }
  function pending() {
    clearTimeout(timer);
    button.dataset.mediaState = 'loading';
    button.setAttribute('aria-busy', 'true');
    status.hidden = false;
    status.textContent = 'Loading figure…';
    // Safari can keep an interrupted request pending for a long time.
    timer = setTimeout(() => { if (!ready()) nextSource(); }, 12000);
  }
  function nextSource() {
    clearTimeout(timer);
    if (ready()) return;
    attempt += 1;
    if (attempt >= sources.length) {
      button.dataset.mediaState = 'failed';
      button.setAttribute('aria-busy', 'false');
      button.setAttribute('aria-label', originalLabel.replace(/^Enlarge /, 'Retry loading '));
      status.hidden = false;
      status.textContent = 'Figure could not load. Select to retry.';
      return;
    }
    pending();
    image.src = sources[attempt];
  }
  image.addEventListener('load', ready);
  image.addEventListener('error', nextSource);
  button.addEventListener('click', event => {
    if (button.dataset.mediaState !== 'failed') return;
    event.preventDefault();
    event.stopImmediatePropagation();
    attempt = 0;
    button.setAttribute('aria-label', originalLabel);
    pending();
    image.src = networkSource + '?media_retry=' + Date.now();
  }, true);
  if (!ready()) {
    pending();
    if (image.complete) nextSource();
  }
});

// Load offscreen video covers lazily so paper figures can load first.
const deferredPosters = document.querySelectorAll('video[data-poster]');
function loadPoster(video) {
  if (!video.hasAttribute('poster')) video.poster = video.dataset.poster;
}
if ('IntersectionObserver' in window) {
  const posterObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      loadPoster(entry.target);
      posterObserver.unobserve(entry.target);
    });
  }, {rootMargin: '800px 0px'});
  deferredPosters.forEach(video => posterObserver.observe(video));
} else {
  deferredPosters.forEach(loadPoster);
}
