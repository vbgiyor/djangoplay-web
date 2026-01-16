// static/design/js/admin/change_form_permissions.js

document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');

    // Read flags from data attributes (safe no-op if not present)
    const hasChangePermission =
        form && form.dataset.hasChange === 'true';
    const isAddFlag =
        form && form.dataset.isAdd === 'true';

    // ----------------------------------------------------
    // 1) History + Audit collapse chevron toggle
    //    (same behavior as your original block)
    // ----------------------------------------------------
    ['auditCollapse', 'historyCollapse'].forEach(id => {
        const header = document.querySelector(`[data-bs-target="#${id}"]`);
        if (!header) return;

        const icon = header.querySelector('i.fa-chevron-down, i.fa-chevron-up');
        const collapse = document.getElementById(id);
        if (!collapse || !icon) return;

        collapse.addEventListener('shown.bs.collapse', () => {
            icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
        });
        collapse.addEventListener('hidden.bs.collapse', () => {
            icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
        });
    });

    // ----------------------------------------------------
    // 2) Header click → toggle .collapsed
    //    (same as your separate script at the bottom)
    // ----------------------------------------------------
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(el => {
        el.addEventListener('click', () => el.classList.toggle('collapsed'));
    });

    // ----------------------------------------------------
    // 3) Select2 on all <select>
    //    (same as your jQuery block)
    // ----------------------------------------------------
    if (window.jQuery && jQuery.fn && jQuery.fn.select2) {
        jQuery(function () {
            jQuery('select').select2({
                allowClear: true
            });
        });
    }

    // No form? then nothing else to do
    if (!form) return;

    // ----------------------------------------------------
    // 4) If user does NOT have change permission:
    //    - Make all fields read-only/disabled
    //    - Disable submit buttons
    //    - DO NOT set up change tracking
    // ----------------------------------------------------
    if (!hasChangePermission) {
        form.querySelectorAll('input, textarea, select').forEach(el => {
            const type = (el.type || '').toLowerCase();

            // Keep hidden + CSRF intact
            if (type === 'hidden' || el.name === 'csrfmiddlewaretoken') return;

            // Skip buttons here, handle separately
            if (type === 'submit' || type === 'button') return;

            if (el.tagName === 'SELECT') {
                el.disabled = true;
            } else {
                el.readOnly = true;
            }
        });

        // Disable submit buttons (Save/Save Changes)
        form.querySelectorAll("button[type='submit']").forEach(btn => {
            btn.disabled = true;
            btn.classList.add('btn-secondary');
            btn.classList.remove('btn-primary');
        });

        // IMPORTANT: stop here so we don't add "dirty form" behavior
        return;
    }

    // ----------------------------------------------------
    // 5) Original "enable Save only when changed" logic
    //    (identical to your previous code)
    // ----------------------------------------------------
    const saveBtn = document.querySelector("button[type='submit']");
    if (!saveBtn) return;

    // Original behavior: detect "add form" using URL,
    // but also respect the data-is-add flag if present.
    const isAdd = (isAddFlag === true) || window.location.href.includes('/add/');

    // For add forms: Save enabled immediately (unchanged)
    if (isAdd) {
        saveBtn.disabled = false;
        return;
    }

    const initial = {};
    new FormData(form).forEach((v, k) => {
        initial[k] = v;
    });

    function changed() {
        const current = new FormData(form);
        for (let [key, val] of current.entries()) {

            // Same logic as before: ignore file fields unless a new file is chosen
            const field = form.querySelector(`[name="${key}"]`);
            if (field && field.type === 'file') {
                if (val && val.name) return true;
                continue;
            }

            if (initial[key] !== val) return true;
        }
        return false;
    }

    function update() {
        if (changed()) {
            saveBtn.disabled = false;
            saveBtn.classList.add("btn-primary");
            saveBtn.classList.remove("btn-secondary");
        } else {
            saveBtn.disabled = true;
            saveBtn.classList.add("btn-secondary");
            saveBtn.classList.remove("btn-primary");
        }
    }

    // Initial state (same as before)
    saveBtn.disabled = true;
    update();

    form.addEventListener("input", update);
    form.addEventListener("change", update);
});
