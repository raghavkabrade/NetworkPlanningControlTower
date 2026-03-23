import { useState, useEffect, useCallback, useMemo } from 'react'
import axios from 'axios'
import {
  Package, TrendingDown, TrendingUp, AlertTriangle,
  RefreshCw, Sparkles, Mail, Wifi, WifiOff,
  ChevronDown, ChevronUp, BarChart2, Truck, ShoppingCart,
  Activity, Clock, Search, X, Filter, Calendar, GitMerge,
  MapPin, ChevronRight, Layers, Edit3, Check, ArrowRight, Zap,
} from 'lucide-react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const API = '/api'
const GEMINI_ENDPOINT =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'




// ─────────────────────────────────────────────────────────────────────────────
// MOCK DATA — Drill-down hierarchy: Location → Commodity → Customer → SKUs
// ─────────────────────────────────────────────────────────────────────────────
const MOCK_NETWORK_ALERTS = [
  {
    id: 'MPL1-Beefsteak',
    location: 'MPL1',
    commodity: 'Beefsteak',
    severity: 'Critical',
    availableSupply: 1_100,
    customers: [
      {
        id: 'C31', customerName: 'LOBLAW COMPANIES LTD', shipDate: '2026-03-23',
        skus: [
          { skuCode: 'RTBB1015', description: 'Beefsteak - 15lb 39ct Beef No1', orderedQty: 540, unitPrice: 23.20 },
          { skuCode: 'RTBB1023', description: 'Beefsteak - 15lb 25ct Beef No1', orderedQty: 180, unitPrice: 24.00 },
        ],
      },
      {
        id: 'C33', customerName: 'SOBEYS-ONTARIO', shipDate: '2026-03-24',
        skus: [
          { skuCode: 'RTBB1007', description: 'Beefsteak - 15lb 22ct Beef No1', orderedQty: 270, unitPrice: 40.00 },
          { skuCode: 'RTBB1023', description: 'Beefsteak - 15lb 25ct Beef No1', orderedQty:  90, unitPrice: 40.00 },
        ],
      },
      {
        id: 'C06', customerName: 'MEIJER INC', shipDate: '2026-03-26',
        skus: [
          { skuCode: 'RTBB1012', description: 'Beefsteak - 15lb 35ct Beef No1', orderedQty: 360, unitPrice: 16.85 },
          { skuCode: 'RTBB1010', description: 'Beefsteak - 15lb 32ct Beef No1', orderedQty: 270, unitPrice: 16.50 },
        ],
      },
    ],
  },
  {
    id: 'MPL6B-TOV',
    location: 'MPL6-B',
    commodity: 'TOV',
    severity: 'Critical',
    availableSupply: 800,
    customers: [
      {
        id: 'C01', customerName: 'METRO ONTARIO INC', shipDate: '2026-03-23',
        skus: [
          { skuCode: 'RTOV1132', description: '6x3lb TOV TS No1',  orderedQty: 600, unitPrice: 25.50 },
          { skuCode: 'RTOV1008', description: '11lb TOV No1',       orderedQty: 400, unitPrice: 22.00 },
        ],
      },
      {
        id: 'C84', customerName: 'WALMART (USA)', shipDate: '2026-03-25',
        skus: [
          { skuCode: 'RTOV1132', description: '6x3lb TOV TS No1',  orderedQty: 960, unitPrice: 19.50 },
          { skuCode: 'RTOV1133', description: '6x2lb TOV TS No1',  orderedQty: 480, unitPrice: 18.00 },
        ],
      },
      {
        id: 'C167', customerName: 'COSTCO US', shipDate: '2026-03-27',
        skus: [
          { skuCode: 'RTOV1200', description: 'TOV 5lb Club Pack No1', orderedQty: 960, unitPrice: 16.00 },
        ],
      },
    ],
  },
  {
    id: 'MPL8-Campari',
    location: 'MPL8',
    commodity: 'Campari',
    severity: 'High',
    availableSupply: 1_200,
    customers: [
      {
        id: 'C118', customerName: 'PUBLIX SUPERMARKETS', shipDate: '2026-03-24',
        skus: [
          { skuCode: 'RTCA1010', description: 'Campari - 8x2lb Camp OTV No1',    orderedQty: 480, unitPrice: 28.50 },
          { skuCode: 'RTCA1012', description: 'Campari - 12x1lb Camp OTV No1',   orderedQty: 240, unitPrice: 26.00 },
        ],
      },
      {
        id: 'C42', customerName: 'ALBERTSONS SHAWS MARKET', shipDate: '2026-03-25',
        skus: [
          { skuCode: 'RTCA1010', description: 'Campari - 8x2lb Camp OTV No1',    orderedQty: 360, unitPrice: 19.50 },
          { skuCode: 'RTCA1015', description: 'Campari - 16x1lb Camp OTV No1',   orderedQty: 240, unitPrice: 18.75 },
        ],
      },
      {
        id: 'C38', customerName: 'C&S WHOLESALE GROCERS INC', shipDate: '2026-03-26',
        skus: [
          { skuCode: 'RTCA1010', description: 'Campari - 8x2lb Camp OTV No1',    orderedQty: 480, unitPrice: 15.50 },
        ],
      },
    ],
  },
  {
    id: 'MPLW-Beefsteak',
    location: 'MPLW',
    commodity: 'Beefsteak',
    severity: 'Medium',
    availableSupply: 580,
    customers: [
      {
        id: 'C13', customerName: 'MEIJER INC', shipDate: '2026-03-23',
        skus: [
          { skuCode: 'RTBB1015', description: 'Beefsteak - 15lb 39ct Beef No1',  orderedQty: 270, unitPrice: 16.85 },
          { skuCode: 'RTBB1017', description: 'Beefsteak - 15lb 42ct Beef No1',  orderedQty: 180, unitPrice: 16.50 },
        ],
      },
      {
        id: 'C30', customerName: 'HY-VEE INC', shipDate: '2026-03-25',
        skus: [
          { skuCode: 'RTBB1007', description: 'Beefsteak - 15lb 22ct Beef No1',  orderedQty: 180, unitPrice: 22.00 },
          { skuCode: 'RTBB1010', description: 'Beefsteak - 15lb 32ct Beef No1',  orderedQty:  90, unitPrice: 20.50 },
        ],
      },
      {
        id: 'C107', customerName: 'WEGMANS FOOD MARKETS', shipDate: '2026-03-27',
        skus: [
          { skuCode: 'RTBB1007', description: 'Beefsteak - 15lb 22ct Beef No1',  orderedQty: 180, unitPrice: 25.00 },
        ],
      },
    ],
  },
]

// ── Missing POs per location (unrecieved inbound shipments) ───────────────────
const MOCK_MISSING_POS = {
  'MPL1': [
    { poNumber: 'PO-88234', vendor: 'Sunfresh Farms',     expectedQty: 480, deliveryDate: '2026-03-22', severity: 'Critical' },
    { poNumber: 'PO-88301', vendor: 'Heritage Growers',   expectedQty: 240, deliveryDate: '2026-03-23', severity: 'High'     },
    { poNumber: 'PO-88412', vendor: 'Sunfresh Farms',     expectedQty: 360, deliveryDate: '2026-03-24', severity: 'High'     },
  ],
  'MPL6-B': [
    { poNumber: 'PO-88190', vendor: 'Valley Fresh Growers', expectedQty: 600, deliveryDate: '2026-03-22', severity: 'Critical' },
    { poNumber: 'PO-88211', vendor: 'Sunrise Greenhouse',   expectedQty: 800, deliveryDate: '2026-03-23', severity: 'Critical' },
  ],
  'MPL8': [
    { poNumber: 'PO-88520', vendor: 'Carlo Farms',          expectedQty: 300, deliveryDate: '2026-03-23', severity: 'High' },
  ],
  'MPLW': [],
}

// ── Safety stock per alert (minimum buffer that must be maintained) ───────────
const MOCK_SAFETY_STOCK = {
  'MPL1-Beefsteak': 250,
  'MPL6B-TOV':      350,
  'MPL8-Campari':   300,
  'MPLW-Beefsteak': 150,
}

