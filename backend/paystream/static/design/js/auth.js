document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = e.target.username.value;
  const password = e.target.password.value;

  try {
    const res = await fetch('/api/v1/auth/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }).then(r => r.json());

    if (res.access) {
      localStorage.setItem('token', res.access);
      toast.success('Welcome back, Commander!');
      bootstrap.Modal.getInstance('#loginModal').hide();
      setTimeout(() => location.reload(), 500);
    } else {
      toast.error(res.detail || 'Login failed');
    }
  } catch (err) {
    toast.error('Network error');
  }
});