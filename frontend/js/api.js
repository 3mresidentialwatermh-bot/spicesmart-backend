/* ─── API base URL ─────────────────────────────────────────── */
const API_BASE = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
    ? 'http://127.0.0.1:5000/api' 
    : 'https://spicesmart-api.onrender.com/api';

/* ─── Auth helpers ─────────────────────────────────────────── */
function getToken()      { return localStorage.getItem('sm_token'); }
function setToken(t)     { localStorage.setItem('sm_token', t); }
function removeToken()   { localStorage.removeItem('sm_token'); localStorage.removeItem('sm_user'); }
function getUser()       { try { return JSON.parse(localStorage.getItem('sm_user')); } catch { return null; } }
function setUser(u)      { localStorage.setItem('sm_user', JSON.stringify(u)); }

/* ─── Core fetch wrapper ───────────────────────────────────── */
async function apiRequest(method, path, body = null, auth = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
        const token = getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(API_BASE + path, opts);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
        throw { status: res.status, message: data.error || 'Request failed' };
    }
    return data;
}

/* ─── File upload wrapper (multipart/form-data) ────────────── */
async function apiUpload(path, formData) {
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers,
        body: formData,   // no Content-Type — browser sets boundary automatically
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, message: data.error || 'Upload failed' };
    return data;
}

/* ─── Convenience methods ──────────────────────────────────── */
const api = {
    get:    (path)        => apiRequest('GET',    path),
    post:   (path, body)  => apiRequest('POST',   path, body),
    put:    (path, body)  => apiRequest('PUT',    path, body),
    delete: (path)        => apiRequest('DELETE', path),

    /* Auth */
    login:    (email, password) => apiRequest('POST', '/auth/login',    { email, password }, false),
    register: (data)            => apiRequest('POST', '/auth/register',  data,               false),
    me:       ()                => apiRequest('GET',  '/auth/me'),
    updateProfile: (data)       => apiRequest('PUT',  '/auth/profile', data),
    changePassword:(data)       => apiRequest('POST', '/auth/change-password', data),



    /* Products */
    getPublicProducts: (params) => apiRequest('GET', '/products/public' + (params ? '?' + new URLSearchParams(params) : ''), null, false),
    getProducts: (params) => apiRequest('GET', '/products/' + (params ? '?' + new URLSearchParams(params) : '')),
    getCategories: () => apiRequest('GET', '/products/categories'),
    createProduct: (data) => apiRequest('POST', '/products/', data),
    updateProduct: (id, data) => apiRequest('PUT', `/products/${id}`, data),
    deleteProduct: (id) => apiRequest('DELETE', `/products/${id}`),
    uploadProductImage: async (file) => {
        const formData = new FormData(); formData.append('file', file);
        return apiUpload('/products/upload-image', formData);
    },
    bulkImportProducts: async (file) => {
        const formData = new FormData(); formData.append('file', file);
        return apiUpload('/products/bulk-import', formData);
    },
    bulkUploadImages: async (files) => {
        const formData = new FormData();
        Array.from(files).forEach(f => formData.append('images', f));
        return apiUpload('/products/bulk-upload-images', formData);
    },

    // Pricing & Inventory
    getPricing: () => apiRequest('GET', '/pricing/'),
    updatePricing: (data) => apiRequest('PUT', '/pricing/', data),
    getInventory: () => apiRequest('GET', '/inventory/'),
    updateInventory: (data) => apiRequest('PUT', '/inventory/', data),

    // Orders & Payments
    getOrders: () => apiRequest('GET', '/orders/'),
    createOrder: (data) => apiRequest('POST', '/orders/', data),
    updateOrderStatus: (id, status) => apiRequest('PUT', `/orders/${id}/status`, { status }),
    getPaymentKey: () => apiRequest('GET', '/payments/key', null, false),
    createPaymentOrder: (data) => apiRequest('POST', '/payments/create-order', data),
    verifyPayment: (data) => apiRequest('POST', '/payments/verify', data),

    // Settings
    getSettings: () => apiRequest('GET', '/settings/'),
    updateSettings: (data) => apiRequest('PUT', '/settings/', data),
    uploadSettingsLogo: async (file) => {
        const formData = new FormData(); formData.append('file', file);
        return apiUpload('/settings/upload-logo', formData);
    },

    downloadProductTemplate: () => `${API_BASE}/products/sample-csv?token=${getToken()}`,

    bulkImportPricing: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return apiUpload('/pricing/bulk-import', fd);
    },

    /* Analytics */
    getAnalyticsData: ()               => apiRequest('GET', '/analytics/dashboard'),

    /* Orders */
    placeOrder:       (data)           => apiRequest('POST', '/orders/', data),
    getOrders:        (mode = 'placed') => apiRequest('GET', `/orders/?mode=${mode}`),
    updateOrderStatus:(id, status)     => apiRequest('PUT',  `/orders/${id}/status`, { status }),
    getOrderStats:    ()               => apiRequest('GET', '/orders/stats'),

    /* Payments */
    getPaymentKey:    ()               => apiRequest('GET', '/payments/key', null, false),
    createRazorpayOrder: (amount, orderId) => apiRequest('POST', '/payments/create-order', { amount, order_id: orderId }),
    verifyPayment:    (data)           => apiRequest('POST', '/payments/verify', data),

    /* Inventory */
    getAlerts:        ()               => apiRequest('GET', '/inventory/alerts'),
    adjustStock:      (data)           => apiRequest('POST', '/inventory/adjust', data),
    setStock:         (data)           => apiRequest('POST', '/inventory/set', data),
    getInventorySummary: ()            => apiRequest('GET', '/inventory/summary'),

    /* Users */
    getUsers:         ()               => apiRequest('GET', '/users/'),
    createUser:       (data)           => apiRequest('POST', '/users/', data),
    updateUser:       (id, data)       => apiRequest('PUT',  `/users/${id}`, data),
    deleteUser:       (id)             => apiRequest('DELETE', `/users/${id}`),
    getHierarchy:     ()               => apiRequest('GET', '/users/hierarchy'),
    getDistributors:  ()               => apiRequest('GET', '/users/distributors'),
};

window.api = api;
window.apiUpload = apiUpload;
window.getUser = getUser;
window.setToken = setToken;
window.setUser = setUser;
window.removeToken = removeToken;

// Global Branding Auto-fetch
(async function applyGlobalBranding() {
    try {
        const s = await api.getSettings();
        if (s.brand_name) {
            document.title = document.title.replace('SpicesMart', s.brand_name);
            document.querySelectorAll('#sidebar-brand-name').forEach(el => el.textContent = s.brand_name);
            document.querySelectorAll('.pub-logo').forEach(el => {
                if (!el.querySelector('img')) {
                    el.innerHTML = `${s.brand_logo_url ? '' : '🌶️ '} ${s.brand_name}`;
                }
            });
        }
        if (s.brand_logo_url) {
            const logoHtml = `<img src="http://localhost:8080${s.brand_logo_url}" style="width:100%;height:100%;object-fit:contain"/>`;
            document.querySelectorAll('#sidebar-logo-icon, .logo-icon').forEach(el => {
                el.innerHTML = logoHtml;
                el.style.background = 'transparent';
            });
            document.querySelectorAll('.pub-logo').forEach(el => {
                if (!el.innerHTML.includes('<img')) {
                    el.innerHTML = logoHtml + ` <span>${s.brand_name}</span>`;
                }
            });
        }
    } catch (e) {
        // Ignore errors if settings not configured yet
    }
})();
