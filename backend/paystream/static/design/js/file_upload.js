// paystream/static/design/js/file_upload.js
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="file"][name="files"]').forEach(initFileInput);
});

function initFileInput(input) {
    if (input.dataset.init) return;
    input.dataset.init = '1';

    const wrapper = input.closest('.attachment-label, .bug-file-input-wrapper');
    const displayContainer = wrapper.querySelector('[data-role="file-list"]') || createFileList(wrapper);
    const clearAllBtn = wrapper.querySelector('.clear-all-btn') || createClearAll(wrapper);

    function createFileList(wrapper) {
        const div = document.createElement('div');
        div.setAttribute('data-role', 'file-list');
        div.style.marginTop = '8px';
        div.style.maxHeight = '100px';
        div.style.overflowY = 'auto';
        wrapper.appendChild(div);
        return div;
    }

    function createClearAll(wrapper) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = 'Clear All';
        btn.className = 'clear-all-btn';
        btn.style.display = 'none';
        btn.style.marginTop = '8px';
        btn.style.fontSize = '12px';
        btn.style.color = '#dc3545';
        wrapper.appendChild(btn);
        return btn;
    }

    function updateFileList() {
        const files = Array.from(input.files);
        displayContainer.innerHTML = '';
        clearAllBtn.style.display = files.length ? 'block' : 'none';

        if (!files.length) {
            displayContainer.innerHTML = '<div class="text-muted">No file chosen</div>';
            return;
        }

        files.forEach((file, index) => {
            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.justifyContent = 'space-between';
            item.style.alignItems = 'center';
            item.style.padding = '4px 0';
            item.style.borderBottom = '1px solid #eee';

            const name = document.createElement('span');
            name.textContent = file.name;
            name.style.fontSize = '14px';
            name.style.flex = '1';
            name.style.whiteSpace = 'nowrap';
            name.style.overflow = 'hidden';
            name.style.textOverflow = 'ellipsis';

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.innerHTML = '×';
            remove.style.background = 'none';
            remove.style.border = 'none';
            remove.style.color = '#dc3545';
            remove.style.fontSize = '16px';
            remove.style.cursor = 'pointer';

            // CRITICAL: Remove file by recreating file list WITHOUT modifying input.files
            remove.onclick = () => {
                const dt = new DataTransfer();
                Array.from(input.files)
                    .filter((_, i) => i !== index)
                    .forEach(f => dt.items.add(f));
                input.files = dt.files;
                updateFileList();
            };

            item.appendChild(name);
            item.appendChild(remove);
            displayContainer.appendChild(item);
        });
    }

    input.addEventListener('change', updateFileList);
    clearAllBtn.addEventListener('click', () => {
        input.value = ''; // This is safe
        updateFileList();
    });

    // Click on label opens file picker
    wrapper.addEventListener('click', (e) => {
        if (e.target.closest('.file-input-label, .custom-file-btn')) {
            e.preventDefault();
            input.click();
        }
    });

    updateFileList();
}

// Re-init on modal show
document.addEventListener('shown.bs.modal', (e) => {
    if (e.target.id === 'bug-modal') {
        const input = e.target.querySelector('input[name="files"]');
        if (input) initFileInput(input);
    }
});