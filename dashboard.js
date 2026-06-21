// dashboard.js
// Handles all API calls and chart rendering for CustomerAI dashboard
// Quick and dirty - needs a proper framework (React? asked team, no decision yet)

const API_BASE = window.location.origin;  // same origin as Flask app

let segmentChart = null;
let allCustomers = [];
let filteredCustomers = [];

// ---- init ----
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('last-updated').textContent =
    'Last updated: ' + new Date().toLocaleTimeString();

  loadCustomers();

  document.getElementById('segment-filter').addEventListener('change', applyFilters);
  document.getElementById('search-input').addEventListener('input', applyFilters);
});


// ---- data fetching ----
async function loadCustomers() {
  try {
    const res = await fetch(`${API_BASE}/api/customers?per_page=500`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allCustomers = data.customers;
    filteredCustomers = [...allCustomers];
    renderKPIs(allCustomers);
    renderSegmentChart(allCustomers);
    renderTable(filteredCustomers);
  } catch (err) {
    console.error('Failed to load customers:', err);
    document.getElementById('customer-tbody').innerHTML =
      `<tr><td colspan="6" class="text-center text-danger">Failed to load data: ${err.message}</td></tr>`;
  }
}

async function loadRecommendations(customerId, customerName) {
  const panel = document.getElementById('rec-panel');
  const body = document.getElementById('rec-body');
  document.getElementById('rec-customer-name').textContent = customerName;
  panel.style.display = '';

  body.innerHTML = '<div class="text-muted">Loading...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, n: 5 })
    });
    const data = await res.json();
    renderRecommendations(data.recommendations);
  } catch (err) {
    body.innerHTML = `<div class="text-danger">Error: ${err.message}</div>`;
  }
}


// ---- rendering ----
function renderKPIs(customers) {
  document.getElementById('kpi-total').textContent = customers.length.toLocaleString();

  const vipCount = customers.filter(c => c.segment === 'VIP').length;
  document.getElementById('kpi-vip').textContent = vipCount.toLocaleString();

  // churn high risk > 0.7
  const highRisk = customers.filter(c => (c.churn_probability || 0) > 0.7).length;
  document.getElementById('kpi-churn').textContent = highRisk.toLocaleString();

  const avgCLV = customers.reduce((s, c) => s + (c.clv || 0), 0) / customers.length;
  document.getElementById('kpi-clv').textContent =
    '$' + Math.round(avgCLV).toLocaleString();
}

function renderSegmentChart(customers) {
  const counts = { VIP: 0, Regular: 0, 'At-Risk': 0, New: 0 };
  customers.forEach(c => { if (counts[c.segment] !== undefined) counts[c.segment]++; });

  const ctx = document.getElementById('segmentChart').getContext('2d');
  if (segmentChart) segmentChart.destroy();

  segmentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: Object.keys(counts),
      datasets: [{
        data: Object.values(counts),
        backgroundColor: ['#7c3aed', '#0369a1', '#b45309', '#166534'],
        borderWidth: 0,
      }]
    },
    options: {
      plugins: {
        legend: { labels: { color: '#e2e8f0', font: { size: 12 } } }
      }
    }
  });
}

function renderTable(customers) {
  const tbody = document.getElementById('customer-tbody');
  if (!customers.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No results</td></tr>';
    return;
  }

  tbody.innerHTML = customers.slice(0, 100).map(c => {
    const seg = c.segment || 'Unknown';
    const segClass = `badge-${seg.toLowerCase().replace('-', '-')}`;
    const churnProb = c.churn_probability || 0;
    const riskClass = churnProb > 0.7 ? 'risk-high' : churnProb > 0.4 ? 'risk-medium' : 'risk-low';
    const riskLabel = churnProb > 0.7 ? 'HIGH' : churnProb > 0.4 ? 'MED' : 'LOW';

    return `<tr onclick="loadRecommendations(${c.customer_id}, '${(c.company || '').replace(/'/g, "\\'")}')">
      <td>${c.customer_id}</td>
      <td>${c.company || '—'}</td>
      <td><span class="segment-badge ${segClass}">${seg}</span></td>
      <td>$${Math.round(c.clv || 0).toLocaleString()}</td>
      <td><span class="${riskClass}">${riskLabel}</span></td>
      <td><button class="btn btn-outline-secondary btn-sm py-0" onclick="event.stopPropagation();alert('TODO: open detail view')">View</button></td>
    </tr>`;
  }).join('');

  document.getElementById('table-footer').textContent =
    `Showing ${Math.min(100, customers.length)} of ${customers.length} customers`;
}

function renderRecommendations(recs) {
  const body = document.getElementById('rec-body');
  if (!recs || !recs.length) {
    body.innerHTML = '<p class="text-muted">No recommendations available.</p>';
    return;
  }
  body.innerHTML = `<div class="d-flex flex-column gap-2">` +
    recs.map(r => `<div class="rec-card">
      <div>
        <strong>${r.name || r.product_id}</strong>
        <span class="text-muted ms-2">${r.category || ''}</span>
      </div>
      <div class="d-flex align-items-center gap-3">
        <span>${r.price ? '$' + r.price : ''}</span>
        <span class="rec-score">Score: ${r.score || '—'}</span>
      </div>
    </div>`).join('') + `</div>`;
}


// ---- filtering ----
function applyFilters() {
  const seg = document.getElementById('segment-filter').value;
  const q = document.getElementById('search-input').value.toLowerCase();

  filteredCustomers = allCustomers.filter(c => {
    const matchSeg = !seg || c.segment === seg;
    const matchQ = !q || (c.company || '').toLowerCase().includes(q) ||
                         String(c.customer_id).includes(q);
    return matchSeg && matchQ;
  });

  renderTable(filteredCustomers);
}
