
// $(function() {
//     // --------------------------------------------------
//     // Initialize Select2 for all dropdowns
//     // --------------------------------------------------
//     $('.select2').select2({
//         width: '100%',
//         placeholder: 'Select an option',
//         allowClear: true,
//         theme: 'default' // For space theme compatibility
//     });

//     // --------------------------------------------------
//     // Auto-slug from name (works for both add/edit)
//     // --------------------------------------------------
//     const nameField = $('#id_name');
//     const slugField = $('#id_slug');
//     if (nameField.length && slugField.length) {
//         nameField.on('blur', function() {
//             if (!slugField.val()) {
//                 let slug = $(this).val().toLowerCase().trim()
//                     .replace(/[^a-z0-9]+/g, '-')
//                     .replace(/^-+|-+$/g, '');
//                 slugField.val(slug);
//             }
//         });
//     }

//     // --------------------------------------------------
//     // Responsive: Adjust Select2 on mobile
//     // --------------------------------------------------
//     if ($(window).width() < 768) {
//         $('.select2').select2('destroy');
//         $('.select2').select2({
//             width: '100%',
//             dropdownParent: $('body') // Prevent z-index issues on mobile
//         });
//     }

//     // --------------------------------------------------
//     // Form validation preview (UX: real-time errors)
//     // --------------------------------------------------
//     $('input, select, textarea').on('blur', function() {
//         const field = $(this);
//         if (field.hasClass('is-invalid')) {
//             field.removeClass('is-invalid').next('.invalid-feedback').remove();
//         }
//     });

//     // --------------------------------------------------
//     // Button loading state on submit
//     // --------------------------------------------------
//     $('form').on('submit', function() {
//         const submitBtn = $(this).find('button[type="submit"]');
//         submitBtn.prop('disabled', true)
//                  .html('<i class="fas fa-spinner fa-spin me-2"></i>Saving...');
//     });

//     // --------------------------------------------------
//     // Modal close on outside click (for delete modal in edit)
//     // --------------------------------------------------
//     $('.modal').on('hidden.bs.modal', function () {
//         const form = $(this).find('form')[0];
//         if (form) {
//             form.reset();
//         }
//     });

//     // --------------------------------------------------
//     // Collapse chevron toggle for Audit & History sections
//     // (was inline in template before)
//     // --------------------------------------------------
//     ['auditCollapse', 'historyCollapse'].forEach(function(id) {
//         const header = document.querySelector('[data-bs-target="#' + id + '"]');
//         if (!header) return;

//         const icon = header.querySelector('i.fa-chevron-down, i.fa-chevron-up');
//         const collapse = document.getElementById(id);
//         if (!collapse || !icon) return;

//         collapse.addEventListener('shown.bs.collapse', function () {
//             icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
//         });

//         collapse.addEventListener('hidden.bs.collapse', function () {
//             icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
//         });
//     });

//     // --------------------------------------------------
//     // Toggle `.collapsed` class on any collapse header
//     // (matches your last inline script)
//     // --------------------------------------------------
//     $('[data-bs-toggle="collapse"]').on('click', function () {
//         $(this).toggleClass('collapsed');
//     });

//     // --------------------------------------------------
//     // Enable Save button only when form is dirty
//     // (moved from inline <script> to here)
//     // --------------------------------------------------
//     const formEl = document.querySelector('form');
//     if (formEl) {
//         const saveBtn = formEl.querySelector("button[type='submit']");
//         if (saveBtn) {
//             const initialFormData = new FormData(formEl);

//             function formChanged() {
//                 const currentData = new FormData(formEl);
//                 for (let [key, val] of currentData.entries()) {
//                     if (initialFormData.get(key) !== val) {
//                         return true;
//                     }
//                 }
//                 return false;
//             }

//             function toggleSaveBtn() {
//                 if (formChanged()) {
//                     saveBtn.disabled = false;
//                     saveBtn.classList.remove("btn-secondary");
//                     saveBtn.classList.add("btn-primary");
//                 } else {
//                     saveBtn.disabled = true;
//                     saveBtn.classList.remove("btn-primary");
//                     saveBtn.classList.add("btn-secondary");
//                 }
//             }

//             // Initial state
//             saveBtn.disabled = true;
//             toggleSaveBtn();

//             formEl.addEventListener("input", toggleSaveBtn);
//             formEl.addEventListener("change", toggleSaveBtn);
//         }
//     }
// });

/////////////////

// working

// $(function () {
//     // Initialize Select2 on all <select> elements
//     $('select').select2({
//         width: '100%',
//         allowClear: true,
//         placeholder: "Select an option"
//     });

//     // CRITICAL: Fix form submission
//     $('form').on('submit', function (e) {
//         // Do NOT preventDefault() — let the form submit normally
//         const $btn = $(this).find('button[type="submit"]');
//         $btn.prop('disabled', true)
//             .html('<i class="fas fa-spinner fa-spin me-2"></i>Saving...');
        
//         // DO NOT return false → let form submit!
//         // Just showing spinner is enough
//     });

//     // Auto-slug (if needed elsewhere)
//     const nameField = $('#id_name');
//     const slugField = $('#id_slug');
//     if (nameField.length && slugField.length) {
//         nameField.on('blur', function () {
//             if (!slugField.val()) {
//                 let slug = $(this).val().toLowerCase().trim()
//                     .replace(/[^a-z0-9]+/g, '-')
//                     .replace(/^-+|-+$/g, '');
//                 slugField.val(slug);
//             }
//         });
//     }
// });
///////////

/// original

$(function() {
    // Initialize Select2 for all dropdowns
    $('.select2').select2({
        width: '100%',
        placeholder: 'Select an option',
        allowClear: true,
        theme: 'default' // For space theme compatibility
    });

    // Auto-slug from name (works for both add/edit)
    const nameField = $('#id_name');
    const slugField = $('#id_slug');
    if (nameField.length && slugField.length) {
        nameField.on('blur', function() {
            if (!slugField.val()) {
                let slug = $(this).val().toLowerCase().trim()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/^-+|-+$/g, '');
                slugField.val(slug);
            }
        });
    }

    // Responsive: Adjust Select2 on mobile
    if ($(window).width() < 768) {
        $('.select2').select2('destroy');
        $('.select2').select2({
            width: '100%',
            dropdownParent: $('body') // Prevent z-index issues on mobile
        });
    }

    // Form validation preview (UX: real-time errors)
    $('input, select, textarea').on('blur', function() {
        const field = $(this);
        if (field.hasClass('is-invalid')) {
            field.removeClass('is-invalid').next('.invalid-feedback').remove();
        }
    });

    // // Button loading state on submit
    // $('form').on('submit', function() {
    //     const submitBtn = $(this).find('button[type="submit"]');
    //     submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-2"></i>Saving...');
    // });

    // Modal close on outside click (for delete modal in edit)
    $('.modal').on('hidden.bs.modal', function () {
        $(this).find('form')[0].reset();
    });
});