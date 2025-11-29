
// Base URL for data (relative to where index.html is served)
const DATA_BASE_URL = './out'; // IMPORTANT: keep 'out' here
const AVAILABLE_YEARS = [2013,2014,2015,2016,2017,2018,2019,2021, 2022, 2023, 2024, 2025]; // Update with your real years

// ---------------- Utils ----------------
function secondsToHMS(total) {
  if (total == null || isNaN(total)) return '';
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  const hh = h > 0 ? `${h}:` : '';
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  const ss = String(s).padStart(2, '0');
  return `${hh}${mm}:${ss}`;
}

function paceMinPerKm(seconds, distanceKm) {
  if (!seconds || !distanceKm) return '';
  const minPerKm = (seconds / 60) / distanceKm;
  const m = Math.floor(minPerKm);
  const s = Math.round((minPerKm - m) * 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function renderRows(tbody, rows, distanceKm) {
  tbody.innerHTML = '';
  rows.forEach((r, idx) => {
    const tr = document.createElement('tr');
    const pace = paceMinPerKm(r.time_net, distanceKm);
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td>${r.full_name ?? ''}</td>
      <td>${r.gender ?? ''}</td>
      <td>${secondsToHMS(r.sant_julia)}</td>
      <td>${secondsToHMS(r.time_net)}</td>
      <td>${pace}</td>
      <td>${r.club ?? ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------------- FKT (unisex) ----------------
async function loadFKT() {
  const url = `${DATA_BASE_URL}/leaders/leaders_fkt_skt.json`;
  console.log('[loadFKT] fetching', url);
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`[loadFKT] HTTP ${res.status} for`, url);
      return;
    }
    const data = await res.json();
    const top = (data?.overall?.FKT_top10) || [];
    const distanceKm = 45; // same default as ETL
    const tbody = document.querySelector('#fkt-table tbody');
    renderRows(tbody, top, distanceKm);
    console.log(`[loadFKT] rendered ${top.length} rows`);
  } catch (err) {
    console.error('[loadFKT] fetch error', err);
  }
}

// ---------------- Edition results ----------------
async function loadEdition(year) {
  const url = `${DATA_BASE_URL}/${year}.json`; // ALWAYS include /out base
  console.log('[loadEdition] fetching', url);
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.error(`[loadEdition] HTTP ${res.status} for`, url);
      return;
    }
    const data = await res.json();
    const distanceKm = data?.edition?.distance_km || 45;
    const rows = Array.isArray(data.results) ? data.results.slice() : [];

    // Order by net time ascending; non-finishers go to bottom
    rows.sort((a, b) => {
      const ta = (typeof a.time_net === 'number') ? a.time_net : Number.MAX_SAFE_INTEGER;
      const tb = (typeof b.time_net === 'number') ? b.time_net : Number.MAX_SAFE_INTEGER;
      return ta - tb;
    });

    const tbody = document.querySelector('#edition-table tbody');
    renderRows(tbody, rows, distanceKm);
    console.log(`[loadEdition] rendered ${rows.length} rows for`, year);
  } catch (err) {
    console.error('[loadEdition] fetch error', err);
  }
}

function initYearSelect() {
  const sel = document.getElementById('edition-select');
  sel.innerHTML = AVAILABLE_YEARS.map(y => `<option value="${y}">${y}</option>`).join('');
  sel.addEventListener('change', () => loadEdition(sel.value));
  if (AVAILABLE_YEARS.length) {
    sel.value = AVAILABLE_YEARS[AVAILABLE_YEARS.length - 1];
    loadEdition(sel.value);
  }
}

// ---------------- Init ----------------
document.addEventListener('DOMContentLoaded', () => {
  initYearSelect();
  loadFKT();
});
