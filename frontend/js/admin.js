/* admin.js — shared admin page logic (products, pricing, users, inventory) */

let currentUser = null;
let allProductsAdmin = [];
let allUsersAdmin = [];
let currentUserRoleFilter = '';

function initAdminBase(page) {
    currentUser = requireAuth(['admin', 'distributor', 'retailer']);
    if (!currentUser) return false;
    renderUserInfo();
    buildSidebar(currentUser.role, page);
    initSidebarToggle();
    return true;
}

/* ══════════════════════════════════════════════════
   PRODUCTS ADMIN
══════════════════════════════════════════════════ */
async function initAdminProducts() {
    if (!initAdminBase('products')) return;
    await loadAdminProducts();
}

async function loadAdminProducts() {
    const data = await api.getProducts().catch(() => ({ products: [] }));
    allProductsAdmin = data.products || [];
    renderProductsTable(allProductsAdmin);
}

function filterProducts(query) {
    const q = query.toLowerCase();
    const filtered = allProductsAdmin.filter(p =>
        p.name.toLowerCase().includes(q) || (p.sku||'').toLowerCase().includes(q)
    );
    renderProductsTable(filtered);
}

function renderProductsTable(products) {
    const body = document.getElementById('products-table-body');
    if (!products.length) {
        body.innerHTML = `<div class="empty-state"><div class="empty-icon">🌶️</div><p>No products found</p></div>`;
        return;
    }

    body.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>SKU</th>
              <th>Category</th>
              <th>Unit</th>
              <th>Dist. Price</th>
              <th>Retail Price</th>
              <th>Customer Price</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${products.map(p => `
              <tr>
                <td><strong>${productEmoji(p.category)} ${p.name}</strong></td>
                <td class="td-muted">${p.sku || '—'}</td>
                <td>${p.category || '—'}</td>
                <td>${p.unit || '—'}</td>
                <td>${formatCurrency(p.prices?.distributor || 0)}</td>
                <td>${formatCurrency(p.prices?.retailer || 0)}</td>
                <td>${formatCurrency(p.prices?.customer || 0)}</td>
                <td>${p.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-red">Inactive</span>'}</td>
                <td style="display:flex;gap:6px">
                  <button class="btn btn-ghost btn-sm" onclick="openProductModal(${p.id})">✏️</button>
                  <button class="btn btn-danger btn-sm" onclick="toggleProduct(${p.id},${!p.is_active})">${p.is_active ? '🚫' : '✅'}</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
    `;
}

function openProductModal(productId = null) {
    const modal = document.getElementById('product-modal');
    document.getElementById('product-modal-title').textContent = productId ? 'Edit Product' : 'Add Product';
    document.getElementById('product-id').value = productId || '';

    if (productId) {
        const p = allProductsAdmin.find(x => x.id === productId);
        if (!p) return;
        document.getElementById('p-name').value = p.name;
        document.getElementById('p-sku').value  = p.sku || '';
        document.getElementById('p-unit').value = p.unit || '';
        document.getElementById('p-category').value  = p.category || 'Powders';
        document.getElementById('p-desc').value  = p.description || '';
        document.getElementById('p-price-distributor').value = p.prices?.distributor || '';
        document.getElementById('p-price-retailer').value    = p.prices?.retailer || '';
        document.getElementById('p-price-customer').value    = p.prices?.customer || '';
        document.getElementById('p-stock').value = '';
        // Restore image
        const imgUrl = document.getElementById('p-image-url');
        const preview = document.getElementById('image-preview');
        if (imgUrl && preview) {
            imgUrl.value = p.image_url || '';
            if (p.image_url) {
                preview.innerHTML = `<img src="${p.image_url}" style="width:100%;height:100%;object-fit:cover"/>`;
            } else {
                preview.innerHTML = productEmoji(p.category);
            }
        }
    } else {
        document.getElementById('product-form').reset();
        const preview = document.getElementById('image-preview');
        if (preview) preview.innerHTML = '🌶️';
    }

    modal.classList.add('open');
}

function closeProductModal() {
    document.getElementById('product-modal').classList.remove('open');
}

/* ── Image upload handler ──────────────────────────────────── */
async function handleImageUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById('image-upload-status');
    const preview  = document.getElementById('image-preview');
    statusEl.textContent = 'Uploading...';
    statusEl.style.color = 'var(--text-muted)';

    try {
        const result = await api.uploadProductImage(file);
        document.getElementById('p-image-url').value = result.url;
        preview.innerHTML = `<img src="${result.url}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='🌶️'"/>`;
        statusEl.textContent = 'Image uploaded!';
        statusEl.style.color = 'var(--success)';
    } catch (err) {
        statusEl.textContent = 'Upload failed: ' + err.message;
        statusEl.style.color = 'var(--danger)';
    }
}

/* ── Bulk import modal ─────────────────────────────────────── */
function openBulkImportModal() {
    const modal = document.getElementById('bulk-import-modal');
    if (modal) modal.classList.add('open');
}
function closeBulkImportModal() {
    const modal = document.getElementById('bulk-import-modal');
    if (modal) modal.classList.remove('open');
    const result = document.getElementById('bulk-import-result');
    if (result) result.style.display = 'none';
}

async function runBulkImport() {
    const fileInput = document.getElementById('bulk-import-file');
    const file = fileInput?.files[0];
    if (!file) { showToast('Please select a CSV file', 'warning'); return; }

    const btn = document.getElementById('bulk-import-btn');
    btn.disabled = true; btn.textContent = 'Importing...';

    try {
        const result = await api.bulkImportProducts(file);
        const resultEl = document.getElementById('bulk-import-result');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
            <div style="color:var(--success);font-weight:700;margin-bottom:8px">Import Complete</div>
            <div>Created: <strong>${result.created}</strong> products</div>
            <div>Updated: <strong>${result.updated}</strong> products</div>
            <div>Errors: <strong style="color:${result.errors>0?'var(--danger)':'inherit'}">${result.errors}</strong></div>
            ${result.error_details.length ? `<div style="margin-top:8px;font-size:0.8rem;color:var(--danger)">${result.error_details.map(e=>`Row ${e.row}: ${e.error}`).join('<br/>')}</div>` : ''}
        `;
        if (result.created > 0 || result.updated > 0) {
            showToast(`Imported ${result.created} new, updated ${result.updated}`, 'success');
            await loadAdminProducts();
        }
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false; btn.textContent = '📤 Import Now';
    }
}

/* ── Bulk Image Upload modal ───────────────────────────────── */
function openBulkImageModal() {
    const modal = document.getElementById('bulk-image-modal');
    if (modal) modal.classList.add('open');
}
function closeBulkImageModal() {
    const modal = document.getElementById('bulk-image-modal');
    if (modal) modal.classList.remove('open');
    const result = document.getElementById('bulk-image-result');
    if (result) result.style.display = 'none';
}

async function runBulkImageUpload() {
    const fileInput = document.getElementById('bulk-image-files');
    const files = fileInput?.files;
    if (!files || files.length === 0) { showToast('Please select images', 'warning'); return; }

    const btn = document.getElementById('bulk-image-btn');
    btn.disabled = true; btn.textContent = 'Uploading...';

    try {
        const result = await api.bulkUploadImages(files);
        const resultEl = document.getElementById('bulk-image-result');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
            <div style="color:var(--success);font-weight:700;margin-bottom:8px">Upload Complete</div>
            <div>Matched & Updated: <strong>${result.matched}</strong> products</div>
            ${result.errors && result.errors.length ? `<div style="margin-top:8px;font-size:0.8rem;color:var(--danger)">${result.errors.join('<br/>')}</div>` : ''}
        `;
        if (result.matched > 0) {
            showToast(`Successfully uploaded ${result.matched} images`, 'success');
            await loadAdminProducts();
        }
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false; btn.textContent = '📤 Upload Images';
    }
}

document.getElementById?.('product-form')?.addEventListener?.('submit', saveProduct);
window.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('product-form');
    if (form) form.addEventListener('submit', saveProduct);
});

