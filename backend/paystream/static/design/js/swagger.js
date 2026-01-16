(function () {
  // ------------- Config from <body> data-* -------------

  function getConfigFromBody() {
    const body = document.body || {};
    const dataset = body.dataset || {};

    return {
      schemaUrl: dataset.schemaUrl || '/api/v1/schema/',
      accessLoginUrl: dataset.accessLoginUrl || '/accounts/login/',
      supportUrl: dataset.supportUrl || '/support/',
      licenseUrl: dataset.licenseUrl || '/license/',
      publicMonitorUrl: dataset.publicMonitorUrl || '/api-monitor/public/',
      myMonitorUrl: dataset.myMonitorUrl || '/api-monitor/'
    };
  }

  // ------------- Swagger UI Init -------------

  function initSwaggerUI(cfg) {
    if (typeof SwaggerUIBundle === 'undefined') {
      // Swagger libs not loaded
      return;
    }

    const ui = SwaggerUIBundle({
      url: cfg.schemaUrl,
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis],
      plugins: [
        SwaggerUIBundle.plugins.DownloadUrl,
        () => ({
          wrapComponents: {
            authorizeBtn: () => () => null // Hides Authorize button
          }
        })
      ],
      docExpansion: 'none',
      displayRequestDuration: true,
      persistAuthorization: false,
      tryItOutEnabled: true,
      layout: 'BaseLayout',

      requestInterceptor: (req) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          req.headers['Authorization'] = 'Bearer ' + token;
        }
        return req;
      },

      responseInterceptor: (res) => {
        if (res.status === 401 && res.url && !res.url.includes('/token/')) {
          const hadToken = !!localStorage.getItem('access_token');
          const username = localStorage.getItem('username') || 'unknown';

          if (hadToken) {
            console.log(`[JWT] Session expired for user: ${username}`);
            fetch('/api/v1/auth/log/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ event: 'session_expired', user: username })
            }).catch(() => {});
          }

          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          showReloginModal(hadToken ? 'expired' : 'login');
        }
        return res;
      }
    });

    window.ui = ui;
  }

  // ------------- Token Refresh -------------

  function refreshToken() {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return;

    fetch('/api/v1/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.access) {
          localStorage.setItem('access_token', data.access);
          if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh);
          }
        }
      })
      .catch(() => {
        console.warn('Refresh failed. Will prompt on next API call.');
      });
  }

  // expose globally like before
  window.refreshToken = refreshToken;

  // ------------- Re-login Modal -------------

  function showReloginModal(mode) {
    if (document.getElementById('reloginModal')) return;

    const isExpired = mode === 'expired';
    const title = isExpired ? 'Session Expired' : 'Authentication Required';
    const message = isExpired
      ? 'Your session has expired. Please log in again.'
      : 'You need to log in to access this API.';

    const savedUsername = localStorage.getItem('remembered_username') || '';
    const savedRemember = localStorage.getItem('remember_me') === 'true';

    const modalHtml = `
      <div class="modal fade" id="reloginModal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title text-${isExpired ? 'danger' : 'primary'}">${title}</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <p class="mb-3">${message}</p>
              <form id="reloginForm">
                <div class="mb-3">
                  <label class="form-label">Username or Email</label>
                  <input type="text" name="username" class="form-control" value="${savedUsername}" required autofocus>
                </div>
                <div class="mb-3">
                  <label class="form-label">Password</label>
                  <input type="password" name="password" class="form-control" required>
                </div>
                <div class="mb-3 form-check">
                  <input type="checkbox" class="form-check-input" id="rememberMe" name="remember_me" ${savedRemember ? 'checked' : ''}>
                  <label class="form-check-label" for="rememberMe">Remember me (30 days)</label>
                </div>
                <div id="loginError" class="text-danger small mb-2" style="display:none;"></div>
                <button type="submit" class="btn btn-primary w-100">
                  <span class="spinner-border spinner-border-sm d-none" role="status"></span>
                  Log In
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>`;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const modalElement = document.getElementById('reloginModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();

    const form = document.getElementById('reloginForm');
    const errorDiv = document.getElementById('loginError');
    const spinner = form.querySelector('.spinner-border');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorDiv.style.display = 'none';
      spinner.classList.remove('d-none');

      const username = form.username.value.trim();
      const password = form.password.value;
      const remember_me = form.remember_me?.checked || false;

      try {
        const res = await fetch('/api/v1/auth/token/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password, remember_me })
        });

        const data = await res.json();

        if (res.ok && data.access) {
          localStorage.setItem('access_token', data.access);
          localStorage.setItem('refresh_token', data.refresh);
          localStorage.setItem('username', username);

          if (remember_me) {
            localStorage.setItem('remember_me', 'true');
            localStorage.setItem('remembered_username', username);
          } else {
            localStorage.removeItem('remember_me');
            localStorage.removeItem('remembered_username');
          }

          console.log(`[JWT] Re-authenticated: ${username} | remember_me: ${remember_me}`);
          fetch('/api/v1/auth/log/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event: 're_authenticated', user: username })
          }).catch(() => {});

          modal.hide();
          setTimeout(() => location.reload(), 300);
        } else {
          errorDiv.textContent = data.detail || 'Invalid credentials';
          errorDiv.style.display = 'block';
        }
      } catch (err) {
        errorDiv.textContent = 'Invalid credentials.';
        errorDiv.style.display = 'block';
      } finally {
        spinner.classList.add('d-none');
      }
    });
  }

  // expose globally like before
  window.showReloginModal = showReloginModal;

  // ------------- Custom Footer / Info Block -------------

function insertCustomInfo(cfg) {
  // Keep checking; if Swagger replaces .info, we restore our content
  setInterval(() => {
    const info = document.querySelector('.swagger-ui .info');
    if (!info) return;

    // If our custom block is already there, do nothing
    if (info.querySelector('.custom-info-content')) {
      return;
    }

    info.innerHTML = `
      <div class="custom-info-content">
        <h4 class="djangoplay-heading">API Explorer</h4>
        <p class="welcome-name">
          Access the full capabilities of the DjangoPlay platform through our robust and secure APIs.
        </p>
        <div class="links-container">
          <a href="${cfg.accessLoginUrl}" class="primary-text" target="_blank">Access Platform</a>
          <a href="${cfg.supportUrl}" class="primary-text" target="_blank">Contact Support</a>
          <a href="${cfg.licenseUrl}" class="primary-text" target="_blank">Apache License 2.0</a>
          <a href="${cfg.publicMonitorUrl}" class="primary-text" target="_blank">Public API Monitor</a>
          <a href="${cfg.myMonitorUrl}" class="primary-text" target="_blank">My API Monitor</a>
        </div>
      </div>
    `;

    info.style.visibility = 'visible';
    info.style.marginTop = '10px';

    const heading = info.querySelector('.djangoplay-heading');
    if (heading) {
      heading.style.fontFamily = "'Aoboshi One', sans-serif";
    }
  }, 500);  // 0.5s is fine; reduce/increase if you like
}


  // ------------- Init on window load -------------

  window.addEventListener('load', function () {
    const cfg = getConfigFromBody();
    initSwaggerUI(cfg);
    insertCustomInfo(cfg);
  });
})();
