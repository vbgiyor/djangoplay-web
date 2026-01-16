window.api = {
  token: () => localStorage.getItem('token'),
  headers: () => {
    const token = api.token();
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  },
  get: (url) => fetch(url, {
    method: 'GET',
    headers: api.headers(),
    credentials: 'include'
  }).then(r => {
    if (!r.ok) throw r;
    return r.json();
  }),
  post: (url, data) => fetch(url, {
    method: 'POST',
    headers: api.headers(),
    body: JSON.stringify(data),
    credentials: 'include'
  }).then(r => r.json()),
  patch: (url, data) => fetch(url, {
    method: 'PATCH',
    headers: api.headers(),
    body: JSON.stringify(data),
    credentials: 'include'
  }).then(r => r.json()),
  delete: (url, data) => fetch(url, {
    method: 'DELETE',
    headers: api.headers(),
    credentials: 'include'
}).then(r => r.json())
};