async function saveProduct(e) {
    e.preventDefault();
    const pid = document.getElementById('product-id').value;
    const btn = document.getElementById('product-save-btn');
    btn.disabled = true;
    btn.textContent = 'Saving…';

    const payload = {
        name:     document.getElementById('p-name').value,
        sku:      document.getElementById('p-sku').value,
        unit:     document.getElementById('p-unit').value,
        category: document.getElementById('p-category').value,
        description: document.getElementById('p-desc').value,
        image_url: document.getElementById('p-image-url')?.value || null,
        prices: {
            distributor: parseFloat(document.getElementById('p-price-distributor').value) || 0,
            retailer:    parseFloat(document.getElementById('p-price-retailer').value) || 0,
            customer:    parseFloat(document.getElementById('p-price-customer').value) || 0,
        }
    };
    
    const stockInput = document.getElementById('p-stock').value;
    if (stockInput !== '') {
        payload.initial_stock = parseInt(stockInput) || 0;
    }

    try {
        if (pid) {
            await api.updateProduct(pid, payload);
            showToast('Product updated', 'success');
        } else {
            await api.createProduct(payload);
            showToast('Product created', 'success');
        }
        closeProductModal();
        await loadAdminProducts();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Product';
    }
}

async function toggleProduct(id, active) {
    await api.updateProduct(id, { is_active: active });
    showToast(`Product ${active ? 'activated' : 'deactivated'}`, 'info');
    await loadAdminProducts();
}


