window.toast = {
  success: (msg) => {
    const t = document.createElement('div');
    t.className = 'toast align-items-center text-white bg-success border-0';
    t.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    document.body.appendChild(t);
    new bootstrap.Toast(t).show();
    setTimeout(() => t.remove(), 5000);
  },
  error: (msg) => {
    const t = document.createElement('div');
    t.className = 'toast align-items-center text-white bg-danger border-0';
    t.innerHTML = `<div class="d-flex"><div class="toast-body">${msg}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    document.body.appendChild(t);
    new bootstrap.Toast(t).show();
    setTimeout(() => t.remove(), 5000);
  }
};