// ── Expected future inbounds per alert (to rebuild inventory) ─────────────────
const MOCK_INBOUND_SCHEDULE = {
  'MPL1-Beefsteak': [
    { date: '2026-03-25', vendor: 'Sunfresh Farms',   expectedQty: 600 },
    { date: '2026-03-27', vendor: 'Heritage Growers', expectedQty: 400 },
  ],
  'MPL6B-TOV': [
    { date: '2026-03-24', vendor: 'Sunrise Greenhouse',   expectedQty: 500 },
    { date: '2026-03-26', vendor: 'Valley Fresh Growers', expectedQty: 700 },
  ],
  'MPL8-Campari': [
    { date: '2026-03-25', vendor: 'Carlo Farms',    expectedQty: 400 },
    { date: '2026-03-27', vendor: 'Carlo Farms',    expectedQty: 350 },
  ],
  'MPLW-Beefsteak': [
    { date: '2026-03-24', vendor: 'Heritage Growers', expectedQty: 300 },
    { date: '2026-03-26', vendor: 'Sunfresh Farms',   expectedQty: 250 },
  ],
}

// ─────────────────────────────────────────────────────────────────────────────
// PACK SCHEDULE ENGINE — Mock output from Python logic
// Each row = one recommended pack run for an at-risk SKU
// Fields mirror the final_schedule DataFrame produced by the Python engine
// ─────────────────────────────────────────────────────────────────────────────
const MOCK_PACK_SCHEDULE = [
  {
    id: 'PS-001',
    skuCode: 'RTOV1132',
    description: '6x3lb TOV TS No1',
    commodity: 'TOV',
    location: 'MPL6-B',
    severity: 'Critical',
    packDate: '2026-03-23',
    shipDate: '2026-03-25',
    suggestedPackQty: 660,
    feasiblePackQty: 275,        // capped by raw material
    rawLbsRequired: 13500,
    availableLbs: 5610,
    rawConstrained: true,
    fillRatio: 0.42,
    // 7-day rolling projection (date, forecast, expected inbound, projected inventory after pack)
    projection: [
      { date: '2026-03-23', forecast: 600,  inbound:   0, projectedInventory:  480, packQty: 275 },
      { date: '2026-03-24', forecast:   0,  inbound: 300, projectedInventory:  755, packQty:   0 },
      { date: '2026-03-25', forecast: 960,  inbound:   0, projectedInventory: -205, packQty:   0 },
      { date: '2026-03-26', forecast:   0,  inbound:   0, projectedInventory: -205, packQty:   0 },
      { date: '2026-03-27', forecast: 960,  inbound: 700, projectedInventory: -465, packQty:   0 },
      { date: '2026-03-28', forecast:   0,  inbound:   0, projectedInventory: -465, packQty:   0 },
      { date: '2026-03-29', forecast:   0,  inbound:   0, projectedInventory: -465, packQty:   0 },
    ],
  },
  {
    id: 'PS-002',
    skuCode: 'RTCA1010',
    description: 'Campari 8x2lb OTV No1',
    commodity: 'Campari',
    location: 'MPL8',
    severity: 'Critical',
    packDate: '2026-03-23',
    shipDate: '2026-03-24',
    suggestedPackQty: 480,
    feasiblePackQty: 200,
    rawLbsRequired: 9366,
    availableLbs: 4000,
    rawConstrained: true,
    fillRatio: 0.43,
    projection: [
      { date: '2026-03-23', forecast:   0,  inbound:   0, projectedInventory:  200, packQty: 200 },
      { date: '2026-03-24', forecast: 480,  inbound:   0, projectedInventory: -280, packQty:   0 },
      { date: '2026-03-25', forecast: 360,  inbound: 150, projectedInventory: -490, packQty:   0 },
      { date: '2026-03-26', forecast: 480,  inbound:   0, projectedInventory: -970, packQty:   0 },
      { date: '2026-03-27', forecast:   0,  inbound:   0, projectedInventory: -970, packQty:   0 },
      { date: '2026-03-28', forecast:   0,  inbound:   0, projectedInventory: -970, packQty:   0 },
      { date: '2026-03-29', forecast:   0,  inbound:   0, projectedInventory: -970, packQty:   0 },
    ],
  },
  {
    id: 'PS-003',
    skuCode: 'RTBB1015',
    description: 'Beefsteak 15lb 39ct No1',
    commodity: 'Beefsteak',
    location: 'MPL1',
    severity: 'High',
    packDate: '2026-03-25',
    shipDate: '2026-03-26',
    suggestedPackQty: 350,
    feasiblePackQty: 350,        // fully feasible — raw material available
    rawLbsRequired: 6176,
    availableLbs: 7000,
    rawConstrained: false,
    fillRatio: 1.0,
    projection: [
      { date: '2026-03-23', forecast:   0,  inbound:   0, projectedInventory:  320, packQty:   0 },
      { date: '2026-03-24', forecast: 270,  inbound:   0, projectedInventory:   50, packQty:   0 },
      { date: '2026-03-25', forecast:   0,  inbound: 400, projectedInventory:  800, packQty: 350 },
      { date: '2026-03-26', forecast: 360,  inbound:   0, projectedInventory:  440, packQty:   0 },
      { date: '2026-03-27', forecast: 180,  inbound:   0, projectedInventory:  260, packQty:   0 },
      { date: '2026-03-28', forecast:   0,  inbound:   0, projectedInventory:  260, packQty:   0 },
      { date: '2026-03-29', forecast:   0,  inbound:   0, projectedInventory:  260, packQty:   0 },
    ],
  },
  {
    id: 'PS-004',
    skuCode: 'RTBB1023',
    description: 'Beefsteak 15lb 25ct No1',
    commodity: 'Beefsteak',
    location: 'MPL1',
    severity: 'Medium',
    packDate: '2026-03-24',
    shipDate: '2026-03-25',
    suggestedPackQty: 150,
    feasiblePackQty: 150,
    rawLbsRequired: 2647,
    availableLbs: 9000,
    rawConstrained: false,
    fillRatio: 1.0,
    projection: [
      { date: '2026-03-23', forecast:   0,  inbound:   0, projectedInventory:  150, packQty:   0 },
      { date: '2026-03-24', forecast: 180,  inbound:   0, projectedInventory:  120, packQty: 150 },
      { date: '2026-03-25', forecast:  90,  inbound: 200, projectedInventory:  230, packQty:   0 },
      { date: '2026-03-26', forecast:   0,  inbound:   0, projectedInventory:  230, packQty:   0 },
      { date: '2026-03-27', forecast:   0,  inbound:   0, projectedInventory:  230, packQty:   0 },
      { date: '2026-03-28', forecast:   0,  inbound:   0, projectedInventory:  230, packQty:   0 },
      { date: '2026-03-29', forecast:   0,  inbound:   0, projectedInventory:  230, packQty:   0 },
    ],
  },
]

// ── Allocation logic ───────────────────────────────────────────────────────────
function getTier(price) {
  if (price >= 22) return 'Tier 1'
  if (price >= 18) return 'Tier 2'
  return 'Tier 3'
}
function getCutRate(tier, flatRate) {
  if (tier === 'Tier 1') return 0
  if (tier === 'Tier 2') return Math.min(flatRate * 0.5, 1)
  return Math.min(flatRate * 2, 1)
}
function enrichAlert(alert) {
  const totalDemand = alert.customers
    .flatMap(c => c.skus)
    .reduce((s, sk) => s + sk.orderedQty, 0)
  const shortage    = Math.max(totalDemand - alert.availableSupply, 0)
  const flatRate    = totalDemand > 0 ? shortage / totalDemand : 0

  const customers = alert.customers.map(c => {
    const skus = c.skus.map(sk => {
      const tier        = getTier(sk.unitPrice)
      const cutRate     = getCutRate(tier, flatRate)
      const suggestedCut   = Math.round(sk.orderedQty * cutRate)
      const suggestedAlloc = sk.orderedQty - suggestedCut
      return { ...sk, tier, cutRate, suggestedCut, suggestedAlloc }
    })
    const custDemand = skus.reduce((s, sk) => s + sk.orderedQty, 0)
    const custAlloc  = skus.reduce((s, sk) => s + sk.suggestedAlloc, 0)
    const highestTier = skus.reduce((best, sk) => {
      const order = { 'Tier 1': 0, 'Tier 2': 1, 'Tier 3': 2 }
      return order[sk.tier] < order[best] ? sk.tier : best
    }, 'Tier 3')
    return { ...c, skus, custDemand, custAlloc, highestTier }
  })

  const flatRevenue = customers.flatMap(c => c.skus).reduce((s, sk) => {
    const flatAlloc = Math.round(sk.orderedQty * (1 - flatRate))
    return s + flatAlloc * sk.unitPrice
  }, 0)
  const tierRevenue = customers.flatMap(c => c.skus)
    .reduce((s, sk) => s + sk.suggestedAlloc * sk.unitPrice, 0)

  return {
    ...alert, totalDemand, shortage, flatRate,
    revenueFlat: Math.round(flatRevenue),
    revenueTier: Math.round(tierRevenue),
    revenueProtected: Math.round(tierRevenue - flatRevenue),
    customers,
  }
}
const ENRICHED_ALERTS = MOCK_NETWORK_ALERTS.map(enrichAlert)

