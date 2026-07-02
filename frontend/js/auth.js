/* ─── Toast notification system ────────────────────────────── */
function showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span style="font-size:1rem">${icons[type]||'•'}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/* ─── Auth guard — redirect if not logged in ────────────────── */
function requireAuth(allowedRoles = []) {
    const token = getToken();
    const user  = getUser();
    if (!token || !user) {
        window.location.href = '/index.html';
        return null;
    }
    if (allowedRoles.length && !allowedRoles.includes(user.role)) {
        window.location.href = '/dashboard.html';
        return null;
    }
    return user;
}

/* ─── Redirect if already logged in ─────────────────────────── */
function redirectIfLoggedIn(dest = '/dashboard.html') {
    if (getToken() && getUser()) {
        window.location.href = dest;
    }
}

/* ─── Logout ─────────────────────────────────────────────────── */
function logout() {
    removeToken();
    window.location.href = '/index.html';
}

/* ─── Render sidebar user info ───────────────────────────────── */
function renderUserInfo() {
    const user = getUser();
    if (!user) return;

    const nameEl = document.getElementById('sidebar-user-name');
    const roleEl = document.getElementById('sidebar-user-role');
    const avatarEl = document.getElementById('sidebar-user-avatar');

    if (nameEl) nameEl.textContent = user.name;
    if (roleEl) roleEl.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
}

/* ─── Role badge color ───────────────────────────────────────── */
function roleBadge(role) {
    const map = {
        admin: 'badge-purple',
        distributor: 'badge-blue',
        retailer: 'badge-green',
        customer: 'badge-gold',
    };
    return `<span class="badge ${map[role]||'badge-gray'}">${role}</span>`;
}

/* ─── Status badge ───────────────────────────────────────────── */
function statusBadge(status) {
    const map = {
        pending:   'badge-yellow',
        confirmed: 'badge-blue',
        shipped:   'badge-purple',
        delivered: 'badge-green',
        cancelled: 'badge-red',
        paid:      'badge-green',
        failed:    'badge-red',
    };
    return `<span class="badge ${map[status]||'badge-gray'}">${status}</span>`;
}

/* ─── Format currency ────────────────────────────────────────── */
function formatCurrency(amount) {
    return '₹' + Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 });
}

/* ─── Format date ────────────────────────────────────────────── */
function formatDate(iso) {
    return new Date(iso).toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric'
    });
}

/* ─── Product emoji by category ─────────────────────────────── */
function productEmoji(category) {
    const map = {
        'Powders':      '🌶️',
        'Whole Spices': '🌿',
        'Blends':       '🫙',
        'Premium':      '✨',
    };
    return map[category] || '🌶️';
}

/* ─── Hamburger sidebar toggle ───────────────────────────────── */
function initSidebarToggle() {
    const hamburger = document.getElementById('hamburger-btn');
    const sidebar   = document.getElementById('sidebar');
    if (!hamburger || !sidebar) return;

    hamburger.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
}

/* ─── Active nav item ────────────────────────────────────────── */
function setActiveNav(page) {
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });
}