/* ══════════════════════════════════════════════════
   PRICING ADMIN
══════════════════════════════════════════════════ */
async function initAdminPricing() {
    if (!initAdminBase('pricing')) return;
    await loadPricingMatrix();
}

async function loadPricingMatrix() {
    const data = await api.getProducts().catch(() => ({ products: [] }));
    const products = data.products || [];
    renderPricingTable(products);
}

function renderPricingTable(products) {
    const body = document.getElementById('pricing-table-body');
    if (!products.length) {
        body.innerHTML = '<div class="empty-state"><p>No products</p></div>';
        return;
    }

    body.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Unit</th>
              <th>Distributor Price (₹)</th>
              <th>Retailer Price (₹)</th>
              <th>Customer Price (₹)</th>
            </tr>
          </thead>
          <tbody>
            ${products.map(p => `
              <tr>
                <td><strong>${productEmoji(p.category)} ${p.name}</strong></td>
                <td class="td-muted">${p.unit||'—'}</td>
                <td><input type="number" data-pid="${p.id}" data-role="distributor" value="${p.prices?.distributor||0}" min="0" step="0.01"/></td>
                <td><input type="number" data-pid="${p.id}" data-role="retailer"    value="${p.prices?.retailer||0}"    min="0" step="0.01"/></td>
                <td><input type="number" data-pid="${p.id}" data-role="customer"    value="${p.prices?.customer||0}"    min="0" step="0.01"/></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
    `;
}

async function savePricing() {
    const inputs = document.querySelectorAll('.pricing-table input[type="number"]');
    const updates = [];
    inputs.forEach(inp => {
        updates.push({
            product_id: parseInt(inp.dataset.pid),
            role: inp.dataset.role,
            price: parseFloat(inp.value) || 0,
        });
    });

    const btn = document.getElementById('save-pricing-btn');
    btn.disabled = true;
    btn.textContent = 'Saving…';

    try {
        await api.bulkSetPrices(updates);
        showToast('All prices saved!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 Save All Prices';
    }
}

/* ══════════════════════════════════════════════════
   USERS ADMIN
══════════════════════════════════════════════════ */
async function initAdminUsers() {
    if (!initAdminBase('users')) return;
    await loadAdminUsers();
}

async function loadAdminUsers() {
    const data = await api.getUsers().catch(() => ({ users: [] }));
    allUsersAdmin = data.users || [];
    renderUsersTable(allUsersAdmin);
}

function filterUserRole(el, role) {
    currentUserRoleFilter = role;
    document.querySelectorAll('[data-role]').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    const filtered = role ? allUsersAdmin.filter(u => u.role === role) : allUsersAdmin;
    renderUsersTable(filtered);
}

function renderUsersTable(users) {
    const body = document.getElementById('users-table-body');
    const countEl = document.getElementById('users-count');
    countEl.textContent = `${users.length} user(s)`;

    if (!users.length) {
        body.innerHTML = '<div class="empty-state"><p>No users found</p></div>';
        return;
    }

    body.innerHTML = `
        <table>
          <thead>
            <tr><th>Name</th><th>Email</th><th>Role</th><th>Parent</th><th>Phone</th><th>Status</th><th>Actions</th></tr>
          </thead>
          <tbody>
            ${users.map(u => `
              <tr>
                <td><strong>${u.name}</strong></td>
                <td class="td-muted">${u.email}</td>
                <td>${roleBadge(u.role)}</td>
                <td class="td-muted">${u.parent_name || '—'}</td>
                <td class="td-muted">${u.phone || '—'}</td>
                <td>${u.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-red">Inactive</span>'}</td>
                <td style="display:flex;gap:6px">
                  <button class="btn btn-ghost btn-sm" onclick="openUserModal(${u.id})">✏️</button>
                  <button class="btn btn-danger btn-sm" onclick="toggleUser(${u.id},${!u.is_active})">${u.is_active ? '🚫' : '✅'}</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
    `;
}

async function openUserModal(userId = null) {
    const modal = document.getElementById('user-modal');
    document.getElementById('user-modal-title').textContent = userId ? 'Edit User' : 'Add User';
    document.getElementById('user-id').value = userId || '';

    // Load distributors for parent dropdown
    await loadParentOptions();

    if (userId) {
        const u = allUsersAdmin.find(x => x.id === userId);
        if (!u) return;
        document.getElementById('u-name').value = u.name;
        document.getElementById('u-email').value = u.email;
        document.getElementById('u-phone').value = u.phone || '';
        document.getElementById('u-role').value  = u.role;
        document.getElementById('u-address').value = u.address || '';
        document.getElementById('u-parent').value = u.parent_id || '';
        onRoleChange(u.role);
    } else {
        document.getElementById('user-form').reset();
        onRoleChange('distributor');
    }

    modal.classList.add('open');
}

async function loadParentOptions() {
    const data = await api.getDistributors().catch(() => ({ distributors: [] }));
    const sel = document.getElementById('u-parent');
    sel.innerHTML = '<option value="">No Parent (Admin Level)</option>' +
        (data.distributors || []).map(d => `<option value="${d.id}">${d.name}</option>`).join('');
}

function onRoleChange(role) {
    const pg = document.getElementById('parent-group');
    if (pg) pg.style.display = role === 'retailer' || role === 'customer' ? 'block' : 'none';
}

function closeUserModal() {
    document.getElementById('user-modal').classList.remove('open');
}

window.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('user-form');
    if (form) form.addEventListener('submit', saveUser);
});

async function saveUser(e) {
    e.preventDefault();
    const uid = document.getElementById('user-id').value;
    const btn = document.getElementById('user-save-btn');
    btn.disabled = true;
    btn.textContent = 'Saving…';

    const payload = {
        name:     document.getElementById('u-name').value,
        email:    document.getElementById('u-email').value,
        phone:    document.getElementById('u-phone').value,
        role:     document.getElementById('u-role').value,
        parent_id: document.getElementById('u-parent').value || null,
        address:  document.getElementById('u-address').value,
    };
    const pwd = document.getElementById('u-password').value;
    if (pwd) {
        payload.password = pwd;
    } else if (!uid) {
        payload.password = 'spices@123';
    }

    try {
        if (uid) {
            await api.updateUser(uid, payload);
            showToast('User updated', 'success');
        } else {
            await api.createUser(payload);
            showToast('User created', 'success');
        }
        closeUserModal();
        await loadAdminUsers();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save User';
    }
}

async function toggleUser(id, active) {
    await api.updateUser(id, { is_active: active });
    showToast(`User ${active ? 'activated' : 'deactivated'}`, 'info');
    await loadAdminUsers();
}


/* ══════════════════════════════════════════════════
   INVENTORY ADMIN
══════════════════════════════════════════════════ */
let allInventory = [];
let allProductsForAdj = [];
let allUsersForAdj = [];

async function initAdminInventory() {
    if (!initAdminBase('inventory')) return;

    await Promise.all([
        loadInventory(),
        loadAdjustDropdowns(),
    ]);

    const alertData = await api.getAlerts().catch(() => ({ alerts: [], count: 0 }));
    if (alertData.count > 0) {
        const banner = document.getElementById('alert-banner');
        banner.classList.remove('hidden');
        banner.style.display = 'flex';
        document.getElementById('alert-text').textContent =
            `⚠️ ${alertData.count} product(s) are low in stock: ${alertData.alerts.map(a => a.product_name).join(', ')}`;
    }
}

async function loadInventory() {
    const data = await api.getInventory().catch(() => ({ inventory: [] }));
    allInventory = data.inventory || [];

    // Populate owner filter
    const ownerFilter = document.getElementById('owner-filter');
    if (ownerFilter) {
        const owners = [...new Map(allInventory.map(i => [i.owner_id, { id: i.owner_id, name: i.owner_name, role: i.owner_role }])).values()];
        const current = ownerFilter.value;
        ownerFilter.innerHTML = '<option value="">All Owners</option>' +
            owners.map(o => `<option value="${o.id}" ${current==o.id?'selected':''}>${o.name} (${o.role})</option>`).join('');
    }

    const filtered = ownerFilter?.value
        ? allInventory.filter(i => i.owner_id == ownerFilter.value)
        : allInventory;

    renderInventoryTable(filtered);
}

function renderInventoryTable(items) {
    const body = document.getElementById('inventory-table-body');
    if (!items.length) {
        body.innerHTML = '<div class="empty-state"><p>No inventory records</p></div>';
        return;
    }

    body.innerHTML = `
        <table>
          <thead>
            <tr><th>Product</th><th>Unit</th><th>Owner</th><th>Role</th><th>Qty in Stock</th><th>Low Stock Threshold</th><th>Status</th></tr>
          </thead>
          <tbody>
            ${items.map(i => `
              <tr style="${i.is_low ? 'background:rgba(231,76,60,0.05)' : ''}">
                <td><strong>${productEmoji('')} ${i.product_name}</strong></td>
                <td class="td-muted">${i.product_unit||'—'}</td>
                <td>${i.owner_name}</td>
                <td>${roleBadge(i.owner_role)}</td>
                <td><strong style="color:${i.is_low ? 'var(--danger)' : 'var(--success)'}">${i.quantity}</strong></td>
                <td class="td-muted">${i.low_stock_threshold}</td>
                <td>${i.is_low
                    ? '<span class="badge badge-red">⚠️ Low Stock</span>'
                    : '<span class="badge badge-green">OK</span>'
                }</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
    `;
}

async function loadAdjustDropdowns() {
    const [prodData, userdata] = await Promise.all([
        api.getProducts().catch(() => ({ products: [] })),
        api.getUsers().catch(() => ({ users: [] })),
    ]);
    allProductsForAdj = prodData.products || [];
    allUsersForAdj    = userdata.users || [];

    const adjProd = document.getElementById('adj-product');
    const adjOwner = document.getElementById('adj-owner');
    if (adjProd) {
        adjProd.innerHTML = allProductsForAdj.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
    if (adjOwner) {
        adjOwner.innerHTML = allUsersForAdj.map(u => `<option value="${u.id}">${u.name} (${u.role})</option>`).join('');
    }
}

function openAdjustModal() {
    document.getElementById('adjust-modal').classList.add('open');
    document.getElementById('adjust-form').reset();
}
function closeAdjustModal() {
    document.getElementById('adjust-modal').classList.remove('open');
}

window.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('adjust-form');
    if (form) form.addEventListener('submit', applyAdjustment);
});

async function applyAdjustment(e) {
    e.preventDefault();
    const productId = document.getElementById('adj-product').value;
    const ownerId   = document.getElementById('adj-owner').value;
    const adjQty    = document.getElementById('adj-qty').value;
    const absQty    = document.getElementById('adj-absolute').value;

    try {
        if (absQty !== '') {
            await api.setStock({ product_id: parseInt(productId), owner_id: parseInt(ownerId), quantity: parseInt(absQty) });
        } else if (adjQty !== '') {
            await api.adjustStock({ product_id: parseInt(productId), owner_id: parseInt(ownerId), quantity: parseInt(adjQty) });
        } else {
            showToast('Enter an adjustment or absolute quantity', 'warning');
            return;
        }
        showToast('Stock updated', 'success');
        closeAdjustModal();
        await loadInventory();
    } catch (err) {
        showToast(err.message, 'error');
    }
}
