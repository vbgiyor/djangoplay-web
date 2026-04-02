(function () {
  const HEADER_HEIGHT = 80;

  // ------------------------------------------------------------
  // Config
  // ------------------------------------------------------------
  function getConfigFromBody() {
    const dataset = document.body?.dataset || {};

    return {
      schemaUrl: dataset.schemaUrl || '/api/v1/schema/',
      accessLoginUrl: dataset.accessLoginUrl || '/accounts/login/',
      supportUrl: dataset.supportUrl || '/support/',
      licenseUrl: dataset.licenseUrl || '/license/',
      publicMonitorUrl: dataset.publicMonitorUrl || '/api-monitor/public/',
      myMonitorUrl: dataset.myMonitorUrl || '/api-monitor/',
    };
  }

  // ------------------------------------------------------------
  // ReDoc Init
  // ------------------------------------------------------------
  function initRedoc() {
    if (typeof Redoc === 'undefined') return;

    const container = document.getElementById('redoc-container');
    if (!container) return;

    const cfg = getConfigFromBody();

    Redoc.init(
      cfg.schemaUrl,
      {
        scrollYOffset: HEADER_HEIGHT,
        hideDownloadButton: true,
        expandResponses: '200,201',
        requiredPropsFirst: true,
        sortPropsAlphabetically: true,
        hideLoading: true,
      },
      container,
      () => insertBanner(cfg)
    );
  }

  function insertBanner(cfg) {
    const info = document.querySelector('.api-info');
    if (!info) return;

    const banner = document.createElement('div');
    banner.innerHTML = `
      <div class="links-container">
        <a href="${cfg.accessLoginUrl}" class="primary-text" target="_blank">Access Platform</a>
        <a href="${cfg.supportUrl}" class="primary-text" target="_blank">Contact Support</a>
        <a href="${cfg.licenseUrl}" class="primary-text" target="_blank">Apache License 2.0</a>
        <a href="${cfg.publicMonitorUrl}" class="primary-text" target="_blank">Public API Monitor</a>
        <a href="${cfg.myMonitorUrl}" class="primary-text" target="_blank">My API Monitor</a>
      </div>
    `;
    info.appendChild(banner);
  }

  // ------------------------------------------------------------
  // JWT Injection
  // ------------------------------------------------------------
  function wrapFetchWithAuthHeader() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const originalFetch = window.fetch;
    window.fetch = function (...args) {
      const [url, config = {}] = args;
      const headers = new Headers(config.headers || {});
      headers.set('Authorization', `Bearer ${token}`);
      return originalFetch(url, { ...config, headers });
    };
  }

  // ------------------------------------------------------------
  // 401 Handling
  // ------------------------------------------------------------
  function wrapFetchWith401Handler() {
    const originalFetch = window.fetch;

    window.fetch = async function (...args) {
      const response = await originalFetch(...args);

      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }

      return response;
    };
  }

  // ------------------------------------------------------------
  // Token Refresh
  // ------------------------------------------------------------
  function scheduleTokenRefresh() {
    setTimeout(() => {
      if (localStorage.getItem('refresh_token')) {
        refreshToken();
      }
    }, 1000);

    setInterval(refreshToken, 10 * 60 * 1000);
  }

  function refreshToken() {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return;

    fetch('/api/v1/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.access) {
          localStorage.setItem('access_token', data.access);
          if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh);
          }
        }
      })
      .catch(() => {});
  }

  // ------------------------------------------------------------
  // Go-to-Top Button
  // ------------------------------------------------------------
  (function () {
    const btn = document.getElementById('redoc-go-top');

    function scrollToApiTitle() {
      const apiInfo = document.querySelector('.api-info');
      if (!apiInfo) return;

      /* 🚫 stop Redoc hash reactions */
      window.__REDOC_SUSPEND_HASH_SCROLL__(true);

      apiInfo.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });

      /* ✅ re-enable after scroll settles */
      setTimeout(() => {
        window.__REDOC_SUSPEND_HASH_SCROLL__(false);
      }, 600);
    }

    window.addEventListener('scroll', () => {
      btn.style.display = window.scrollY > 400 ? 'block' : 'none';
    });

    btn.addEventListener('click', scrollToApiTitle);
  })();

  // ------------------------------------------------------------
  // Scroll Async
  // ------------------------------------------------------------

  (function () {
  let suspendHashScroll = false;

  function scrollToHash() {
    if (suspendHashScroll) return;
    const hash = location.hash;
    if (!hash) return;

    const id = decodeURIComponent(hash.slice(1));

    // 1. Never scroll on tag clicks (they only expand/collapse)
    if (id.startsWith('tag-')) return;

    // 2. Only scroll on operation (endpoint) clicks
    if (!id.includes('operation')) return;

    const el = document.getElementById(id);
    if (!el) return;

    // Wait for collapse/expand animation to finish (~300-400ms)
    setTimeout(() => {
      el.scrollIntoView({
        block: 'start',
        behavior: 'smooth',     // better UX than 'auto'
        inline: 'nearest'
      });
    }, 420); // 420ms → safe value after most animations
  }

  // Override pushState/replaceState to trigger our delayed scroll
  const originalPushState = history.pushState;
  history.pushState = function (...args) {
    originalPushState.apply(this, args);
    scrollToHash();
  };

  const originalReplaceState = history.replaceState;
  history.replaceState = function (...args) {
    originalReplaceState.apply(this, args);
    scrollToHash();
  };

  // Also handle browser back/forward
  window.addEventListener('popstate', scrollToHash);

  // Initial load
  document.addEventListener('DOMContentLoaded', scrollToHash);

  // Allow external code to suspend scrolling if needed
  window.__REDOC_SUSPEND_HASH_SCROLL__ = (value) => {
    suspendHashScroll = value;
  };
})();


/* ============================================================
   Prevent TAG clicks from triggering scroll
   ============================================================ */
  document.addEventListener(
    'click',
    function (e) {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;

      // ReDoc tag links live in the left menu
      const isMenuClick = link.closest('.menu-content');
      if (!isMenuClick) return;

      const href = link.getAttribute('href') || '';

      // Tag clicks → prevent hash navigation, allow collapse
      if (!href.includes('operation')) {
        e.preventDefault();
      }
    },
    true // CAPTURE phase — must be before ReDoc
  );

  // ------------------------------------------------------------
  // Init
  // ------------------------------------------------------------
  function onReady() {
    initRedoc();
    wrapFetchWithAuthHeader();
    wrapFetchWith401Handler();
    scheduleTokenRefresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }
})();


