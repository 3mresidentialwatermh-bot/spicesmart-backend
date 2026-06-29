/* orders.js — order listing, status management */

let currentMode = 'placed';
let allOrders = [];
let currentUser = null;

const STATUS_STEPS = ['confirmed', 'shipped', 'delivered'];

async function initOrders() {
    currentUser = requireAuth();
    if (!currentUser) return;

    renderUserInfo();
    buildSidebar(currentUser.role, 'orders');
    initSidebarToggle();

    // Hide received tab for customers
    if (currentUser.role === 'customer') {
        const tab = document.getElementById('received-tab');
        if (tab) tab.classList.add('hidden');
    }

    await loadOrders();
}

async function loadOrders() {
    const data = await api.getOrders(currentMode).catch(() => ({ orders: [] }));
    allOrders = data.orders || [];
    renderOrdersTable();
}

function switchTab(btn, mode) {
    currentMode = mode;
    document.querySelectorAll('[data-mode]').forEach(b => {
        b.className = b.dataset.mode === mode ? 'btn btn-primary btn-sm' : 'btn btn-ghost btn-sm';
    });
    document.getElementById('orders-title').textContent = mode === 'placed' ? 'My Orders' : 'Incoming Orders';
    loadOrders();
}

function renderOrdersTable() {
    const body = document.getElementById('orders-body');
    const count = document.getElementById('orders-count');
    count.textContent = `${allOrders.length} order(s)`;

    if (!allOrders.length) {
        body.innerHTML = `<div class="empty-state"><div class="empty-icon">📦</div><p>No orders found</p></div>`;
        return;
    }

    const canUpdateStatus = (order) =>
        currentMode === 'received' || currentUser.role === 'admin';

    body.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Order</th>
              <th>${currentMode === 'received' ? 'From (Buyer)' : 'To (Seller)'}</th>
              <th>Items</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Payment</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${allOrders.map(o => `
              <tr>
                <td><strong>#${o.id}</strong></td>
                <td>
                  ${currentMode === 'received'
                    ? `<div>${o.buyer_name}</div><div class="td-muted text-sm">${o.buyer_role}</div>`
                    : `<div>${o.seller_name}</div><div class="td-muted text-sm">${o.seller_role}</div>`}
                </td>
                <td class="td-muted">${o.items.length} item(s)</td>
                <td><strong>${formatCurrency(o.total_amount)}</strong></td>
                <td>${statusBadge(o.status)}</td>
                <td>${statusBadge(o.payment_status)}</td>
                <td class="td-muted">${formatDate(o.created_at)}</td>
                <td style="display:flex;gap:6px">
                  <button class="btn btn-ghost btn-sm" onclick="viewOrder(${o.id})">👁 View</button>
                  <button class="btn btn-outline btn-sm" onclick="window.open('${API_BASE}/orders/${o.id}/invoice?token=' + getToken(), '_blank')">📄 Invoice</button>
                  ${canUpdateStatus(o) && o.status !== 'delivered' && o.status !== 'cancelled'
                    ? `<button class="btn btn-outline btn-sm" onclick="openStatusUpdate(${o.id},'${o.status}')">✏️</button>`
                    : ''}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
    `;
}

function viewOrder(orderId) {
    const order = allOrders.find(o => o.id === orderId);
    if (!order) return;

    document.getElementById('order-modal-title').textContent = `Order #${order.id}`;

    const steps = ['confirmed', 'shipped', 'delivered'];
    const currentIdx = steps.indexOf(order.status);

    const timeline = steps.map((step, i) => {
        const done = i < currentIdx || order.status === 'delivered';
        const current = i === currentIdx;
        return `
            <div class="timeline-step ${done ? 'done' : ''} ${current && order.status !== 'delivered' ? 'current' : ''}">
              <div class="timeline-dot">${done || (current && order.status === 'delivered') ? '✓' : i+1}</div>
              <div class="timeline-label">${step.charAt(0).toUpperCase()+step.slice(1)}</div>
            </div>
        `;
    }).join('');

    document.getElementById('order-modal-body').innerHTML = `
        <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap">
          <div class="card-dark" style="flex:1;min-width:140px">
            <div class="text-muted text-sm">Buyer</div>
            <div style="font-weight:700">${order.buyer_name}</div>
            <div class="text-muted text-sm">${order.buyer_role}</div>
          </div>
          <div class="card-dark" style="flex:1;min-width:140px">
            <div class="text-muted text-sm">Seller</div>
            <div style="font-weight:700">${order.seller_name}</div>
            <div class="text-muted text-sm">${order.seller_role}</div>
          </div>
          <div class="card-dark" style="flex:1;min-width:140px">
            <div class="text-muted text-sm">Total</div>
            <div style="font-weight:800;font-size:1.2rem;color:var(--saffron)">${formatCurrency(order.total_amount)}</div>
          </div>
        </div>
        
        ${order.coupon_code ? `<div style="margin-top:8px;padding:8px;background:rgba(0,150,0,0.1);border-radius:6px;color:#2e7d32">
          <strong>🏷️ Coupon Applied:</strong> ${order.coupon_code} (-${formatCurrency(order.discount_amount)})
        </div>` : ''}

        <div class="order-timeline">${timeline}</div>
        
        ${order.tracking_number ? `<div style="margin-top:16px;padding:12px;background:var(--surface-2);border-radius:6px;">
          <div class="text-sm text-muted">🚚 Shipping Details</div>
          <div><strong>Courier:</strong> ${order.courier || 'N/A'}</div>
          <div><strong>Tracking Number:</strong> ${order.tracking_number}</div>
        </div>` : ''}

        <div class="divider"></div>

        <div class="table-title" style="margin-bottom:10px">Order Items</div>
        <table style="width:100%">
          <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
          <tbody>
            ${order.items.map(i => `
              <tr>
                <td>${i.product_name} <span class="td-muted">(${i.product_unit||''})</span></td>
                <td>${i.quantity}</td>
                <td>${formatCurrency(i.unit_price)}</td>
                <td><strong>${formatCurrency(i.subtotal)}</strong></td>
              </tr>
            `).join('')}
          </tbody>
        </table>

        ${(currentMode === 'received' || currentUser.role === 'admin') && order.status !== 'delivered' && order.status !== 'cancelled'
          ? `<div class="divider"></div>
             <div style="display:flex;gap:8px;align-items:center">
               <label class="form-label" style="margin:0">Update Status:</label>
               <select class="form-select" id="status-select-${order.id}" style="flex:1">
                 <option value="pending" ${order.status==='pending'?'selected':''}>Pending</option>
                 <option value="confirmed" ${order.status==='confirmed'?'selected':''}>Confirmed</option>
                 <option value="shipped" ${order.status==='shipped'?'selected':''}>Shipped</option>
                 <option value="delivered" ${order.status==='delivered'?'selected':''}>Delivered</option>
                 <option value="cancelled">Cancelled</option>
               </select>
               <button class="btn btn-primary btn-sm" onclick="saveStatus(${order.id})">Save</button>
             </div>`
          : ''}
    `;

    document.getElementById('order-detail-modal').classList.add('open');
}

async function saveStatus(orderId) {
    const sel = document.getElementById(`status-select-${orderId}`);
    if (!sel) return;
    
    let payload = { status: sel.value };
    
    if (sel.value === 'shipped') {
        const tracking = prompt("Enter tracking number (optional):");
        if (tracking !== null) {
            payload.tracking_number = tracking;
            payload.courier = prompt("Enter courier name (optional):") || "";
        } else {
            return; // Cancelled
        }
    }

    try {
        await apiRequest('PUT', `/orders/${orderId}/status`, payload);
        showToast('Order status updated', 'success');
        closeOrderModal();
        loadOrders();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function closeOrderModal() {
    document.getElementById('order-detail-modal').classList.remove('open');
}

initOrders();
