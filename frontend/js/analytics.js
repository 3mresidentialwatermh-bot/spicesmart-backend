/* analytics.js — business analytics using Chart.js */

async function initAnalytics() {
    const user = requireAuth();
    if (!user) return;

    renderUserInfo();
    buildSidebar(user.role, 'analytics');
    initSidebarToggle();

    const app = document.getElementById('app');
    app.style.opacity = '1';

    try {
        const data = await api.getAnalyticsData();
        renderAnalyticsStats(data);
        initCharts(data);
    } catch (err) {
        console.error("Failed to load analytics:", err);
    } finally {
        document.getElementById('page-loader').style.display = 'none';
    }
}

function renderAnalyticsStats(data) {
    const row = document.getElementById('analytics-stats');
    row.innerHTML = `
        <div class="stat-card" style="flex:1">
          <div class="stat-icon gold">📦</div>
          <div class="stat-info">
            <div class="stat-value">${data.total_orders || 0}</div>
            <div class="stat-label">Total Orders</div>
          </div>
        </div>
        <div class="stat-card" style="flex:1">
          <div class="stat-icon green">₹</div>
          <div class="stat-info">
            <div class="stat-value">${formatCurrency(data.total_revenue || 0)}</div>
            <div class="stat-label">Total Revenue</div>
          </div>
        </div>
        <div class="stat-card" style="flex:1">
          <div class="stat-icon" style="color: #f56565;">!</div>
          <div class="stat-info">
            <div class="stat-value" style="color: #f56565;">${formatCurrency(data.missed_sales || 0)}</div>
            <div class="stat-label">Missed Opportunities</div>
          </div>
        </div>
    `;
}

function initCharts(data) {
    Chart.defaults.color = '#a0aec0';
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Revenue Chart (Line)
    const revCtx = document.getElementById('revenueChart').getContext('2d');
    const dates = Object.keys(data.revenue_by_date || {});
    const revenues = Object.values(data.revenue_by_date || {});

    new Chart(revCtx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Revenue (₹)',
                data: revenues,
                borderColor: '#eab308',
                backgroundColor: 'rgba(234, 179, 8, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#eab308'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            }
        }
    });

    // 2. Top Products Chart (Doughnut)
    const prodCtx = document.getElementById('productsChart').getContext('2d');
    const prods = data.top_products || [];
    new Chart(prodCtx, {
        type: 'doughnut',
        data: {
            labels: prods.map(p => p.name),
            datasets: [{
                data: prods.map(p => p.quantity),
                backgroundColor: ['#f87171', '#fb923c', '#fbbf24', '#34d399', '#60a5fa'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12 } }
            },
            cutout: '70%'
        }
    });

    // 3. Sales by Role (Pie)
    const rolesCtx = document.getElementById('rolesChart').getContext('2d');
    const roles = Object.keys(data.sales_by_role || {});
    const roleRevs = Object.values(data.sales_by_role || {});
    new Chart(rolesCtx, {
        type: 'pie',
        data: {
            labels: roles.map(r => r.charAt(0).toUpperCase() + r.slice(1)),
            datasets: [{
                data: roleRevs,
                backgroundColor: ['#a78bfa', '#f472b6', '#38bdf8'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { boxWidth: 12 } } }
        }
    });
}
