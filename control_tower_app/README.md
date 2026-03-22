# Network Planning Control Tower — Setup Guide

A live web application that replaces static Jupyter notebooks with a real-time
supply-chain dashboard.
FastAPI backend + React (Vite + Tailwind) frontend.

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

---

## 1 — Start the Python Backend

```bash
# From the project root
cd control_tower_app/backend

# (Optional but recommended) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server (auto-reloads on file save)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

---

## 2 — Start the React Frontend

Open a **second terminal**:

```bash
# From the project root
cd control_tower_app/frontend

# Install Node dependencies (first run only)
npm install

# Start the Vite dev server
npm run dev
```

The app will open at **http://localhost:3000**

---

## 3 — Run Both Simultaneously (one-liner, Windows)

```powershell
# From project root — runs both servers in parallel
Start-Process -NoNewWindow powershell {cd control_tower_app\backend; uvicorn main:app --reload --port 8000}; cd control_tower_app\frontend; npm run dev
```

Or use two separate terminals as shown in steps 1 & 2 above.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Connectivity check |
| GET | `/api/kpis` | Headline KPIs for latest date |
| GET | `/api/exceptions` | Overnight inbound exceptions (PO-level) |
| GET | `/api/forecast` | Daily Supply vs Demand across planning horizon |
| GET | `/api/allocations` | Tier-based allocation for a shortage SKU/Location |

### Query parameters

**`/api/exceptions`**
- `delivery_date` — filter to a specific date (YYYYMMDD, default: all dates)
- `min_variance` — minimum missing cases to include (default: 1)

**`/api/allocations`**
- `sku_key` — integer SKU surrogate key (default: `4` = RTBB1015)
- `location_key` — integer location surrogate key (default: `124` = MPL1)

---

## AI Features (Gemini)

1. Obtain a free Gemini API key at **https://aistudio.google.com**
2. Click **"Enter Gemini API key"** in the dashboard AI panel
3. Paste your key (stored only in browser memory — never sent to the backend)
4. Click **✨ Generate Action Plan** or **✨ Draft Supplier Email**

The AI reads the live dashboard state (KPIs + top exceptions + allocation data)
and generates a context-aware response.

---

## Directory Structure

```
control_tower_app/
├── backend/
│   ├── main.py             ← FastAPI app (4 endpoints)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js      ← proxies /api → localhost:8000
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx         ← full dashboard (KPIs, chart, tables, AI)
│       └── index.css       ← Tailwind directives + component classes
└── README.md               ← this file
```

## Data path

Both the backend and the notebooks read from:

```
../../data/curated/   (relative to control_tower_app/backend/main.py)
```

No database required — the app reads the curated star-schema CSVs directly.
