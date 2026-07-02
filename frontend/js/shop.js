/* shop.js — product catalog, cart, and checkout */

let allProducts = [];
let cart = JSON.parse(localStorage.getItem('cart')) || {};   // { productId: { product, qty } }
let activeCoupon = null; // { code, discount_percent }
let currentUser = null;

async function initShop() {
    currentUser = requireAuth();
    if (!currentUser) return;

    renderUserInfo();
    buildSidebar(currentUser.role, 'shop');
    initSidebarToggle();

    await loadCategories();
    await loadProducts();
    await loadAddresses();

    // Search
    document.getElementById('search-input').addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        const filtered = allProducts.filter(p =>
            p.name.toLowerCase().includes(q) ||
            (p.category||'').toLowerCase().includes(q)
        );
        renderProducts(filtered);
    });

    // Cart toggle
    document.getElementById('cart-btn').addEventListener('click', openCart);
}

async function loadCategories() {
    const data = await api.getCategories().catch(() => ({ categories: [] }));
    const pills = document.getElementById('category-pills');
    pills.innerHTML = `<div class="category-pill active" data-cat="" onclick="filterCategory(this,'')">All</div>`;
    (data.categories || []).forEach(cat => {
        const div = document.createElement('div');
        div.className = 'category-pill';
        div.dataset.cat = cat;
        div.textContent = cat;
        div.onclick = () => filterCategory(div, cat);
        pills.appendChild(div);
    });
}

async function loadAddresses() {
    try {
        const res = await apiRequest('GET', '/auth/addresses');
        const select = document.getElementById('checkout-address-select');
        const addresses = res.addresses || [];
        
        let html = '<option value="">Default Profile Address</option>';
        addresses.forEach(a => {
            html += `<option value="${a.id}">${a.title || 'Address'} - ${a.city}, ${a.state} ${a.is_default ? '(Default)' : ''}</option>`;
        });
        select.innerHTML = html;
        
        // Auto-select default
        const defaultAddr = addresses.find(a => a.is_default);
        if (defaultAddr) {
            select.value = defaultAddr.id;
        }
    } catch (e) {
        console.error("Failed to load addresses", e);
    }
}

async function loadProducts(params = {}) {
    const data = await api.getProducts(params).catch(() => ({ products: [] }));
    allProducts = data.products || [];
    renderProducts(allProducts);
}

function filterCategory(el, cat) {
    document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    const filtered = cat ? allProducts.filter(p => p.category === cat) : allProducts;
    renderProducts(filtered);
}

function renderProducts(products) {
    const grid = document.getElementById('products-grid');
    if (!products.length) {
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🌶️</div><p>No products found</p></div>`;
        return;
    }

    grid.innerHTML = products.map(p => `
        <div class="product-card" id="prod-${p.id}">
          <div class="product-img" style="${p.image_url ? `background:url('${p.image_url}') center/cover no-repeat;` : ''}">
            ${p.image_url ? '' : `<span>${productEmoji(p.category)}</span>`}
          </div>
          <div class="product-info">
            <div class="product-category">${p.category || 'General'}</div>
            <div class="product-name">${p.name}</div>
            <div class="product-unit">📦 ${p.unit || '—'}</div>
            <div class="product-price">${formatCurrency(p.my_price || 0)}</div>
          </div>
          <div class="product-actions">
            <button class="btn btn-primary btn-sm" style="flex:1" onclick="addToCart(${p.id})">
              + Add to Cart
            </button>
            ${cart[p.id] ? `<span class="badge badge-gold" id="cart-badge-${p.id}" style="display:inline-flex;align-items:center">×${cart[p.id].qty}</span>` : `<span id="cart-badge-${p.id}"></span>`}
          </div>
        </div>
    `).join('');
}

/* ─── Cart Logic ─────────────────────────────────────────────── */
function addToCart(productId) {
    const p = allProducts.find(x => x.id === productId);
    if (!p) return;

    if (cart[productId]) {
        cart[productId].qty++;
    } else {
        cart[productId] = { product: p, qty: 1 };
    }

    updateCartUI();
    showToast(`${p.name} added to cart`, 'success', 2000);
}

function removeFromCart(productId) {
    delete cart[productId];
    updateCartUI();
    renderCartItems();
}

function changeQty(productId, delta) {
    if (!cart[productId]) return;
    cart[productId].qty += delta;
    if (cart[productId].qty <= 0) {
        delete cart[productId];
    }
    updateCartUI();
    renderCartItems();
}

function updateCartUI() {
    const items = Object.values(cart);
    const count = items.reduce((s, i) => s + i.qty, 0);
    let total = items.reduce((s, i) => s + i.qty * (i.product.my_price || 0), 0);
    
    if (activeCoupon) {
        total = total * (1 - activeCoupon.discount_percent / 100);
    }

    document.getElementById('cart-count').textContent = count;
    document.getElementById('cart-total').textContent = formatCurrency(total);

    // Update badge on product card
    allProducts.forEach(p => {
        const badge = document.getElementById(`cart-badge-${p.id}`);
        if (badge) {
            if (cart[p.id]) {
                badge.className = 'badge badge-gold';
                badge.textContent = `×${cart[p.id].qty}`;
            } else {
                badge.textContent = '';
                badge.className = '';
            }
        }
    });

    // Save to localStorage
    localStorage.setItem('cart', JSON.stringify(cart));
}

function renderCartItems() {
    const container = document.getElementById('cart-items');
    const items = Object.entries(cart);

    if (!items.length) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">🛒</div><p>Your cart is empty</p></div>`;
        return;
    }

    container.innerHTML = items.map(([id, { product: p, qty }]) => `
        <div class="cart-item">
          <div class="cart-item-icon">${productEmoji(p.category)}</div>
          <div class="cart-item-info">
            <div class="cart-item-name">${p.name}</div>
            <div class="cart-item-price">${formatCurrency(p.my_price || 0)} × ${qty} = ${formatCurrency((p.my_price||0)*qty)}</div>
          </div>
          <div class="cart-qty">
            <button onclick="changeQty(${id},-1)">−</button>
            <span>${qty}</span>
            <button onclick="changeQty(${id},1)">+</button>
          </div>
          <button onclick="removeFromCart(${id})" style="background:none;border:none;color:var(--danger);cursor:pointer;font-size:1rem;margin-left:4px">✕</button>
        </div>
    `).join('');
}

