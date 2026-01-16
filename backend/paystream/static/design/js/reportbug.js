/* static/design/js/reportbug.js */
console.log('reportbug.js START');

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initBugModal() {
    const fileInput = document.getElementById('bug-attachment');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileNameWrapper = fileNameDisplay?.parentElement;
    const fileSizeError = document.getElementById('file-size-error');

    if (!fileInput || !fileNameDisplay || !fileNameWrapper) return;
    if (fileInput.dataset.initialized) return;
    fileInput.dataset.initialized = "true";

    // Clear button
    const existing = fileNameWrapper.querySelector('.clear-file-btn');
    if (existing) existing.remove();

    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.textContent = 'X';
    clearBtn.classList.add('clear-file-btn');
    fileNameWrapper.appendChild(clearBtn);
    clearBtn.style.display = fileInput.files.length ? 'flex' : 'none';

    // File change
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        const name = file?.name || 'No file chosen';
        const size = file?.size || 0;
        fileNameDisplay.textContent = name;
        clearBtn.style.display = fileInput.files.length ? 'flex' : 'none';

        if (size > 10 * 1024 * 1024) {
            fileSizeError.style.display = 'block';
            fileInput.setCustomValidity("File too large (max 10MB).");
        } else {
            fileSizeError.style.display = 'none';
            fileInput.setCustomValidity("");
        }
    });

    // Clear
    clearBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileInput.value = '';
        fileNameDisplay.textContent = 'No file chosen';
        clearBtn.style.display = 'none';
        fileSizeError.style.display = 'none';
        fileInput.setCustomValidity("");
    });
}

// Modal shown → init
document.addEventListener('shown.bs.modal', (e) => {
    if (e.target.id === 'bug-modal') initBugModal();
});

// Pulse animation
function applyPulse() {
    const btn = document.getElementById('bug-report-btn');
    if (btn) {
        btn.style.animation = 'none';
        void btn.offsetHeight;
        btn.style.animation = null;
    }
}
document.addEventListener('DOMContentLoaded', applyPulse);
setTimeout(applyPulse, 500);

// Auto-hide Django messages
document.addEventListener("DOMContentLoaded", () => {
    const messages = document.querySelectorAll(".messages > div"); // selects each message div
    messages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = "opacity 0.5s ease-out";
            msg.style.opacity = "0";
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    });
});

console.log('reportbug.js READY');