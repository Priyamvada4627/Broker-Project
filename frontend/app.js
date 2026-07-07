// Broker App — frontend logic



// When running on Vercel (or anywhere other than the same origin as the
// API), point this at your Render backend URL, e.g.:
//   const BASE = "https://your-app.onrender.com";
// Locally (opening this file directly, or same-origin testing) it falls
// back to the current origin.
const BASE = "https://broker-project-2.onrender.com";

let token = localStorage.getItem('token');


function nav(page, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (el) el.classList.add('active');

}


async function apiCall(method, path, body = null, isFormData = false) {
  const headers = {};
  if (token) headers['Authorization'] = 'Bearer ' + token;
  if (!isFormData && body) headers['Content-Type'] = 'application/json';
  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);
  try {
    const res = await fetch(BASE + path, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { detail: 'Network error or CORS — make sure your backend is running at ' + BASE } };
  }
}

// ─────────────────────────────────────────────
//  ALERT HELPERS
// ─────────────────────────────────────────────
function showAlert(id, type, msg) {
  document.getElementById(id).innerHTML = `<div class="alert ${type}">${msg}</div>`;
}

// ─────────────────────────────────────────────
//  AUTH
// ─────────────────────────────────────────────
async function doLogin() {
  const email = document.getElementById('loginEmail').value;
  const pass  = document.getElementById('loginPass').value;
  const form  = new URLSearchParams();
  form.append('username', email);
  form.append('password', pass);
  try {
    const res  = await fetch(BASE + '/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form
    });
    const data = await res.json();
    if (res.ok) {
      token = data.access_token;
      localStorage.setItem('token', token);
      const initials = email.slice(0, 2).toUpperCase();
      document.getElementById('userName').textContent = email;
      document.getElementById('userRole').textContent = 'logged in';
      document.getElementById('userAvatar').textContent = initials;
      showAlert('loginResult', 'success', 'Login successful — JWT stored.');
    } else {
      showAlert('loginResult', 'danger', 'Error: ' + (data.detail || JSON.stringify(data)));
    }
  } catch (e) {
    showAlert('loginResult', 'danger', 'Could not reach the server (' + e.message + '). Check your connection and try again.');
  }
}
function logout() {
  token = null;
  localStorage.removeItem('token');
  document.getElementById('userName').textContent = 'Not logged in';
  document.getElementById('userRole').textContent = '—';
  document.getElementById('userAvatar').textContent = '?';

  showAlert(
    'loginResult',
    'success',
    'Logged out successfully.'
  );

  nav('login', null);
} 
async function doRegister() {
  const email    = document.getElementById('regEmail').value;
  const password = document.getElementById('regPass').value;
  const phone    = document.getElementById('regPhone').value;
  const role     = document.getElementById('regRole').value;
  if (!email || !password) { showAlert('registerResult', 'danger', 'Email and password are required.'); return; }
  const r = await apiCall('POST', '/users/register', { email, password, phone, role });
  r.ok
    ? showAlert('registerResult', 'success', 'Registered successfully! Now login.')
    : showAlert('registerResult', 'danger', 'Error: ' + (r.data.detail || JSON.stringify(r.data)));
}

