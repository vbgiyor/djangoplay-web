async function loadUser() {
  try {
    let res = null;
    let source = '';

    // 1. Try JWT first
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const jwtRes = await fetch('/api/v1/auth/me/jwt/', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        if (jwtRes.ok) {
          res = await jwtRes.json();
          source = 'JWT';
        }
      } catch (e) {
        localStorage.removeItem('token');
      }
    }

    // 2. Fall back to session
    if (!res) {
      const sessionRes = await fetch('/api/v1/auth/me/', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
          'Content-Type': 'application/json'
        }
      });

      if (!sessionRes.ok) {
        throw new Error(`Session failed: ${sessionRes.status}`);
      }
      res = await sessionRes.json();
      source = 'Session';
    }

    window.user = res;
    console.log(`${source} User loaded:`, window.user.username);

    document.querySelectorAll('[data-perm]').forEach(el => {
      const perm = el.dataset.perm;
      if (!window.user.permissions.includes(perm)) {
        el.remove();
      }
    });

  } catch (e) {
    console.log("Not logged in");
    window.user = null;
  }
}

loadUser();