async function initSettings() {
    if (!initAdminBase('settings')) return;
    await loadSettings();
}

async function loadSettings() {
    try {
        const settings = await api.getSettings();
        
        document.getElementById('set-brand-name').value = settings.brand_name || '';
        document.getElementById('set-rzp-id').value = settings.razorpay_key_id || '';
        
        if (settings.brand_logo_url) {
            document.getElementById('settings-logo-preview').innerHTML = `<img src="http://localhost:8080${settings.brand_logo_url}" style="width:100%;height:100%;object-fit:contain"/>`;
        }
    } catch (err) {
        showToast('Failed to load settings', 'error');
    }
}

async function handleLogoUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById('logo-status');
    const preview  = document.getElementById('settings-logo-preview');
    statusEl.textContent = 'Uploading...';
    statusEl.style.color = 'var(--text-muted)';

    try {
        const result = await api.uploadSettingsLogo(file);
        preview.innerHTML = `<img src="http://localhost:8080${result.url}" style="width:100%;height:100%;object-fit:contain"/>`;
        statusEl.textContent = 'Logo uploaded! Remember to save settings.';
        statusEl.style.color = 'var(--success)';
        
        // Also update the sidebar immediately for preview
        updateBrandingUI(document.getElementById('set-brand-name').value, result.url);
    } catch (err) {
        statusEl.textContent = 'Upload failed: ' + err.message;
        statusEl.style.color = 'var(--danger)';
    }
}

async function saveSettings() {
    const btn = document.getElementById('save-settings-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    const payload = {
        brand_name: document.getElementById('set-brand-name').value.trim(),
        razorpay_key_id: document.getElementById('set-rzp-id').value.trim(),
    };

    const secret = document.getElementById('set-rzp-secret').value.trim();
    if (secret) {
        payload.razorpay_key_secret = secret;
    }

    try {
        await api.updateSettings(payload);
        showToast('Settings saved successfully', 'success');
        
        // Update local UI
        const currentLogo = document.getElementById('settings-logo-preview').querySelector('img')?.src?.replace('http://localhost:8080', '');
        updateBrandingUI(payload.brand_name, currentLogo);
        
        // Clear secret field for security
        document.getElementById('set-rzp-secret').value = '';
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 Save All Settings';
    }
}

// Helper to update branding globally without reload
function updateBrandingUI(name, logoUrl) {
    if (name) {
        const nameEls = document.querySelectorAll('#sidebar-brand-name, .pub-logo');
        nameEls.forEach(el => {
            if (el.tagName === 'A') el.innerHTML = `${logoUrl?'':'🌶️ '} ${name}`;
            else el.textContent = name;
        });
        document.title = document.title.replace(/SpicesMart/g, name);
    }
    if (logoUrl) {
        const iconEls = document.querySelectorAll('#sidebar-logo-icon, .logo-icon');
        iconEls.forEach(el => {
            el.innerHTML = `<img src="http://localhost:8080${logoUrl}" style="width:100%;height:100%;object-fit:contain"/>`;
            el.style.background = 'transparent';
        });
    }
}

window.addEventListener('DOMContentLoaded', initSettings);
