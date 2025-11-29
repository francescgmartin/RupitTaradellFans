
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

// sanitize JSON text by replacing bare NaN tokens outside string literals with null
function sanitizeJsonText(text) {
  let out = '';
  let inString = false;
  let stringChar = '';
  let esc = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];

    if (inString) {
      out += ch;
      if (esc) {
        esc = false;
      } else if (ch === '\\') {
        esc = true;
      } else if (ch === stringChar) {
        inString = false;
        stringChar = '';
      }
      continue;
    }

    // not inside string
    if (ch === '"' || ch === "'") {
      inString = true;
      stringChar = ch;
      out += ch;
      continue;
    }

    // attempt to detect bare NaN token
    if (ch === 'N' && text.substr(i, 3) === 'NaN') {
      const prev = text[i - 1] || '';
      const next = text[i + 3] || '';
      // check boundaries: previous/next should not be word char or quote/bracket that suggest it's inside a name/string
      const prevOk = !/[\w\]"']/.test(prev);
      const nextOk = !/[\w\["']/.test(next);
      if (prevOk && nextOk) {
        out += 'null';
        i += 2; // advance past 'NaN'
        continue;
      }
    }

    out += ch;
  }
  return out;
}

// small helper to fetch JSON even if the file contains NaN tokens
async function fetchPossiblyInvalidJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status} for ${url}`);
    err.status = res.status;
    throw err;
  }
  const text = await res.text();
  // first try safe sanitize (avoids touching "NaN" inside strings)
  const cleaned = sanitizeJsonText(text);
  try {
    return JSON.parse(cleaned);
  } catch (e1) {
    // fallback: blunt replacement (covers some edge cases)
    try {
      const fallback = text.replace(/\bNaN\b/g, 'null');
      return JSON.parse(fallback);
    } catch (e2) {
      // rethrow the original parse error with context
      console.error('Failed to parse JSON after sanitization for', url, e1, e2);
      throw e1;
    }
  }
}

// ---------------- FKT (unisex) ----------------
async function loadFKT() {
  const url = `${DATA_BASE_URL}/leaders/leaders_fkt_skt.json`;
  console.log('[loadFKT] fetching', url);
  try {
    const data = await fetchPossiblyInvalidJson(url);
    const top = (data?.overall?.FKT_top10) || [];
    const distanceKm = 45; // same default as ETL
    const tbody = document.querySelector('#fkt-table tbody');
    renderRows(tbody, top, distanceKm);
    console.log(`[loadFKT] rendered ${top.length} rows`);
  } catch (err) {
    console.error('[loadFKT] fetch error', err);
  }
}


// ---------------- FKT (femení, mateix patró que unisex) ----------------
async function loadFKTFemale() {
  const url = `${DATA_BASE_URL}/leaders/leaders_fkt_skt.json`;
  console.log('[loadFKTFemale] fetching', url);
  try {
    const data = await fetchPossiblyInvalidJson(url);
    // Canvi únic: node del JSON
    const top = (data?.by_gender?.F?.FKT_top10) || [];
    const distanceKm = 45; // mateix default que l’ETL
    const tbody = document.querySelector('#fkt-female-table tbody'); // mateix patró, altre selector
    renderRows(tbody, top, distanceKm);
    console.log(`[loadFKTFemale] rendered ${top.length} rows`);
  } catch (err) {
    console.error('[loadFKTFemale] fetch error', err);
  }
}



// ---------------- Edition results ----------------
async function loadEdition(year) {
  const url = `${DATA_BASE_URL}/${year}.json`; // ALWAYS include /out base
  console.log('[loadEdition] fetching', url);
  try {
    const data = await fetchPossiblyInvalidJson(url);
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
  loadFKTFemale();  // femení (by_gender.F.FKT_top10)
});
