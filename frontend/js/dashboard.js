/* dashboard.js — role-aware dashboard logic */
/* Note: buildSidebar and NAV_LINKS are defined in auth.js */


async function initDashboard() {
    const user = requireAuth();
    if (!user) return;

    renderUserInfo();
    buildSidebar(user.role, 'dashboard');
    initSidebarToggle();

    document.getElementById('page-loader').style.display = 'none';
    const app = document.getElementById('app');
    app.style.opacity = '1';

    const [stats, invSummary] = await Promise.all([
        api.getOrderStats().catch(() => ({})),
        api.getInventorySummary().catch(() => ({})),
    ]);

    renderStats(user, stats, invSummary);
    renderDashboardBody(user, stats);
}

function renderStats(user, stats, inv) {
    const grid = document.getElementById('stats-grid');
    grid.innerHTML = `
        <div class="stat-card">
          <div class="stat-icon gold">📦</div>
          <div class="stat-info">
            <div class="stat-value">${stats.total_orders ?? 0}</div>
            <div class="stat-label">Total Orders</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green">₹</div>
          <div class="stat-info">
            <div class="stat-value">${formatCurrency(stats.total_revenue ?? 0)}</div>
            <div class="stat-label">${user.role === 'admin' ? 'Total Revenue' : 'Total Spent'}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon blue">🚚</div>
          <div class="stat-info">
            <div class="stat-value">${stats.shipped ?? 0}</div>
            <div class="stat-label">Shipped</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon red">⚠️</div>
          <div class="stat-info">
            <div class="stat-value">${inv.low_stock_count ?? 0}</div>
            <div class="stat-label">Low Stock Alerts</div>
          </div>
        </div>
        ${user.role === 'admin' ? `
        <div class="stat-card">
          <div class="stat-icon purple">✅</div>
          <div class="stat-info">
            <div class="stat-value">${stats.delivered ?? 0}</div>
            <div class="stat-label">Delivered</div>
          </div>
        </div>` : ''}
    `;
}

async function renderDashboardBody(user) {
    const body = document.getElementById('dashboard-body');
    body.style.gridTemplateColumns = '1fr 1fr';

    // Recent orders
    const recentData = await api.getOrders('placed').catch(() => ({ orders: [] }));
    const recent5 = (recentData.orders || []).slice(0, 5);

    // Incoming orders (for distributors/retailers)
    const incomingData = (user.role !== 'customer')
        ? await api.getOrders('received').catch(() => ({ orders: [] }))
        : { orders: [] };
    const incoming5 = (incomingData.orders || []).slice(0, 5);

    const orderRows = (orders) => orders.length ? orders.map(o => `
        <tr>
          <td><strong>#${o.id}</strong></td>
          <td>${statusBadge(o.status)}</td>
          <td>${formatCurrency(o.total_amount)}</td>
          <td class="td-muted">${formatDate(o.created_at)}</td>
        </tr>
    `).join('') : `<tr><td colspan="4"><div class="empty-state" style="padding:30px"><div class="empty-icon">📦</div><p>No orders yet</p></div></td></tr>`;

    body.innerHTML = `
        <div class="table-container">
          <div class="table-header">
            <span class="table-title">📤 My Recent Orders</span>
            <a href="/orders.html" class="btn btn-ghost btn-sm">View All</a>
          </div>
          <table>
            <thead><tr><th>Order</th><th>Status</th><th>Amount</th><th>Date</th></tr></thead>
            <tbody>${orderRows(recent5)}</tbody>
          </table>
        </div>
        ${user.role !== 'customer' ? `
        <div class="table-container">
          <div class="table-header">
            <span class="table-title">📥 Incoming Orders</span>
            <a href="/orders.html" class="btn btn-ghost btn-sm">View All</a>
          </div>
          <table>
            <thead><tr><th>Order</th><th>Status</th><th>Amount</th><th>Date</th></tr></thead>
            <tbody>${orderRows(incoming5)}</tbody>
          </table>
        </div>` : `
        <div class="card-dark" style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border-radius:14px">
          <div style="font-size:3rem">🛒</div>
          <p style="font-size:0.95rem;color:var(--text-secondary)">Ready to order?</p>
          <a href="/shop.html" class="btn btn-primary">Browse Products</a>
        </div>`}
    `;
}

// Only auto-init on the dashboard page (which has #page-loader)
if (document.getElementById('page-loader')) {
    initDashboard();
}