function openCart() {
    renderCartItems();
    document.getElementById('cart-overlay').classList.add('open');
    document.getElementById('cart-panel').classList.add('open');
}

function closeCart() {
    document.getElementById('cart-overlay').classList.remove('open');
    document.getElementById('cart-panel').classList.remove('open');
}

async function applyPromo() {
    const input = document.getElementById('promo-code');
    const code = input.value.trim().toUpperCase();
    const msg = document.getElementById('promo-msg');
    
    if (!code) {
        activeCoupon = null;
        msg.textContent = '';
        updateCartUI();
        return;
    }
    
    try {
        const data = await apiRequest('POST', '/coupons/validate', { code }, true);
        
        activeCoupon = { code: data.code, discount_percent: data.discount_percent };
        msg.innerHTML = `<span style="color:#2e7d32">Applied: ${data.discount_percent}% off!</span>`;
        updateCartUI();
    } catch (e) {
        activeCoupon = null;
        msg.innerHTML = `<span style="color:var(--danger)">${e.message}</span>`;
        updateCartUI();
    }
}

async function checkout() {
    if (!Object.keys(cart).length) {
        showToast('Your cart is empty!', 'warning');
        return;
    }

    const btn = document.getElementById('checkout-btn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    const items = Object.entries(cart).map(([id, { qty }]) => ({
        product_id: parseInt(id),
        quantity: qty,
    }));
    
    const payload = { items };
    if (activeCoupon) {
        payload.coupon_code = activeCoupon.code;
    }
    
    const addressId = document.getElementById('checkout-address-select').value;
    if (addressId) {
        payload.address_id = parseInt(addressId);
    }

    try {
        // Step 1: Place the order in our system
        const data = await api.placeOrder(payload);
        const order = data.order;

        // Step 2: Create Razorpay payment order
        const payInfo = await api.createRazorpayOrder(order.total_amount, order.id);

        if (payInfo.mock) {
            // ── MOCK PAYMENT (no Razorpay keys configured) ─────────────────
            await api.verifyPayment({ mock: true, order_id: order.id, razorpay_order_id: payInfo.razorpay_order_id });
            cart = {}; localStorage.removeItem('cart'); activeCoupon = null; updateCartUI(); closeCart();
            showOrderSuccess(order, 'MOCK-PAID');
        } else {
            // ── REAL RAZORPAY CHECKOUT ──────────────────────────────────────
            const keyInfo = await api.getPaymentKey();
            const options = {
                key:      keyInfo.key_id,
                amount:   payInfo.amount,
                currency: 'INR',
                name:     'SpicesMart',
                description: `Order #${order.id}`,
                order_id: payInfo.razorpay_order_id,
                prefill: {
                    name:  currentUser.name,
                    email: currentUser.email,
                },
                theme: { color: '#e67e22' },
                handler: async (response) => {
                    // Verify payment on backend
                    const verified = await api.verifyPayment({
                        razorpay_order_id:  response.razorpay_order_id,
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_signature: response.razorpay_signature,
                        order_id: order.id,
                    });
                    if (verified.success) {
                        cart = {}; localStorage.removeItem('cart'); activeCoupon = null; updateCartUI(); closeCart();
                        showOrderSuccess(order, response.razorpay_payment_id);
                    } else {
                        showToast('Payment verification failed', 'error');
                    }
                },
                modal: { ondismiss: () => showToast('Payment cancelled', 'warning') }
            };
            const rzp = new window.Razorpay(options);
            rzp.open();
        }

    } catch (err) {
        showToast(err.message || 'Failed to place order', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Place Order';
    }
}

function showOrderSuccess(order, paymentId) {
    const details = document.getElementById('checkout-details');
    details.innerHTML = `
        <div style="background:rgba(46,204,113,0.08);border:1px solid rgba(46,204,113,0.25);border-radius:10px;padding:16px;margin-bottom:16px;text-align:center">
          <div style="font-size:2rem">✅</div>
          <div style="font-size:0.78rem;color:var(--text-muted)">ORDER ID</div>
          <div style="font-size:1.6rem;font-weight:800;color:var(--success)">#${order.id}</div>
          <div style="font-size:0.78rem;color:var(--text-muted);margin-top:4px">Payment: ${paymentId}</div>
        </div>
        <div style="line-height:2.2">
          <b>Ordered From:</b> ${order.seller_name}<br/>
          <b>Total Paid:</b> ${formatCurrency(order.total_amount)}<br/>
          <b>Items:</b> ${order.items.map(i => `${i.product_name} x${i.quantity}`).join(', ')}<br/>
          <b>Status:</b> ${statusBadge(order.status)} | <b>Payment:</b> ${statusBadge('paid')}
        </div>
    `;
    document.getElementById('checkout-modal').classList.add('open');
    showToast('Order placed & paid!', 'success');
}

function closeCheckoutModal() {
    document.getElementById('checkout-modal').classList.remove('open');
}

initShop();
