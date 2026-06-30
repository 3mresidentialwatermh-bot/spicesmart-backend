document.addEventListener('DOMContentLoaded', () => {
    initApp();
    loadCoupons();
});

async function loadCoupons() {
    const container = document.getElementById('coupons-table-body');
    try {
        const data = await apiRequest('GET', '/coupons/');
        renderCoupons(data.coupons);
    } catch (e) {
        container.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
    }
}

function renderCoupons(coupons) {
    const container = document.getElementById('coupons-table-body');
    if (!coupons || coupons.length === 0) {
        container.innerHTML = `<div class="empty-state">No coupons found. Create one!</div>`;
        return;
    }
    
    let html = `<table class="data-table">
        <thead>
            <tr>
                <th>Code</th>
                <th>Discount</th>
                <th>Created At</th>
                <th style="text-align:right">Actions</th>
            </tr>
        </thead>
        <tbody>`;
        
    coupons.forEach(c => {
        const d = new Date(c.created_at).toLocaleDateString();
        html += `
            <tr>
                <td><strong style="color:var(--primary-color)">${c.code}</strong></td>
                <td>${c.discount_percent}% Off</td>
                <td class="text-muted text-sm">${d}</td>
                <td style="text-align:right">
                    <button class="btn btn-ghost btn-sm text-danger" onclick="deleteCoupon(${c.id})">Delete</button>
                </td>
            </tr>
        `;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
}

function openCouponModal() {
    document.getElementById('coupon-form').reset();
    document.getElementById('coupon-modal').classList.add('open');
}

function closeCouponModal() {
    document.getElementById('coupon-modal').classList.remove('open');
}

document.getElementById('coupon-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('c-save-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    const payload = {
        code: document.getElementById('c-code').value.trim().toUpperCase(),
        discount_percent: parseFloat(document.getElementById('c-discount').value)
    };
    
    try {
        await apiRequest('POST', '/coupons/', payload);
        closeCouponModal();
        loadCoupons();
    } catch (e) {
        alert(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Coupon';
    }
});

async function deleteCoupon(id) {
    if (!confirm('Are you sure you want to delete this coupon?')) return;
    
    try {
        await apiRequest('DELETE', `/coupons/${id}`);
        loadCoupons();
    } catch (e) {
        alert(e.message);
    }
}