// ── Helpers ────────────────────────────────────────────────────────────────────
const fmt = n =>
  n == null ? '—' : Number(n).toLocaleString('en-CA', { maximumFractionDigits: 0 })

const fmtDate = key => {
  if (!key) return '—'
  const s = String(key)
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
}

const SeverityBadge = ({ level }) => {
  const cls = {
    Critical: 'badge-critical', High: 'badge-high',
    Medium: 'badge-medium',     Low:  'badge-low',
  }
  return <span className={cls[level] ?? 'badge-low'}>{level}</span>
}

const Spinner = ({ sm }) => (
  <RefreshCw className={`${sm ? 'w-3 h-3' : 'w-4 h-4'} animate-spin text-gray-400`} />
)
const ErrorNote = ({ msg }) => (
  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
    <AlertTriangle className="w-3 h-3" /> {msg}
  </p>
)
const ForecastTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-medium">{fmt(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// PACK SCHEDULE ACTION CENTER
// ─────────────────────────────────────────────────────────────────────────────
function PackScheduleActionCenter() {
  const [approved, setApproved]     = useState({})   // { [id]: true }
  const [expanded, setExpanded]     = useState({})   // { [id]: true }
  const [filterSev, setFilterSev]   = useState('all')

  const toggleExpand = id => setExpanded(p => ({ ...p, [id]: !p[id] }))
  const approve      = id => setApproved(p => ({ ...p, [id]: true }))

  const sevOrder  = { Critical: 0, High: 1, Medium: 2, 'On Track': 3 }
  const displayed = MOCK_PACK_SCHEDULE
    .filter(r => filterSev === 'all' || r.severity === filterSev)
    .sort((a, b) => (sevOrder[a.severity] ?? 9) - (sevOrder[b.severity] ?? 9))

  const critCount = MOCK_PACK_SCHEDULE.filter(r => r.severity === 'Critical').length
  const highCount = MOCK_PACK_SCHEDULE.filter(r => r.severity === 'High').length

  const sevStyle = {
    Critical: { badge: 'bg-red-100 text-red-700',    border: 'border-red-300',    row: 'bg-red-50'     },
    High:     { badge: 'bg-orange-100 text-orange-700', border: 'border-orange-300', row: 'bg-orange-50' },
    Medium:   { badge: 'bg-yellow-100 text-yellow-700', border: 'border-yellow-300', row: 'bg-yellow-50' },
    'On Track':{ badge: 'bg-emerald-100 text-emerald-700', border: 'border-gray-200', row: '' },
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <Layers className="w-4 h-4 text-brand" />
            <h3 className="font-semibold text-gray-900 text-sm">Pack Schedule Action Center</h3>
            <span className="text-[10px] bg-brand/10 text-brand px-2 py-0.5 rounded-full font-semibold">
              7-Day Rolling Window
            </span>
          </div>
          <p className="text-xs text-gray-400">
            JIT pack recommendations — packing the day before shipment to prevent stockouts
          </p>
        </div>

        {/* Summary badges + filter */}
        <div className="flex items-center gap-2">
          {critCount > 0 && (
            <span className="text-xs bg-red-100 text-red-700 px-2.5 py-1 rounded-full font-semibold">
              {critCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-xs bg-orange-100 text-orange-700 px-2.5 py-1 rounded-full font-semibold">
              {highCount} High
            </span>
          )}
          <select
            value={filterSev}
            onChange={e => setFilterSev(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand/30"
          >
            <option value="all">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
          </select>
        </div>
      </div>

      {/* ── Legend ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 px-5 py-2 bg-gray-50 border-b border-gray-100 text-[10px] text-gray-500">
        <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-purple-400 inline-block"/>Demand</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-emerald-400 inline-block"/>Expected Inbound</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-blue-400 inline-block"/>Pack Run</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-red-300 inline-block"/>Projected Stockout</span>
      </div>

      {/* ── SKU Rows ────────────────────────────────────────────────────────── */}
      <div className="divide-y divide-gray-100">
        {displayed.map(run => {
          const sty        = sevStyle[run.severity] ?? sevStyle.Medium
          const isApproved = approved[run.id]
          const isExpanded = expanded[run.id]
          const rawShortPct = run.rawConstrained
            ? Math.round((1 - run.fillRatio) * 100)
            : 0

          return (
            <div key={run.id} className={`${isApproved ? 'opacity-60' : ''}`}>

              {/* ── Summary row ─────────────────────────────────────────────── */}
              <div
                className={`
                  grid grid-cols-[2fr_1fr_1fr_1fr_1fr_auto] gap-3 items-center
                  px-5 py-3 hover:bg-gray-50/70 transition-colors cursor-pointer text-xs
                `}
                onClick={() => toggleExpand(run.id)}
              >
                {/* SKU info */}
                <div className="flex items-center gap-2.5">
                  {isExpanded
                    ? <ChevronUp   className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    : <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${sty.badge}`}>
                        {run.severity}
                      </span>
                      <span className="font-mono text-[10px] text-gray-400">{run.skuCode}</span>
                    </div>
                    <p className="font-medium text-gray-800 mt-0.5 leading-tight">{run.description}</p>
                    <p className="text-gray-400 text-[10px]">{run.location} · {run.commodity}</p>
                  </div>
                </div>

                {/* Pack date */}
                <div>
                  <p className="text-gray-400 text-[10px] uppercase tracking-wide">Pack Date</p>
                  <p className="font-semibold text-gray-800">{run.packDate}</p>
                  <p className="text-gray-400 text-[10px]">ships {run.shipDate}</p>
                </div>

                {/* Suggested qty */}
                <div>
                  <p className="text-gray-400 text-[10px] uppercase tracking-wide">Suggested</p>
                  <p className="font-bold text-gray-900">{fmt(run.suggestedPackQty)} cs</p>
                </div>

                {/* Feasible qty */}
                <div>
                  <p className="text-gray-400 text-[10px] uppercase tracking-wide">Feasible</p>
                  <p className={`font-bold ${run.rawConstrained ? 'text-red-600' : 'text-emerald-600'}`}>
                    {fmt(run.feasiblePackQty)} cs
                  </p>
                  {run.rawConstrained && (
                    <p className="text-[10px] text-red-500">−{rawShortPct}% raw short</p>
                  )}
                </div>

                {/* Raw material bar */}
                <div>
                  <p className="text-gray-400 text-[10px] uppercase tracking-wide mb-1">Raw Material</p>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${run.rawConstrained ? 'bg-red-400' : 'bg-emerald-400'}`}
                      style={{ width: `${Math.min(Math.round(run.fillRatio * 100), 100)}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    {fmt(run.availableLbs)} / {fmt(run.rawLbsRequired)} lbs
                  </p>
                </div>

                {/* Action button */}
                <div onClick={e => e.stopPropagation()}>
                  {isApproved ? (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-600 font-semibold px-3 py-1.5 bg-emerald-50 rounded-lg border border-emerald-200">
                      <Check className="w-3 h-3" /> Approved
                    </span>
                  ) : (
                    <button
                      onClick={() => approve(run.id)}
                      className="flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-brand text-white hover:bg-brand-dark transition-colors whitespace-nowrap shadow-sm"
                    >
                      <Zap className="w-3 h-3" />
                      Approve Pack Run
                    </button>
                  )}
                </div>
              </div>

              {/* ── Expanded 7-day projection ────────────────────────────────── */}
              {isExpanded && (
                <div className="px-5 pb-4 bg-gray-50/60 border-t border-dashed border-gray-200">

                  {/* Raw material warning banner */}
                  {run.rawConstrained && (
                    <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 mt-3 mb-3 text-xs">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-red-700">Raw Material Constraint</p>
                        <p className="text-red-600">
                          Only <strong>{fmt(run.availableLbs)} lbs</strong> of {run.commodity} bulk available on {run.packDate} —
                          {' '}{fmt(run.rawLbsRequired)} lbs required.
                          Feasible pack is prorated to <strong>{fmt(run.feasiblePackQty)} cases</strong> ({Math.round(run.fillRatio * 100)}% of suggested).
                          Consider sourcing additional bulk or splitting across adjacent days.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* 7-day table */}
                  <div className="overflow-x-auto mt-3">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-400 uppercase tracking-wide text-[10px] border-b border-gray-200">
                          <th className="text-left py-2 pr-3 font-medium w-28">Date</th>
                          <th className="text-right py-2 px-3 font-medium">Demand Forecast</th>
                          <th className="text-right py-2 px-3 font-medium">Expected Inbound</th>
                          <th className="text-right py-2 px-3 font-medium">Pack Run</th>
                          <th className="text-right py-2 px-3 font-medium">End Inventory</th>
                          <th className="text-right py-2 pl-3 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {run.projection.map(day => {
                          const isStockout  = day.projectedInventory < 0
                          const isPackDay   = day.packQty > 0
                          const isShipDay   = day.date === run.shipDate
                          return (
                            <tr
                              key={day.date}
                              className={`
                                ${isStockout  ? 'bg-red-50'    : ''}
                                ${isPackDay   ? 'bg-blue-50/60': ''}
                              `}
                            >
                              <td className="py-2 pr-3 font-medium text-gray-700">
                                {day.date}
                                {isShipDay && (
                                  <span className="ml-1.5 text-[9px] bg-purple-100 text-purple-600 px-1 py-0.5 rounded font-semibold">SHIP</span>
                                )}
                              </td>
                              <td className="py-2 px-3 text-right">
                                {day.forecast > 0
                                  ? <span className="text-purple-600 font-semibold">−{fmt(day.forecast)}</span>
                                  : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="py-2 px-3 text-right">
                                {day.inbound > 0
                                  ? <span className="text-emerald-600 font-semibold">+{fmt(day.inbound)}</span>
                                  : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="py-2 px-3 text-right">
                                {day.packQty > 0
                                  ? (
                                    <span className="text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                      +{fmt(day.packQty)} pack
                                    </span>
                                  )
                                  : <span className="text-gray-300">—</span>}
                              </td>
                              <td className={`py-2 px-3 text-right font-bold ${isStockout ? 'text-red-600' : 'text-gray-800'}`}>
                                {isStockout && '⚠ '}
                                {fmt(Math.abs(day.projectedInventory))}
                                {isStockout && ' STOCKOUT'}
                              </td>
                              <td className="py-2 pl-3 text-right">
                                {isStockout
                                  ? <span className="text-[10px] font-semibold text-red-600 bg-red-100 px-1.5 py-0.5 rounded">At Risk</span>
                                  : isPackDay
                                    ? <span className="text-[10px] font-semibold text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">Pack Day</span>
                                    : <span className="text-[10px] text-gray-400">—</span>}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

            </div>
          )
        })}
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <div className="px-5 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
        <p className="text-[10px] text-gray-400">
          Projection logic: Opening Inventory + Expected Inbound − Demand Forecast · JIT: pack 1 day before ship ·
          Raw material pool shared across commodity
        </p>
        <p className="text-[10px] text-gray-400">
          {Object.keys(approved).length} of {MOCK_PACK_SCHEDULE.length} runs approved
        </p>
      </div>

    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// STEP 1 — Network Alert Card
// ─────────────────────────────────────────────────────────────────────────────
function NetworkAlertCard({ alert, selected, onClick, missingPos = [] }) {
  const [showPos, setShowPos] = useState(false)

  const severityColors = {
    Critical: {
      border: 'border-red-400',
      bg:     selected ? 'bg-red-50 ring-2 ring-red-400' : 'bg-white hover:bg-red-50',
      badge:  'bg-red-100 text-red-700',
      icon:   'text-red-500',
      bar:    'bg-red-500',
    },
    High: {
      border: 'border-orange-400',
      bg:     selected ? 'bg-orange-50 ring-2 ring-orange-400' : 'bg-white hover:bg-orange-50',
      badge:  'bg-orange-100 text-orange-700',
      icon:   'text-orange-500',
      bar:    'bg-orange-400',
    },
    Medium: {
      border: 'border-yellow-400',
      bg:     selected ? 'bg-yellow-50 ring-2 ring-yellow-400' : 'bg-white hover:bg-yellow-50',
      badge:  'bg-yellow-100 text-yellow-700',
      icon:   'text-yellow-500',
      bar:    'bg-yellow-400',
    },
  }
  const c = severityColors[alert.severity] ?? severityColors.Medium
  const fillPct = Math.round((alert.availableSupply / alert.totalDemand) * 100)

  return (
    <div className={`rounded-xl border-2 ${c.border} ${c.bg} shadow-sm transition-all duration-150`}>
      {/* Main clickable area */}
      <button onClick={onClick} className="w-full text-left p-4 cursor-pointer">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg bg-white shadow-sm border ${c.border}`}>
              <MapPin className={`w-4 h-4 ${c.icon}`} />
            </span>
            <div>
              <p className="text-sm font-bold text-gray-900 leading-tight">{alert.location}</p>
              <p className="text-xs text-gray-500">{alert.commodity}</p>
            </div>
          </div>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${c.badge}`}>
            {alert.severity}
          </span>
        </div>

        {/* Supply vs Demand */}
        <div className="space-y-1.5 mb-3">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Supply</span>
            <span className="font-medium text-gray-800">{fmt(alert.availableSupply)} cases</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div className={`h-2 rounded-full ${c.bar}`} style={{ width: `${Math.min(fillPct, 100)}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Demand</span>
            <span className="font-medium text-gray-800">{fmt(alert.totalDemand)} cases</span>
          </div>
        </div>

        {/* Gap and customer count */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400">Net gap</p>
            <p className="text-base font-bold text-red-600">−{fmt(alert.shortage)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">Customers</p>
            <p className="text-base font-bold text-gray-700">{alert.customers.length}</p>
          </div>
          <div className={`flex items-center gap-1 text-xs font-medium ${selected ? c.icon : 'text-gray-400'}`}>
            {selected ? <><Check className="w-3.5 h-3.5" /> Open</> : <><ChevronRight className="w-3.5 h-3.5" /> Drill in</>}
          </div>
        </div>
      </button>

      {/* Missing POs section */}
      {missingPos.length > 0 && (
        <div className="border-t border-black/10 px-4 pb-3">
          <button
            onClick={e => { e.stopPropagation(); setShowPos(v => !v) }}
            className="w-full flex items-center justify-between pt-2.5 text-xs group"
          >
            <span className="flex items-center gap-1.5 font-semibold text-red-600">
              <AlertTriangle className="w-3 h-3" />
              {missingPos.length} PO{missingPos.length > 1 ? 's' : ''} not received
              <span className="font-normal text-gray-400">
                · {fmt(missingPos.reduce((s, p) => s + p.expectedQty, 0))} cases missing
              </span>
            </span>
            {showPos
              ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
              : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
          </button>

          {showPos && (
            <div className="mt-2 space-y-1.5">
              {missingPos.map(po => (
                <div key={po.poNumber}
                  className="bg-white/80 border border-red-100 rounded-lg px-3 py-2 text-[11px]">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-mono font-semibold text-gray-700">{po.poNumber}</span>
                    <span className={`px-1.5 py-0.5 rounded-full font-semibold text-[10px] ${
                      po.severity === 'Critical' ? 'bg-red-100 text-red-700'
                      : po.severity === 'High' ? 'bg-orange-100 text-orange-700'
                      : 'bg-yellow-100 text-yellow-700'}`}>
                      {po.severity}
                    </span>
                  </div>
                  <p className="text-gray-600 truncate">{po.vendor}</p>
                  <div className="flex items-center justify-between mt-1 text-gray-500">
                    <span>Due: {po.deliveryDate}</span>
                    <span className="font-semibold text-red-600">{fmt(po.expectedQty)} cases</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// STEP 2 + 3 — Strategic Allocation Engine
// ─────────────────────────────────────────────────────────────────────────────
function AllocationEngine({ alert, finalAllocs, onAllocChange, onClose }) {
  const [expanded, setExpanded] = useState(new Set())

  const toggleExpand = id =>
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const getFinal = (custId, skuCode, suggested) =>
    finalAllocs?.[alert.id]?.[custId]?.[skuCode] ?? suggested

  const tierStyle = tier => ({
    'Tier 1': 'tier-1',
    'Tier 2': 'tier-2',
    'Tier 3': 'tier-3',
  }[tier] ?? 'text-gray-600')

  const tierBg = tier => ({
    'Tier 1': 'bg-emerald-50 border-emerald-200',
    'Tier 2': 'bg-amber-50 border-amber-200',
    'Tier 3': 'bg-red-50 border-red-200',
  }[tier] ?? '')

  // Revenue impact summary
  const actualRevenue = alert.customers.reduce((total, cust) =>
    total + cust.skus.reduce((s, sk) => {
      const alloc = getFinal(cust.id, sk.skuCode, sk.suggestedAlloc)
      return s + alloc * sk.unitPrice
    }, 0), 0)

  // Daily inventory / demand timeline
  const inbounds     = MOCK_INBOUND_SCHEDULE[alert.id] ?? []
  const safetyStock  = MOCK_SAFETY_STOCK[alert.id] ?? 0
  const timeline = useMemo(() => {
    const allDates = [
      ...alert.customers.map(c => c.shipDate),
      ...inbounds.map(i => i.date),
    ].filter(Boolean)
    const uniqueDates = [...new Set(allDates)].sort()
    let running = alert.availableSupply
    return uniqueDates.map(date => {
      const dayDemand  = alert.customers
        .filter(c => c.shipDate === date)
        .reduce((s, c) => s + c.custDemand, 0)
      const dayInbound = inbounds
        .filter(i => i.date === date)
        .reduce((s, i) => s + i.expectedQty, 0)
      const dayInboundVendors = inbounds.filter(i => i.date === date).map(i => i.vendor).join(', ')
      running = running + dayInbound - dayDemand
      const buffer = running - safetyStock
      return { date, demand: dayDemand, inbound: dayInbound, inboundVendors: dayInboundVendors, endInventory: running, buffer }
    })
  }, [alert, safetyStock])

  const [showTimeline, setShowTimeline] = useState(true)

  return (
    <div className="card border-2 border-brand/30 bg-gradient-to-br from-white to-green-50/30">
      {/* Engine Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-widest text-brand">
              Step 2 + 3 → Strategic Allocation Engine
            </span>
          </div>
          <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand" />
            {alert.location} — {alert.commodity} Shortage
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {alert.customers.length} customers serviced from this location ·
            Showing exact Finished SKUs per customer order
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Revenue impact */}
          <div className="text-right bg-white rounded-lg border border-gray-100 px-3 py-2 shadow-sm">
            <p className="text-[10px] uppercase tracking-wide text-gray-400">Revenue protected vs flat cut</p>
            <p className="text-lg font-bold text-emerald-600">
              +${fmt(alert.revenueProtected)}
            </p>
            <p className="text-[10px] text-gray-400">
              ${fmt(alert.revenueFlat)} → ${fmt(alert.revenueTier)} with tier model
            </p>
          </div>
          <button onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Shortage summary strip */}
      <div className="grid grid-cols-5 gap-3 mb-5">
        {[
          { label: 'Available Supply', val: `${fmt(alert.availableSupply)} cases`, color: 'text-blue-600' },
          { label: 'Total Demand',     val: `${fmt(alert.totalDemand)} cases`,     color: 'text-purple-600' },
          { label: 'Shortage',         val: `−${fmt(alert.shortage)} cases`,        color: 'text-red-600' },
          { label: 'Safety Stock',     val: `${fmt(safetyStock)} cases`,            color: 'text-orange-600' },
          { label: 'Flat Cut Rate',    val: `${(alert.flatRate * 100).toFixed(1)}%`, color: 'text-amber-600' },
        ].map(m => (
          <div key={m.label} className="bg-white rounded-lg border border-gray-100 px-3 py-2 text-center shadow-sm">
            <p className="text-[10px] uppercase tracking-wide text-gray-400 mb-0.5">{m.label}</p>
            <p className={`text-sm font-bold ${m.color}`}>{m.val}</p>
          </div>
        ))}
      </div>

      {/* Daily Inventory / Demand Timeline */}
      {timeline.length > 0 && (
        <div className="mb-5 rounded-lg border border-gray-200 overflow-hidden">
          <button
            className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-200 hover:bg-gray-100 transition-colors"
            onClick={() => setShowTimeline(v => !v)}
          >
            <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-500">
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              Future Demand &amp; Inventory Outlook
            </span>
            {showTimeline ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </button>

          {showTimeline && (
            <div className="overflow-x-auto bg-white">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 text-gray-400 uppercase tracking-wide text-[10px]">
                    <th className="text-left px-4 py-2 font-medium">Date</th>
                    <th className="text-right px-3 py-2 font-medium">Expected Inbound</th>
                    <th className="text-left px-3 py-2 font-medium">Vendor</th>
                    <th className="text-right px-3 py-2 font-medium">Orders Shipping</th>
                    <th className="text-right px-3 py-2 font-medium">End-of-Day Inventory</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {/* Today's opening balance row */}
                  <tr className="bg-blue-50/50">
                    <td className="px-4 py-2 font-semibold text-blue-700">Today (opening)</td>
                    <td className="px-3 py-2 text-right text-gray-300">—</td>
                    <td className="px-3 py-2 text-gray-400">—</td>
                    <td className="px-3 py-2 text-right text-gray-300">—</td>
                    <td className="px-3 py-2 text-right font-bold text-blue-700">{fmt(alert.availableSupply)} cases</td>
                  </tr>
                  {timeline.map(row => {
                    const isStockout      = row.endInventory < 0
                    const isBelowSafety   = row.endInventory >= 0 && row.buffer < 0
                    const isLowBuffer     = row.buffer >= 0 && row.buffer < safetyStock * 0.5
                    const rowBg = isStockout ? 'bg-red-50' : isBelowSafety ? 'bg-orange-50' : isLowBuffer ? 'bg-amber-50' : 'hover:bg-gray-50'
                    return (
                      <tr key={row.date} className={rowBg}>
                        <td className="px-4 py-2 font-medium text-gray-700">{row.date}</td>
                        <td className="px-3 py-2 text-right">
                          {row.inbound > 0
                            ? <span className="text-emerald-600 font-semibold">+{fmt(row.inbound)}</span>
                            : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-3 py-2 text-gray-500 text-[11px]">
                          {row.inboundVendors || '—'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {row.demand > 0
                            ? <span className="text-purple-600 font-semibold">−{fmt(row.demand)}</span>
                            : <span className="text-gray-300">—</span>}
                        </td>
                        <td className={`px-3 py-2 text-right font-bold ${
                          isStockout ? 'text-red-600' : isBelowSafety ? 'text-orange-600' : 'text-gray-800'
                        }`}>
                          {isStockout && '⚠ '}
                          {fmt(Math.abs(row.endInventory))} cases
                          {isStockout && ' STOCKOUT'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              {/* Legend */}
              <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-100 bg-gray-50 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-100 inline-block"/>Stockout (inventory &lt; 0)</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-100 inline-block"/>Below safety stock</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-100 inline-block"/>Low buffer (&lt; 50% safety stock)</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-white border border-gray-200 inline-block"/>Healthy</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Customer + SKU table */}
      <div className="space-y-2">
        {alert.customers.map((cust, ci) => {
          const isOpen       = expanded.has(cust.id)
          const custFinalQty = cust.skus.reduce((s, sk) =>
            s + getFinal(cust.id, sk.skuCode, sk.suggestedAlloc), 0)
          const custFillPct  = cust.custDemand > 0
            ? Math.round(custFinalQty / cust.custDemand * 100) : 0

          // Urgency label based on ship date
          const today = new Date('2026-03-22')
          const ship  = cust.shipDate ? new Date(cust.shipDate) : null
          const daysOut = ship ? Math.round((ship - today) / 86400000) : null
          const urgencyLabel = daysOut === null ? null
            : daysOut === 0 ? { text: 'Ships today', cls: 'bg-red-100 text-red-700' }
            : daysOut === 1 ? { text: 'Ships tomorrow', cls: 'bg-orange-100 text-orange-700' }
            : daysOut <= 3  ? { text: `Ships in ${daysOut}d`, cls: 'bg-amber-100 text-amber-700' }
            : { text: `Ships in ${daysOut}d`, cls: 'bg-gray-100 text-gray-500' }

          return (
            <div key={cust.id}
              className={`rounded-lg border ${tierBg(cust.highestTier)} overflow-hidden`}>

              {/* Customer summary row */}
              <button
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-black/5 transition-colors"
                onClick={() => toggleExpand(cust.id)}
              >
                <span className="text-gray-400">
                  {isOpen
                    ? <ChevronDown className="w-4 h-4" />
                    : <ChevronRight className="w-4 h-4" />}
                </span>

                {/* Step indicator */}
                <span className="text-[10px] font-bold text-gray-400 w-4">{ci + 1}</span>

                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-900">{cust.customerName}</p>
                    {urgencyLabel && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${urgencyLabel.cls}`}>
                        {urgencyLabel.text}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-400">
                    {cust.skus.length} SKUs ordered
                    {cust.shipDate && <span className="ml-1">· Ship: {cust.shipDate}</span>}
                  </p>
                </div>

                <span className={`text-xs font-semibold ${tierStyle(cust.highestTier)} min-w-[80px]`}>
                  {cust.highestTier}
                </span>

                <div className="text-right min-w-[80px]">
                  <p className="text-xs text-gray-500">Ordered</p>
                  <p className="text-sm font-bold text-gray-800">{fmt(cust.custDemand)}</p>
                </div>

                <div className="text-right min-w-[80px]">
                  <p className="text-xs text-gray-500">Allocated</p>
                  <p className={`text-sm font-bold ${
                    custFillPct >= 90 ? 'text-emerald-600'
                    : custFillPct >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                    {fmt(custFinalQty)}
                  </p>
                </div>

                <div className="text-right min-w-[54px]">
                  <p className="text-xs text-gray-500">Fill</p>
                  <p className={`text-sm font-bold ${
                    custFillPct >= 90 ? 'text-emerald-600'
                    : custFillPct >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                    {custFillPct}%
                  </p>
                </div>
              </button>

              {/* SKU-level rows (Step 3) */}
              {isOpen && (
                <div className="border-t border-black/5 bg-white/60">
                  <div className="px-4 py-2 bg-gray-50/80 border-b border-gray-100">
                    <p className="text-[10px] uppercase tracking-widest font-bold text-gray-400">
                      Step 3 · Execution Level — Finished SKU Detail
                    </p>
                  </div>

                  {/* SKU table header */}
                  <div className="grid grid-cols-[2fr_1.2fr_1fr_1fr_1fr_1.2fr_0.8fr] gap-2
                    px-4 py-2 text-[10px] uppercase tracking-wide text-gray-400 font-medium
                    border-b border-gray-100">
                    <span>Finished SKU</span>
                    <span className="text-right">$/case</span>
                    <span className="text-right">Tier</span>
                    <span className="text-right">Ordered</span>
                    <span className="text-right">Suggested Cut</span>
                    <span className="text-right">Final Allocation</span>
                    <span className="text-right">Fill %</span>
                  </div>

                  {cust.skus.map(sk => {
                    const finalVal    = getFinal(cust.id, sk.skuCode, sk.suggestedAlloc)
                    const fillPct     = sk.orderedQty > 0
                      ? Math.round(finalVal / sk.orderedQty * 100) : 0
                    const isEdited    = finalVal !== sk.suggestedAlloc

                    return (
                      <div key={sk.skuCode}
                        className="grid grid-cols-[2fr_1.2fr_1fr_1fr_1fr_1.2fr_0.8fr] gap-2
                          items-center px-4 py-2.5 border-b border-gray-50
                          hover:bg-gray-50/60 transition-colors text-xs">

                        {/* SKU description */}
                        <div>
                          <p className="font-mono text-[10px] text-gray-400">{sk.skuCode}</p>
                          <p className="font-medium text-gray-800 leading-tight">{sk.description}</p>
                        </div>

                        {/* Unit price */}
                        <p className="text-right font-mono font-semibold text-gray-700">
                          ${sk.unitPrice.toFixed(2)}
                        </p>

                        {/* Tier */}
                        <p className={`text-right font-semibold text-[11px] ${tierStyle(sk.tier)}`}>
                          {sk.tier}
                        </p>

                        {/* Ordered */}
                        <p className="text-right text-gray-600">{fmt(sk.orderedQty)}</p>

                        {/* Suggested Cut */}
                        <p className="text-right text-red-500 font-medium">
                          {sk.suggestedCut > 0 ? `−${fmt(sk.suggestedCut)}` : '—'}
                        </p>

                        {/* Editable Final Allocation */}
                        <div className="flex items-center justify-end gap-1">
                          {isEdited && (
                            <span className="text-[9px] text-amber-500 font-bold">edited</span>
                          )}
                          <input
                            type="number"
                            min={0}
                            max={sk.orderedQty}
                            value={finalVal}
                            onChange={e =>
                              onAllocChange(alert.id, cust.id, sk.skuCode,
                                Math.min(Math.max(0, Number(e.target.value)), sk.orderedQty))
                            }
                            className={`
                              w-20 text-right text-sm font-bold rounded-lg px-2 py-1 border
                              focus:outline-none focus:ring-2 focus:ring-brand focus:ring-opacity-30
                              ${isEdited
                                ? 'border-amber-300 bg-amber-50 text-amber-700'
                                : 'border-gray-200 bg-white text-gray-800'}
                            `}
                          />
                        </div>

                        {/* Fill % */}
                        <p className={`text-right font-bold ${
                          fillPct >= 90 ? 'text-emerald-600'
                          : fillPct >= 60 ? 'text-amber-500' : 'text-red-500'}`}>
                          {fillPct}%
                        </p>
                      </div>
                    )
                  })}

                  {/* Customer subtotal */}
                  <div className="grid grid-cols-[2fr_1.2fr_1fr_1fr_1fr_1.2fr_0.8fr] gap-2
                    items-center px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-600
                    border-t border-gray-200">
                    <span className="text-gray-700">Customer Total</span>
                    <span />
                    <span />
                    <span className="text-right">{fmt(cust.custDemand)}</span>
                    <span className="text-right text-red-500">
                      −{fmt(cust.skus.reduce((s, sk) => s + sk.suggestedCut, 0))}
                    </span>
                    <span className={`text-right ${
                      custFillPct >= 90 ? 'text-emerald-600'
                      : custFillPct >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                      {fmt(custFinalQty)} cases
                    </span>
                    <span className={`text-right ${
                      custFillPct >= 90 ? 'text-emerald-600'
                      : custFillPct >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                      {custFillPct}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Network-level total */}
      <div className="mt-4 flex items-center justify-between px-4 py-3
        rounded-xl bg-gray-900 text-white text-xs">
        <span className="font-medium text-gray-300">Network Total — {alert.location} · {alert.commodity}</span>
        <div className="flex items-center gap-8">
          <div className="text-right">
            <p className="text-gray-400 text-[10px]">Total Ordered</p>
            <p className="font-bold">{fmt(alert.totalDemand)} cases</p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-[10px]">Tier Allocation</p>
            <p className="font-bold text-emerald-400">{fmt(alert.customers.reduce((s, c) =>
              s + c.skus.reduce((s2, sk) => s2 + getFinal(c.id, sk.skuCode, sk.suggestedAlloc), 0), 0))} cases</p>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-[10px]">Revenue Protected</p>
            <p className="font-bold text-emerald-400">+${fmt(alert.revenueProtected)}</p>
          </div>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand text-white text-xs font-medium hover:bg-brand-dark transition-colors">
            <Check className="w-3.5 h-3.5" /> Confirm Allocation
          </button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter Bar
// ─────────────────────────────────────────────────────────────────────────────
function FilterBar({ options, filters, onChange, onReset }) {
  const hasActive = filters.commodity !== 'all' || filters.locationCode !== 'all'
  return (
    <div className="bg-white border-b border-gray-100 px-6 py-2.5 flex items-center gap-3 flex-wrap shadow-sm">
      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
        <Filter className="w-3.5 h-3.5" /> Filters
      </div>
      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-500">Commodity</label>
        <select value={filters.commodity} onChange={e => onChange('commodity', e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:ring-opacity-30 cursor-pointer">
          <option value="all">All Commodities</option>
          {(options.commodities ?? []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-500">Location</label>
        <select value={filters.locationCode} onChange={e => onChange('locationCode', e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:ring-opacity-30 cursor-pointer">
          <option value="all">All Locations</option>
          {(options.locations ?? []).map(l => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-1.5">
        <Calendar className="w-3.5 h-3.5 text-gray-400" />
        <label className="text-xs text-gray-500">Snapshot Date</label>
        <select value={filters.dateKey} onChange={e => onChange('dateKey', e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:ring-opacity-30 cursor-pointer">
          <option value="latest">Latest</option>
          {options.inventory_dates?.map(d => <option key={d} value={d}>{fmtDate(d)}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-500">Exceptions Date</label>
        <select value={filters.deliveryDate} onChange={e => onChange('deliveryDate', e.target.value)}
          className="text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:ring-opacity-30 cursor-pointer">
          <option value="all">Latest (default)</option>
          {options.delivery_dates?.map(d => <option key={d} value={d}>{fmtDate(d)}</option>)}
        </select>
      </div>
      {hasActive && (
        <button onClick={onReset}
          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 border border-red-200 rounded-lg px-2 py-1.5 hover:bg-red-50 transition-colors">
          <X className="w-3 h-3" /> Reset
        </button>
      )}
      {hasActive && (
        <span className="text-xs bg-brand text-white px-2 py-0.5 rounded-full font-medium">
          Filtered
        </span>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main App
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {

  // ── Filter state ─────────────────────────────────────────────────────────
  const [filterOptions, setFilterOptions] = useState({
    commodities: [], locations: [], inventory_dates: [], delivery_dates: [],
    shortage_dates: [], skus: [],
  })
  const [filters, setFilters] = useState({
    commodity: 'all', locationCode: 'all', dateKey: 'latest', deliveryDate: 'all',
  })
  const [searchText, setSearchText] = useState('')

  // ── Data state ────────────────────────────────────────────────────────────
  const [kpis,           setKpis]           = useState(null)
  const [exceptions,     setExceptions]     = useState([])
  const [forecast,       setForecast]       = useState([])
  const [riskTrace,      setRiskTrace]      = useState([])

  // ── Drill-down state ──────────────────────────────────────────────────────
  const [selectedAlertId, setSelectedAlertId]   = useState(null)
  const [finalAllocs,     setFinalAllocs]         = useState({})
  const selectedAlert = useMemo(
    () => ENRICHED_ALERTS.find(a => a.id === selectedAlertId) ?? null,
    [selectedAlertId]
  )
  const handleAllocChange = (alertId, custId, skuCode, value) =>
    setFinalAllocs(prev => ({
      ...prev,
      [alertId]: { ...prev[alertId], [custId]: { ...prev[alertId]?.[custId], [skuCode]: value } },
    }))

  const [loadingKpis, setLoadingKpis] = useState(false)
  const [loadingExc,  setLoadingExc]  = useState(false)
  const [loadingFc,   setLoadingFc]   = useState(false)
  const [loadingRisk, setLoadingRisk] = useState(false)

  const [errKpis,  setErrKpis]  = useState(null)
  const [errExc,   setErrExc]   = useState(null)
  const [errFc,    setErrFc]    = useState(null)
  const [errRisk,  setErrRisk]  = useState(null)

  const [apiConnected,  setApiConnected]  = useState(null)
  const [lastRefreshed, setLastRefreshed] = useState(null)
  const [excCollapsed,  setExcCollapsed]  = useState(false)
  const [riskCollapsed, setRiskCollapsed] = useState(false)
  const [allocSkuKey,   setAllocSkuKey]   = useState('auto')

  // AI state
  const [geminiKey,    setGeminiKey]    = useState('')
  const [aiOutput,     setAiOutput]     = useState('')
  const [aiLoading,    setAiLoading]    = useState(false)
  const [aiError,      setAiError]      = useState(null)
  const [aiMode,       setAiMode]       = useState(null)
  const [showKeyInput, setShowKeyInput] = useState(false)

  // ── Page navigation ───────────────────────────────────────────────────────
  const [activePage,          setActivePage]          = useState('dashboard')
  const [allocPageSelectedId, setAllocPageSelectedId] = useState(ENRICHED_ALERTS[0]?.id ?? null)
  const allocSelectedAlert = useMemo(
    () => ENRICHED_ALERTS.find(a => a.id === allocPageSelectedId) ?? null,
    [allocPageSelectedId]
  )

  // ── Filter helpers ────────────────────────────────────────────────────────
  const filterParams = useMemo(() => {
    const p = {}
    if (filters.commodity    !== 'all')    p.commodity     = filters.commodity
    if (filters.locationCode !== 'all')    p.location_code = filters.locationCode
    if (filters.dateKey      !== 'latest') p.date_key      = filters.dateKey
    if (filters.deliveryDate !== 'all')    p.delivery_date = filters.deliveryDate
    return p
  }, [filters])

  const handleFilterChange = (key, val) => setFilters(prev => ({ ...prev, [key]: val }))
  const resetFilters = () =>
    setFilters({ commodity: 'all', locationCode: 'all', dateKey: 'latest', deliveryDate: 'all' })

  // ── Fetch ─────────────────────────────────────────────────────────────────
  const fetchFilters = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/filters`)
      setFilterOptions(data); setApiConnected(true)
    } catch { setApiConnected(false) }
  }, [])

  const fetchKpis = useCallback(async (params) => {
    setLoadingKpis(true); setErrKpis(null)
    try { const { data } = await axios.get(`${API}/kpis`, { params }); setKpis(data) }
    catch (e) { setErrKpis(e.message) }
    finally { setLoadingKpis(false) }
  }, [])

  const fetchExceptions = useCallback(async (params) => {
    setLoadingExc(true); setErrExc(null)
    try { const { data } = await axios.get(`${API}/exceptions`, { params }); if (Array.isArray(data)) setExceptions(data) }
    catch (e) { setErrExc(e.message) }
    finally { setLoadingExc(false) }
  }, [])

  const fetchForecast = useCallback(async (params) => {
    setLoadingFc(true); setErrFc(null)
    try { const { data } = await axios.get(`${API}/forecast`, { params }); if (Array.isArray(data)) setForecast(data) }
    catch (e) { setErrFc(e.message) }
    finally { setLoadingFc(false) }
  }, [])

  const fetchRiskTrace = useCallback(async (params) => {
    setLoadingRisk(true); setErrRisk(null)
    try { const { data } = await axios.get(`${API}/risk-trace`, { params }); if (Array.isArray(data)) setRiskTrace(data) }
    catch (e) { setErrRisk(e.message) }
    finally { setLoadingRisk(false) }
  }, [])


  useEffect(() => { fetchFilters() }, [fetchFilters])
  useEffect(() => {
    const p = filterParams
    const dim = { commodity: p.commodity, location_code: p.location_code }
    fetchKpis(p); fetchExceptions(p); fetchForecast(dim); fetchRiskTrace(dim)
    setAllocSkuKey('auto')
    setLastRefreshed(new Date())
  }, [filterParams, fetchKpis, fetchExceptions, fetchForecast, fetchRiskTrace])

  const refreshAll = useCallback(() => {
    fetchFilters()
    const p = filterParams
    const dim = { commodity: p.commodity, location_code: p.location_code }
    fetchKpis(p); fetchExceptions(p); fetchForecast(dim); fetchRiskTrace(dim)
    setLastRefreshed(new Date())
  }, [filterParams, fetchFilters, fetchKpis, fetchExceptions, fetchForecast, fetchRiskTrace])

  // ── Client-side search ────────────────────────────────────────────────────
  const filteredExceptions = useMemo(() => {
    if (!searchText.trim()) return exceptions
    const q = searchText.toLowerCase()
    return exceptions.filter(e =>
      e.PONumber?.toLowerCase().includes(q) || e.VendorName?.toLowerCase().includes(q) ||
      e.LocationCode?.toLowerCase().includes(q) || e.Commodities?.toLowerCase().includes(q)
    )
  }, [exceptions, searchText])

  // ── Gemini AI ─────────────────────────────────────────────────────────────
  const netPositive      = (kpis?.net_position ?? 0) >= 0
  const criticalCount    = filteredExceptions.filter(e => e.Severity === 'Critical').length
  const totalMissing     = filteredExceptions.reduce((s, e) => s + (e.Shortage_Variance ?? 0), 0)
  const totalRevAtRisk   = riskTrace.reduce((s, r) => s + (r.Revenue_At_Risk ?? 0), 0)
  const riskVendors      = [...new Set(riskTrace.map(r => r.VendorName))].length
  const riskCustomers    = [...new Set(riskTrace.map(r => r.CustomerName))].length

  const buildContext = () => {
    const activeFilters = [
      filters.commodity    !== 'all' ? `Commodity: ${filters.commodity}`   : null,
      filters.locationCode !== 'all' ? `Location: ${filters.locationCode}` : null,
    ].filter(Boolean).join(', ') || 'None (network-wide)'
    const top5 = filteredExceptions.slice(0, 5)
      .map(e => `${e.PONumber} | ${e.VendorName} | ${e.LocationCode} | ${e.Shortage_Variance} cases (${e.Severity})`)
      .join('\n')
    return `
NETWORK PLANNING CONTROL TOWER — LIVE SNAPSHOT
Active Filters: ${activeFilters}
KPIs (${fmtDate(kpis?.as_of_date)}):
  Supply: ${fmt(kpis?.total_supply)} | Demand: ${fmt(kpis?.total_demand)} | Net: ${fmt(kpis?.net_position)}
  Shortages: ${kpis?.shortage_count ?? 0} | Inbound Fill: ${kpis?.inbound_fill_rate_pct ?? 0}%
  Peak shortage date: ${fmtDate(kpis?.peak_shortage_date)}

TOP EXCEPTIONS: ${filteredExceptions.length} POs | ${fmt(totalMissing)} cases missing
${top5}

NETWORK ALERTS (mock drill-down):
${ENRICHED_ALERTS.map(a =>
  `${a.location} ${a.commodity}: −${fmt(a.shortage)} cases | ${a.customers.length} customers | $${fmt(a.revenueProtected)} revenue protected`
).join('\n')}

VENDOR RISK TRACE: ${riskVendors} vendors → ${riskCustomers} customers | $${fmt(totalRevAtRisk)} at risk`
  }

  const callGemini = async (mode) => {
    if (!geminiKey.trim()) { setShowKeyInput(true); return }
    setAiLoading(true); setAiError(null); setAiOutput(''); setAiMode(mode)
    const ctx    = buildContext()
    const prompt = mode === 'plan'
      ? `You are a senior supply-chain analyst at Mastronardi Produce. Based on the data below, write a concise morning action plan (bullet points, max 200 words) for the Category Manager. Prioritise the most critical network alerts and recommend which customer tiers to protect first.\n\n${ctx}`
      : `You are a supply-chain communication specialist. Based on the data below, draft a professional email (subject + body, max 150 words) from the Category Manager to the procurement team requesting urgent follow-up on the top missing inbound shipments.\n\n${ctx}`
    try {
      const res = await fetch(`${GEMINI_ENDPOINT}?key=${geminiKey}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.4, maxOutputTokens: 512 },
        }),
      })
      if (!res.ok) throw new Error(`Gemini ${res.status}: ${res.statusText}`)
      const json = await res.json()
      setAiOutput(json?.candidates?.[0]?.content?.parts?.[0]?.text ?? '')
    } catch (e) { setAiError(e.message) }
    finally { setAiLoading(false) }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <p className="text-sm text-gray-600 text-center max-w-sm">
        This link was shared for a 24-hour demo window only. Access to the full dashboard is restricted and will be taken down after that window.
      </p>
    </div>
  )
}

function _AppFull() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* HEADER */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🍅</span>
            <div>
              <h1 className="text-base font-bold text-gray-900 leading-tight">
                Network Planning Control Tower
              </h1>
              <p className="text-xs text-gray-500">Mastronardi Produce — Category Manager Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-xs">
              {apiConnected === null ? (
                <><Spinner sm /><span className="text-gray-400">Connecting…</span></>
              ) : apiConnected ? (
                <><Wifi className="w-3.5 h-3.5 text-green-500" /><span className="text-green-600 font-medium">Live</span></>
              ) : (
                <><WifiOff className="w-3.5 h-3.5 text-red-500" /><span className="text-red-600 font-medium">Offline</span></>
              )}
            </div>
            {lastRefreshed && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />{lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <button onClick={refreshAll} className="btn-outline py-1.5">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </button>
          </div>
        </div>
      </header>

      {/* FILTER BAR */}
      <FilterBar options={filterOptions} filters={filters}
        onChange={handleFilterChange} onReset={resetFilters} />

      <main className="max-w-screen-2xl mx-auto px-6 py-6 space-y-6 flex-1 w-full">

        {/* ── STEP 1: NETWORK SHORTAGE ALERTS ────────────────────────────── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-brand">Step 1</span>
                  <ArrowRight className="w-3 h-3 text-gray-300" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Macro Alert</span>
                </div>
                <h2 className="font-semibold text-gray-900 flex items-center gap-2 mt-0.5">
                  <Zap className="w-4 h-4 text-amber-500" />
                  Network Shortage Alerts
                  <span className="text-xs font-normal text-gray-400">— Location × Commodity level</span>
                </h2>
              </div>
              <p className="text-xs text-gray-400">Click any alert to open the Allocation Engine ↓</p>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {ENRICHED_ALERTS.map(alert => (
                <NetworkAlertCard
                  key={alert.id}
                  alert={alert}
                  selected={allocPageSelectedId === alert.id}
                  onClick={() =>
                    setAllocPageSelectedId(prev => prev === alert.id ? null : alert.id)
                  }
                  missingPos={MOCK_MISSING_POS[alert.location] ?? []}
                />
              ))}
            </div>
          </section>

          {/* ── STEP 2+3: ALLOCATION ENGINE ─────────────────────────────────── */}
          {allocSelectedAlert && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-bold uppercase tracking-widest text-brand">Step 2 + 3</span>
                <ArrowRight className="w-3 h-3 text-gray-300" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                  Affected Customers — Finished SKU Execution
                </span>
              </div>
              <AllocationEngine
                alert={allocSelectedAlert}
                finalAllocs={finalAllocs}
                onAllocChange={handleAllocChange}
                onClose={() => setAllocPageSelectedId(null)}
              />
            </section>
          )}

          {/* ── STEP 4: PACK SCHEDULE ACTION CENTER ─────────────────────────── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-brand">Step 4</span>
                  <ArrowRight className="w-3 h-3 text-gray-300" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Proactive Prevention</span>
                </div>
                <h2 className="font-semibold text-gray-900 flex items-center gap-2 mt-0.5">
                  <Layers className="w-4 h-4 text-brand" />
                  Pack Schedule Action Center
                  <span className="text-xs font-normal text-gray-400">— Prevent tomorrow's shortage today</span>
                </h2>
              </div>
            </div>
            <PackScheduleActionCenter />
          </section>


      </main>

      <footer className="text-center text-xs text-gray-300 py-4 border-t border-gray-100">
        Network Planning Control Tower · Mastronardi Produce · v3.0 — Drill-down Story Flow
      </footer>
    </div>
  )
}

// ── Small reusable components ──────────────────────────────────────────────────
function KpiCard({ icon, label, value, sub, accent, badge }) {
  const border = {
    blue: 'border-l-blue-500 bg-blue-50', purple: 'border-l-purple-500 bg-purple-50',
    green: 'border-l-emerald-500 bg-emerald-50', amber: 'border-l-amber-500 bg-amber-50',
    red: 'border-l-red-500 bg-red-50',
  }
  const text = {
    blue: 'text-blue-700', purple: 'text-purple-700', green: 'text-emerald-700',
    amber: 'text-amber-700', red: 'text-red-700',
  }
  return (
    <div className={`card border-l-4 ${border[accent] ?? border.blue} !p-4`}>
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 bg-white rounded-lg shadow-sm">{icon}</div>
        {badge && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
            badge.color === 'amber' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
            {badge.text}
          </span>
        )}
      </div>
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-1">{label}</p>
      {value == null
        ? <div className="h-7 w-20 bg-gray-200 animate-pulse rounded" />
        : <p className={`text-2xl font-bold ${text[accent] ?? text.blue}`}>{value}</p>}
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  )
}

function Metric({ label, val, color }) {
  return (
    <div>
      <p className="text-gray-400">{label}</p>
      <p className={`font-semibold ${color}`}>{val}</p>
    </div>
  )
}