/* ─── Navigation links per role ──────────────────────────────── */
const NAV_LINKS = {
    admin: [
        { label: 'Dashboard',  page: 'dashboard', href: '/dashboard.html',          icon: '📊' },
        { label: 'Analytics',  page: 'analytics', href: '/admin/analytics.html',    icon: '📈' },
        { label: 'Shop',       page: 'shop',       href: '/shop.html',               icon: '🛒' },
        { label: 'Orders',     page: 'orders',     href: '/orders.html',             icon: '📦' },
        { sep: 'Admin Panel' },
        { label: 'Products',   page: 'products',   href: '/admin/products.html',     icon: '🌶️' },
        { label: 'Pricing',    page: 'pricing',    href: '/admin/pricing.html',      icon: '💰' },
        { label: 'Coupons',    page: 'coupons',    href: '/admin/coupons.html',      icon: '🏷️' },
        { label: 'Users',      page: 'users',      href: '/admin/users.html',        icon: '👥' },
        { label: 'Inventory',  page: 'inventory',  href: '/admin/inventory.html',    icon: '📋' },
        { label: 'Settings',   page: 'settings',   href: '/admin/settings.html',     icon: '⚙️' },
        { sep: 'Account' },
        { label: 'My Profile', page: 'profile',    href: '/profile.html',            icon: '👤' },
    ],
    distributor: [
        { label: 'Dashboard',     page: 'dashboard', href: '/dashboard.html',          icon: '📊' },
        { label: 'Analytics',     page: 'analytics', href: '/admin/analytics.html',    icon: '📈' },
        { label: 'Shop',          page: 'shop',       href: '/shop.html',               icon: '🛒' },
        { label: 'My Orders',     page: 'orders',     href: '/orders.html',             icon: '📦' },
        { label: 'My Inventory',  page: 'inventory',  href: '/admin/inventory.html',    icon: '📋' },
        { label: 'My Retailers',  page: 'users',      href: '/admin/users.html',        icon: '👥' },
        { sep: 'Account' },
        { label: 'My Profile',    page: 'profile',    href: '/profile.html',            icon: '👤' },
    ],
    retailer: [
        { label: 'Dashboard',     page: 'dashboard', href: '/dashboard.html',          icon: '📊' },
        { label: 'Analytics',     page: 'analytics', href: '/admin/analytics.html',    icon: '📈' },
        { label: 'Shop',          page: 'shop',       href: '/shop.html',               icon: '🛒' },
        { label: 'My Orders',     page: 'orders',     href: '/orders.html',             icon: '📦' },
        { label: 'My Inventory',  page: 'inventory',  href: '/admin/inventory.html',    icon: '📋' },
        { sep: 'Account' },
        { label: 'My Profile',    page: 'profile',    href: '/profile.html',            icon: '👤' },
    ],
    customer: [
        { label: 'Shop',       page: 'shop',    href: '/shop.html',    icon: '🛒' },
        { label: 'My Orders',  page: 'orders',  href: '/orders.html',  icon: '📦' },
        { sep: 'Account' },
        { label: 'My Profile', page: 'profile', href: '/profile.html', icon: '👤' },
    ],
};


/* ─── Build sidebar navigation ───────────────────────────────── */
function buildSidebar(role, activePage) {
    const nav = document.getElementById('sidebar-nav');
    if (!nav) return;
    const links = NAV_LINKS[role] || NAV_LINKS.customer;
    nav.innerHTML = links.map(l => {
        if (l.sep) return `<div class="nav-section-title">${l.sep}</div>`;
        return `<a href="${l.href}" class="nav-item ${l.page === activePage ? 'active' : ''}" data-page="${l.page}">
            <span class="nav-icon">${l.icon}</span>
            <span>${l.label}</span>
        </a>`;
    }).join('');

    // Add Dark Mode Toggle
    nav.innerHTML += `<div class="nav-section-title">Theme</div>
        <a href="#" class="nav-item" onclick="toggleTheme(); return false;">
            <span class="nav-icon">🌙</span>
            <span>Toggle Dark Mode</span>
        </a>`;
}

/* ─── Theme Toggle ───────────────────────────────────────────── */
function initTheme() {
    if (localStorage.getItem('theme') === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}
function toggleTheme() {
    if (document.documentElement.getAttribute('data-theme') === 'dark') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
}
initTheme();

window.showToast = showToast;
window.requireAuth = requireAuth;
window.redirectIfLoggedIn = redirectIfLoggedIn;
window.logout = logout;
window.renderUserInfo = renderUserInfo;
window.roleBadge = roleBadge;
window.statusBadge = statusBadge;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.productEmoji = productEmoji;
window.initSidebarToggle = initSidebarToggle;
window.setActiveNav = setActiveNav;
window.buildSidebar = buildSidebar;
window.toggleTheme = toggleTheme;
window.NAV_LINKS = NAV_LINKS;
