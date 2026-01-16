// static/design/js/login_page.js

document.addEventListener('DOMContentLoaded', function () {
    const resetTabItem = document.getElementById('reset-tab-item');
    const resetTabBtn = document.getElementById('reset-tab');
    const forgotLink = document.getElementById('forgot-password-link');

    const resetPane = document.getElementById('reset');
    const resetForm = resetPane ? resetPane.querySelector('form') : null;
    const resetIdentifierInput = document.getElementById('id_reset_identifier');
    const resetSubmitBtn = resetForm ? resetForm.querySelector('button[type="submit"]') : null;

    // ------------------------------
    // Reset tab show/hide logic
    // ------------------------------
    function showResetTab() {
        if (!resetTabItem || !resetTabBtn) return;

        resetTabItem.classList.remove('d-none');

        // Hide "Forgot Password?" link while on reset tab
        if (forgotLink) {
            forgotLink.style.display = 'none';
        }

        // Use Bootstrap's Tab API if present
        if (window.bootstrap && bootstrap.Tab) {
            const tab = new bootstrap.Tab(resetTabBtn);
            tab.show();
        } else {
            // Fallback: manual class toggling
            const panes = document.querySelectorAll('#authTabContent .tab-pane');
            panes.forEach(function (pane) {
                pane.classList.remove('show', 'active');
            });
            if (resetPane) {
                resetPane.classList.add('show', 'active');
            }
        }

        // Focus the identifier input and sync button state
        if (resetIdentifierInput) {
            resetIdentifierInput.focus();
        }
        updateResetButtonState();
    }

    function hideResetTab() {
        if (!resetTabItem) return;
        resetTabItem.classList.add('d-none');

        // Make sure reset tab is not visually active
        if (resetTabBtn) {
            resetTabBtn.classList.remove('active');
        }

        // Show "Forgot Password?" link again
        if (forgotLink) {
            forgotLink.style.display = '';
        }
    }

    // ------------------------------
    // Enable/disable reset button
    // ------------------------------
    function updateResetButtonState() {
        if (!resetSubmitBtn || !resetIdentifierInput) return;
        const value = resetIdentifierInput.value.trim();
        resetSubmitBtn.disabled = value.length === 0;
    }

    // Initial state: keep button disabled until user types something
    if (resetSubmitBtn) {
        resetSubmitBtn.disabled = true;
    }

    if (resetIdentifierInput) {
        resetIdentifierInput.addEventListener('input', updateResetButtonState);
    }

    // ------------------------------
    // Wire up "Forgot Password?" link
    // ------------------------------
    if (forgotLink) {
        forgotLink.addEventListener('click', function (e) {
            e.preventDefault();
            showResetTab();
        });
    }

    // When user switches to Sign In / Sign Up, hide Reset tab
    ['signin-tab', 'signup-tab'].forEach(function (id) {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.addEventListener('shown.bs.tab', function () {
            hideResetTab();
        });
    });

    // Auto-open Reset tab if ?reset=1 in query params
    const params = new URLSearchParams(window.location.search);
    if (params.get('reset') === '1') {
        showResetTab();
    }

    // ------------------------------
    // Auto-dismiss alerts after 4s
    // ------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.classList.remove('show');
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 450);
        }, 4000);
    });
});