// ─────────────────────────────────────────────
//  BROWSE PROPERTIES
// ─────────────────────────────────────────────
async function loadProperties() {
  if (!token) { document.getElementById('propList').innerHTML = '<div class="alert danger">Please login first.</div>'; return; }
  const city    = document.getElementById('filterCity').value;
  const purpose = document.getElementById('filterPurpose').value;
  const type    = document.getElementById('filterType').value;
  const min     = document.getElementById('filterMin').value;
  const max     = document.getElementById('filterMax').value;
  const limit   = document.getElementById('filterLimit').value;

  let qs = `?limit=${limit}&offset=0`;
  if (city)    qs += `&city=${encodeURIComponent(city)}`;
  if (purpose) qs += `&purpose=${purpose}`;
  if (type)    qs += `&property_type=${type}`;
  if (min)     qs += `&price_min=${min}`;
  if (max)     qs += `&price_max=${max}`;

  const r = await apiCall('GET', '/properties/all' + qs);
  if (r.ok && Array.isArray(r.data)) {
    if (!r.data.length) { document.getElementById('propList').innerHTML = '<div class="alert info">No properties found.</div>'; return; }
    document.getElementById('propList').innerHTML = r.data.map(p => `
      <div class="card" style="margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:start">
          <div>
            <div style="font-weight:500;margin-bottom:4px">${p.description || 'Property #' + p.property_id}</div>
            <div style="font-size:12px;color:var(--text-secondary)">${p.location?.city || ''}, ${p.location?.state || ''}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:16px">
            <div style="font-size:16px;font-weight:500">₹${(p.price_to_pay || 0).toLocaleString('en-IN')}</div>
            <span class="badge ${p.is_available ? 'verified' : 'withdrawn'}">${p.is_available ? 'Available' : 'Sold'}</span>
          </div>
        </div>
        <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
          <button class="btn" onclick="document.getElementById('bidPropId').value='${p.property_id}';nav('mybids',null)">
            <i class="ti ti-gavel"></i> Place bid
          </button>
          <span style="font-size:12px;color:var(--text-tertiary)">ID: ${p.property_id}</span>
        </div>
      </div>
    `).join('');
  } else {
    document.getElementById('propList').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

// ─────────────────────────────────────────────
//  BIDS — BUYER
// ─────────────────────────────────────────────
async function loadBuyerBids() {
  if (!token) return;
  const r = await apiCall('GET', '/bid/buyer');
  if (r.ok && Array.isArray(r.data)) {
    if (!r.data.length) { document.getElementById('bidList').innerHTML = '<div class="alert info">No bids yet.</div>'; return; }
    document.getElementById('bidList').innerHTML = `
      <table class="table">
        <thead><tr><th>Interest ID</th><th>Property</th><th>Bid (₹)</th><th>Counter (₹)</th><th>Price to pay (₹)</th><th>Status</th></tr></thead>
        <tbody>
          ${r.data.map(b => `<tr>
            <td>${b.interest_id}</td>
            <td>${b.property_id}</td>
            <td>${(b.bid_amount || 0).toLocaleString('en-IN')}</td>
            <td>${b.counter_amount != null ? b.counter_amount.toLocaleString('en-IN') : '—'}</td>
            <td>${(b.price_to_pay || 0).toLocaleString('en-IN')}</td>
            <td><span class="badge ${b.status}">${b.status}</span></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } else {
    document.getElementById('bidList').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

async function placeBid() {
  if (!token) { showAlert('bidResult', 'danger', 'Login first.'); return; }
  const property_id = document.getElementById('bidPropId').value;
  const bid_amount  = parseInt(document.getElementById('bidAmount').value) || null;
  const message     = document.getElementById('bidMsg').value;
  if (!property_id) { showAlert('bidResult', 'danger', 'Property ID required.'); return; }
  const r = await apiCall('POST', `/bid/${property_id}`, { bid_amount, message });
  if (r.ok) {
    let msg = `Bid placed! Interest ID: <strong>${r.data.interest_id}</strong>`;
    if (r.data.ml_warning) msg += `<br><span style="color:var(--warning-text)">⚠️ ${r.data.ml_warning}</span>`;
    showAlert('bidResult', 'success', msg);
  } else {
    showAlert('bidResult', 'danger', r.data.detail || JSON.stringify(r.data));
  }
}

async function updateBid() {
  if (!token) { showAlert('updateBidResult', 'danger', 'Login first.'); return; }
  const id     = document.getElementById('updateBidId').value;
  const action = document.getElementById('updateBidAction').value;
  if (!id) { showAlert('updateBidResult', 'danger', 'Interest ID required.'); return; }
  const r = await apiCall('PATCH', `/bid/${id}`, { action });
  r.ok
    ? showAlert('updateBidResult', 'success', `Done. New status: <strong>${r.data.status}</strong>`)
    : showAlert('updateBidResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

// ─────────────────────────────────────────────
//  ADD PROPERTY (SELLER)
// ─────────────────────────────────────────────
async function addProperty() {
  if (!token) { showAlert('addPropResult', 'danger', 'Login first.'); return; }
  const city          = document.getElementById('pCity').value;
  const state         = document.getElementById('pState').value;
  const pincode       = document.getElementById('pPin').value;
  const description   = document.getElementById('pDesc').value;
  const property_type = document.getElementById('pType').value;
  const purpose       = document.getElementById('pPurpose').value;
  const price         = parseInt(document.getElementById('pPrice').value) || 0;
  const bedrooms      = parseInt(document.getElementById('pBed').value) || 2;
  const bathrooms     = parseInt(document.getElementById('pBath').value) || 2;
  const area          = parseFloat(document.getElementById('pArea').value) || 1000;
  if (!city || !state || !price) { showAlert('addPropResult', 'danger', 'City, state and price are required.'); return; }
  const r = await apiCall('POST', '/properties/add', {
    city, state, pincode, description, property_type, purpose,
    price, is_available: true, bedrooms, bathrooms, area
  });
  if (r.ok) {
    showAlert('addPropResult', 'success', `Property listed! ID: <strong>${r.data.id}</strong>`);
    const hint = r.data.ml_price_hint;
    if (hint) {
      document.getElementById('mlHintBox').classList.add('show');
      document.getElementById('mlHintPrice').textContent = `₹${(hint.estimated_fair_price || 0).toLocaleString('en-IN')}`;
      document.getElementById('mlHintRange').textContent =
      `Range: ₹${(hint.price_range?.low || 0).toLocaleString('en-IN')} – ₹${(hint.price_range?.high || 0).toLocaleString('en-IN')}`;
      document.getElementById('mlHintNote').textContent = hint.note || '';
    }
  } else {
    showAlert('addPropResult', 'danger', r.data.detail || JSON.stringify(r.data));
  }
}

// ─────────────────────────────────────────────
//  MY LISTINGS (SELLER)
// ─────────────────────────────────────────────
async function loadMyProps() {
  if (!token) { document.getElementById('myPropList').innerHTML = '<div class="alert danger">Login first.</div>'; return; }
  const r = await apiCall('GET', '/properties/my');
  if (r.ok && Array.isArray(r.data)) {
    if (!r.data.length) { document.getElementById('myPropList').innerHTML = '<div class="alert info">No listings yet.</div>'; return; }
    document.getElementById('myPropList').innerHTML = r.data.map(p => `
      <div class="card" style="margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:start">
          <div>
            <div style="font-weight:500">${p.description || 'Property #' + p.id}</div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:3px">
              ₹${(p.price || 0).toLocaleString('en-IN')} · ${p.property_type} · ${p.purpose}
            </div>
          </div>
          <span class="badge ${p.verification_status === 'verified' ? 'verified' : p.verification_status === 'pending' ? 'pending' : 'rejected'}">
            ${p.verification_status}
          </span>
        </div>
        ${p.remarks ? `<div class="alert warning" style="margin-top:8px;font-size:12px">Agent remarks: ${p.remarks}</div>` : ''}
      </div>
    `).join('');
  } else {
    document.getElementById('myPropList').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

async function loadSellerBids() {
  if (!token) return;
  const r = await apiCall('GET', '/bid/seller');
  if (r.ok && Array.isArray(r.data)) {
    if (!r.data.length) { document.getElementById('sellerBidList').innerHTML = '<div class="alert info">No bids on your listings yet.</div>'; return; }
    document.getElementById('sellerBidList').innerHTML = `
      <table class="table">
        <thead><tr><th>Interest ID</th><th>Property</th><th>Bid (₹)</th><th>Counter (₹)</th><th>Status</th></tr></thead>
        <tbody>
          ${r.data.map(b => `<tr>
            <td>${b.interest_id}</td>
            <td>${b.property_id}</td>
            <td>${(b.bid_amount || 0).toLocaleString('en-IN')}</td>
            <td>${b.counter_amount != null ? b.counter_amount.toLocaleString('en-IN') : '—'}</td>
            <td><span class="badge ${b.status}">${b.status}</span></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  }
}

async function respondToBid() {
  if (!token) { showAlert('sellerBidResult', 'danger', 'Login first.'); return; }
  const id      = document.getElementById('sellerBidId').value;
  const action  = document.getElementById('sellerBidAction').value;
  const counter = document.getElementById('sellerCounter').value;
  if (!id) { showAlert('sellerBidResult', 'danger', 'Interest ID required.'); return; }
  const body = { action };
  if (action === 'counter' && counter) body.counter_amount = parseInt(counter);
  const r = await apiCall('PATCH', `/bid/${id}`, body);
  r.ok
    ? showAlert('sellerBidResult', 'success', `Done. Status: <strong>${r.data.status}</strong>`)
    : showAlert('sellerBidResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

// ─────────────────────────────────────────────
//  DEALS
// ─────────────────────────────────────────────
async function loadMyDeals() {
  if (!token) { document.getElementById('myDealList').innerHTML = '<div class="alert danger">Login first.</div>'; return; }
  const r = await apiCall('GET', '/deals/my');
  if (r.ok && Array.isArray(r.data)) {
    if (!r.data.length) { document.getElementById('myDealList').innerHTML = '<div class="alert info">No deals yet.</div>'; return; }
    document.getElementById('myDealList').innerHTML = `
      <table class="table">
        <thead><tr><th>Deal ID</th><th>Property</th><th>Seller price (₹)</th><th>Agent fee (₹)</th><th>Final price (₹)</th><th>Status</th></tr></thead>
        <tbody>
          ${r.data.map(d => `<tr>
            <td>${d.deal_id}</td>
            <td>${d.property_id}</td>
            <td>${(d.seller_price || 0).toLocaleString('en-IN')}</td>
            <td>${(d.agent_fee || 0).toLocaleString('en-IN')}</td>
            <td>${(d.final_price || 0).toLocaleString('en-IN')}</td>
            <td><span class="badge ${d.status === 'completed' ? 'completed' : d.status.includes('document') || d.status.includes('pending') ? 'pending' : 'active'}">${d.status}</span></td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  } else {
    document.getElementById('myDealList').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

async function uploadDoc() {
  if (!token) { showAlert('docResult', 'danger', 'Login first.'); return; }
  const deal_id  = document.getElementById('docDealId').value;
  const doc_type = document.getElementById('docType').value;
  const file     = document.getElementById('docFile').files[0];
  if (!deal_id || !file) { showAlert('docResult', 'danger', 'Deal ID and file are required.'); return; }
  const fd = new FormData();
  fd.append('document_type', doc_type);
  fd.append('file', file);
  const r = await apiCall('POST', `/deals/${deal_id}/documents`, fd, true);
  r.ok
    ? showAlert('docResult', 'success', `Uploaded! Document ID: <strong>${r.data.document_id}</strong><br>URL: <a href="${r.data.file_url}" target="_blank" style="color:inherit">${r.data.file_url}</a>`)
    : showAlert('docResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

async function confirmPayment() {
  if (!token) { showAlert('payResult', 'danger', 'Login first.'); return; }
  const id = document.getElementById('payDealId').value;
  if (!id) { showAlert('payResult', 'danger', 'Deal ID required.'); return; }
  const r = await apiCall('PATCH', `/deals/${id}/pay`);
  r.ok
    ? showAlert('payResult', 'success', r.data.message)
    : showAlert('payResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

// ─────────────────────────────────────────────
//  AGENT DASHBOARD
// ─────────────────────────────────────────────
async function loadAgentDash() {
  if (!token) return;
  const r = await apiCall('GET', '/agents/dashboard');
  if (r.ok) {
    const d = r.data;
    const s = d.summary || {};
    document.getElementById('agentMetrics').innerHTML = `
      <div class="metric"><div class="metric-label">Assigned properties</div><div class="metric-value">${s.total_assigned_properties ?? '—'}</div></div>
      <div class="metric"><div class="metric-label">Pending verification</div><div class="metric-value">${s.pending_verification ?? '—'}</div></div>
      <div class="metric"><div class="metric-label">Active deals</div><div class="metric-value">${s.active_deals ?? '—'}</div></div>
      <div class="metric"><div class="metric-label">Pending docs</div><div class="metric-value">${s.pending_documents ?? '—'}</div></div>
    `;
    document.getElementById('agentDetails').innerHTML = `
      <div class="card">
        <div class="card-title">Properties assigned</div>
        ${d.properties?.length ? `
          <table class="table">
            <thead><tr><th>ID</th><th>Description</th><th>City</th><th>Price</th><th>Modified</th><th>Status</th></tr></thead>
            <tbody>
              ${d.properties.map(p => `<tr>
                <td>${p.property_id}</td>
                <td>${p.description || '—'}</td>
                <td>${p.city || '—'}</td>
                <td>₹${(p.price || 0).toLocaleString('en-IN')}</td>
                <td>${p.is_modified ? 'Yes' : 'No'}</td>
                <td><span class="badge ${p.verification_status === 'verified' ? 'verified' : 'pending'}">${p.verification_status}</span></td>
              </tr>`).join('')}
            </tbody>
          </table>` : '<div class="alert info">No properties assigned.</div>'}
      </div>
      <div class="card">
        <div class="card-title">Active deals</div>
        ${d.active_deals?.length ? `
          <table class="table">
            <thead><tr><th>Deal ID</th><th>Property</th><th>Final price</th><th>Status</th></tr></thead>
            <tbody>
              ${d.active_deals.map(deal => `<tr>
                <td>${deal.deal_id}</td>
                <td>${deal.property_id}</td>
                <td>₹${(deal.final_price || 0).toLocaleString('en-IN')}</td>
                <td><span class="badge pending">${deal.status}</span></td>
              </tr>`).join('')}
            </tbody>
          </table>` : '<div class="alert info">No active deals.</div>'}
      </div>
      <div class="card">
        <div class="card-title">Pending documents to review</div>
        ${d.pending_documents?.length ? `
          <table class="table">
            <thead><tr><th>Doc ID</th><th>Deal ID</th><th>Type</th><th>Uploaded by</th></tr></thead>
            <tbody>
              ${d.pending_documents.map(doc => `<tr>
                <td>${doc.document_id}</td>
                <td>${doc.deal_id}</td>
                <td>${doc.document_type}</td>
                <td>${doc.uploaded_by}</td>
              </tr>`).join('')}
            </tbody>
          </table>` : '<div class="alert info">No pending documents.</div>'}
      </div>
    `;
  } else {
    document.getElementById('agentDetails').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

// ─────────────────────────────────────────────
//  AGENT — VERIFY PROPERTY
// ─────────────────────────────────────────────
async function verifyProperty() {
  if (!token) { showAlert('vpResult', 'danger', 'Login first.'); return; }
  const id      = document.getElementById('vpId').value;
  const action  = document.getElementById('vpAction').value;
  const remarks = document.getElementById('vpRemarks').value;
  if (!id) { showAlert('vpResult', 'danger', 'Property ID required.'); return; }
  let url = `/agents/verify/property/${id}?action=${action}`;
  if (remarks) url += `&remarks=${encodeURIComponent(remarks)}`;
  const r = await apiCall('PATCH', url);
  r.ok
    ? showAlert('vpResult', 'success', r.data.message)
    : showAlert('vpResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

async function registerAgent() {
  if (!token) { showAlert('agResult', 'danger', 'Login first.'); return; }
  const email       = document.getElementById('agEmail').value;
  const password    = document.getElementById('agPass').value;
  const name        = document.getElementById('agName').value;
  const fee_percent = parseFloat(document.getElementById('agFee').value) || 2.5;
  const phone       = document.getElementById('agPhone').value;
  if (!email || !password || !name) { showAlert('agResult', 'danger', 'Email, password and name are required.'); return; }
  const r = await apiCall('POST', '/agents/register', {
    email, password, name, fee_percent, phone, min_fee: 5000, max_fee: 500000
  });
  r.ok
    ? showAlert('agResult', 'success', `Agent created! Agent ID: <strong>${r.data.agent_id}</strong>`)
    : showAlert('agResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

// ─────────────────────────────────────────────
//  AGENT — DOCUMENTS
// ─────────────────────────────────────────────
async function viewDealDocs() {
  if (!token) return;
  const id = document.getElementById('viewDocsDealId').value;
  if (!id) return;
  const r = await apiCall('GET', `/deals/${id}/documents`);
  if (r.ok && Array.isArray(r.data)) {
    document.getElementById('docViewList').innerHTML = r.data.length ? `
      <table class="table">
        <thead><tr><th>Doc ID</th><th>Type</th><th>Status</th><th>Uploaded by</th><th>Notes</th><th>File</th></tr></thead>
        <tbody>
          ${r.data.map(d => `<tr>
            <td>${d.document_id}</td>
            <td>${d.document_type}</td>
            <td><span class="badge ${d.status}">${d.status}</span></td>
            <td>${d.uploaded_by}</td>
            <td style="font-size:12px;color:var(--text-secondary)">${d.notes || '—'}</td>
            <td>${d.file_url ? `<a href="${d.file_url}" target="_blank" style="font-size:12px;color:var(--info-text)">View</a>` : '—'}</td>
          </tr>`).join('')}
        </tbody>
      </table>` : '<div class="alert info">No documents for this deal.</div>';
  } else {
    document.getElementById('docViewList').innerHTML = `<div class="alert danger">${r.data.detail || JSON.stringify(r.data)}</div>`;
  }
}

async function verifyDoc() {
  if (!token) { showAlert('vdResult', 'danger', 'Login first.'); return; }
  const deal_id = document.getElementById('vdDealId').value;
  const doc_id  = document.getElementById('vdDocId').value;
  const status  = document.getElementById('vdStatus').value;
  const notes   = document.getElementById('vdNotes').value;
  if (!deal_id || !doc_id) { showAlert('vdResult', 'danger', 'Deal ID and Document ID required.'); return; }
  let url = `/deals/${deal_id}/documents/${doc_id}/verify?status=${status}`;
  if (notes) url += `&notes=${encodeURIComponent(notes)}`;
  const r = await apiCall('PATCH', url);
  r.ok
    ? showAlert('vdResult', 'success', `${r.data.message}. Deal status now: <strong>${r.data.deal_status}</strong>`)
    : showAlert('vdResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

async function completeDeal() {
  if (!token) { showAlert('completeResult', 'danger', 'Login first.'); return; }
  const id = document.getElementById('completeDealId').value;
  if (!id) { showAlert('completeResult', 'danger', 'Deal ID required.'); return; }
  const r = await apiCall('PATCH', `/deals/${id}/complete`);
  r.ok
    ? showAlert('completeResult', 'success', r.data.message)
    : showAlert('completeResult', 'danger', r.data.detail || JSON.stringify(r.data));
}

// ─────────────────────────────────────────────
//  ML PRICE ESTIMATE
// ─────────────────────────────────────────────
async function getMLEstimate() {
  if (!token) { showAlert('mlResult', 'danger', 'Login first.'); return; }
  const city     = document.getElementById('mlCity').value;
  const type     = document.getElementById('mlType').value;
  const purpose  = document.getElementById('mlPurpose').value;
  const beds     = document.getElementById('mlBed').value;
  const baths    = document.getElementById('mlBath').value;
  const area     = document.getElementById('mlArea').value;
  const furn     = document.getElementById('mlFurn').value;
  const locality = document.getElementById('mlLocality').value;
  if (!city) { showAlert('mlResult', 'danger', 'City is required.'); return; }
  let url = `/ml/price-estimate?city=${encodeURIComponent(city)}&property_type=${type}&purpose=${purpose}&bedrooms=${beds}&bathrooms=${baths}&area=${area}&furnishing=${encodeURIComponent(furn)}`;
  if (locality) url += `&locality=${encodeURIComponent(locality)}`;
  const r = await apiCall('GET', url);
  if (r.ok) {
    const d = r.data;
    document.getElementById('mlResult').innerHTML = `
    <div class="card" style="margin:0">
      <div style="font-size:26px;font-weight:500;margin-bottom:4px">
        ₹${(d.predicted_price || 0).toLocaleString('en-IN')}
      </div>
      <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">
        Range: ₹${(d.price_range?.low || 0).toLocaleString('en-IN')} – ₹${(d.price_range?.high || 0).toLocaleString('en-IN')}
      </div>
      <div style="display:flex;gap:20px;font-size:13px;color:var(--text-secondary);flex-wrap:wrap">
        <span>Confidence: <strong>${d.confidence ? d.confidence.charAt(0).toUpperCase() + d.confidence.slice(1) : '—'}</strong></span>
        <span>Model R²: <strong>${d.model_r2}</strong></span>
      </div>
      <div style="margin-top:10px;font-size:12px;color:var(--text-secondary)">${d.note || ''}</div>
    </div>`;
} else {
  showAlert('mlResult', 'danger', r.data.detail || JSON.stringify(r.data));
}
}


