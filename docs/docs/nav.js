// Shared sidebar navigation — injected into every docs page.
(function () {
  const page = location.pathname.split('/').pop() || 'index.html';

  function a(href, label, sub) {
    const cls = (href === page || (page === '' && href === 'index.html'))
      ? (sub ? 'sidebar-sublink active' : 'sidebar-link active')
      : (sub ? 'sidebar-sublink' : 'sidebar-link');
    return `<a href="${href}" class="${cls}">${label}</a>`;
  }

  const html = `
    <div class="sidebar-group">
      <div class="sidebar-label">Getting Started</div>
      ${a('index.html', 'Installation')}
      ${a('index.html', 'Configuration')}
      ${a('index.html', 'Quick start')}
      ${a('index.html', 'Extra context')}
    </div>
    <div class="sidebar-group">
      <div class="sidebar-label">Workflows</div>
      ${a('workflows.html', 'Overview')}
      ${a('workflows.html', 'deepresearch', true)}
      ${a('workflows.html', 'lit', true)}
      ${a('workflows.html', 'source', true)}
      ${a('workflows.html', 'review', true)}
      ${a('workflows.html', 'audit', true)}
      ${a('workflows.html', 'replicate', true)}
      ${a('workflows.html', 'compare', true)}
      ${a('workflows.html', 'draft', true)}
      ${a('workflows.html', 'autoresearch', true)}
      ${a('workflows.html', 'watch', true)}
    </div>
    <div class="sidebar-group">
      <div class="sidebar-label">Utilities</div>
      ${a('utilities.html', 'search')}
      ${a('utilities.html', 'show')}
      ${a('utilities.html', 'config-check')}
    </div>
    <div class="sidebar-group">
      <div class="sidebar-label">Reference</div>
      ${a('reference.html', 'ADS query syntax')}
      ${a('reference.html', 'Output format')}
      ${a('reference.html', 'Local LLM setup')}
    </div>
  `;

  const el = document.getElementById('sidebar');
  if (el) el.innerHTML = html;

  // Highlight active section on scroll (anchor-based)
  const sections = document.querySelectorAll('.doc-section[id]');
  const sublinks = document.querySelectorAll('.sidebar-sublink');
  if (!sections.length || !sublinks.length) return;

  function onScroll() {
    let current = '';
    sections.forEach(s => {
      if (s.getBoundingClientRect().top <= 90) current = s.id;
    });
    sublinks.forEach(l => {
      const href = l.getAttribute('href');
      const anchor = href.includes('#') ? href.split('#')[1] : null;
      if (anchor) l.classList.toggle('active', anchor === current);
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
