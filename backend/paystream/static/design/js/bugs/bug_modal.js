
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('bug-modal-messages-container');
    if (!container || container.children.length === 0) return;

    const modalBody = document.querySelector('#bug-modal .modal-body');
    if (!modalBody) return;

    modalBody.insertAdjacentHTML('afterbegin', container.innerHTML);

    const bugModal = new bootstrap.Modal(document.getElementById('bug-modal'), {
        backdrop: 'static',
        keyboard: false
    });
    bugModal.show();

    if (container.querySelector('.alert-success')) {
        setTimeout(() => bugModal.hide(), 3000);
    }
});

// document.querySelector('form').addEventListener('submit', function(e) {
//     const githubInput = document.getElementById('bug-github');
//     if (githubInput.value) {
//         const pattern = /^https:\/\/github\.com\/[^\/]+\/[^\/]+\/issues\/\d+$/;
//         if (!pattern.test(githubInput.value)) {
//             githubInput.classList.add('is-invalid');
//             e.preventDefault();
//             return false;
//         } else {
//             githubInput.classList.remove('is-invalid');
//         }
//     }
// });

document.addEventListener('DOMContentLoaded', function () {
    const bugModalEl = document.getElementById('bug-modal');
    if (!bugModalEl) return;

    const bugModal = bootstrap.Modal.getOrCreateInstance(bugModalEl);
    const form = bugModalEl.querySelector('form');
    const githubInput = bugModalEl.querySelector('#bug-github');

    if (!form) return;

    form.addEventListener('submit', function (e) {
        // GitHub URL validation (client-side)
        if (githubInput && githubInput.value) {
            const pattern = /^https:\/\/github\.com\/[^\/]+\/[^\/]+\/issues\/\d+$/;
            if (!pattern.test(githubInput.value)) {
                githubInput.classList.add('is-invalid');
                e.preventDefault();       // Stop form submission
                return false;             // Keep modal open so user can fix it
            } else {
                githubInput.classList.remove('is-invalid');
            }
        }

        // If validation passed, let the form submit and close the modal immediately.
        // The page will redirect, and the user will see Django messages on the parent page.
        bugModal.hide();
    });
});

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss bootstrap alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(function (alertEl) {
        setTimeout(function () {
            // Use Bootstrap's Alert interface if available
            if (window.bootstrap && bootstrap.Alert) {
                const alert = bootstrap.Alert.getOrCreateInstance(alertEl);
                alert.close();
            } else {
                alertEl.style.display = 'none';
            }
        }, 5000); // 5 seconds
    });
});