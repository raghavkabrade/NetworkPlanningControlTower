"""
generate_demo_data.py
=====================
Writes synthetic star-schema CSV files to data/curated/ that reproduce
numbers matching the original demo UI.

After running this script, run run_all.py to regenerate all Intermediate files.

Target alerts:
  MPL1   / Beefsteak : Supply=400,   Demand=1,710  → Shortage=1,310  Critical (77%)
  MPL6-B / TOV       : Supply=800,   Demand=3,400  → Shortage=2,600  Critical (76%)
  MPL8   / Campari   : Supply=1,200, Demand=1,800  → Shortage=600    High     (33%)
  MPLW   / Beefsteak : Supply=700,   Demand=900    → Shortage=200    Medium   (22%)
"""

import os
import pandas as pd
from pathlib import Path

CURATED = Path(__file__).resolve().parents[2] / "data" / "curated"
CURATED.mkdir(parents=True, exist_ok=True)

SNAPSHOT = 20260322   # latest inventory date (integer YYYYMMDD)

# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION TABLES
# ─────────────────────────────────────────────────────────────────────────────

DIM_PRODUCT = [
    # Beefsteak
    (1,  "RTBB1007", "FTBB1007", "Beefsteak - 15lb 22ct Beef No1",      "Beefsteak"),
    (2,  "RTBB1010", "FTBB1010", "Beefsteak - 15lb 32ct Beef No1",      "Beefsteak"),
    (3,  "RTBB1012", "FTBB1012", "Beefsteak - 15lb 35ct Beef No1",      "Beefsteak"),
    (4,  "RTBB1015", "FTBB1015", "Beefsteak - 15lb 39ct Beef No1",      "Beefsteak"),
    (5,  "RTBB1017", "FTBB1017", "Beefsteak - 15lb 42ct Beef No1",      "Beefsteak"),
    (6,  "RTBB1023", "FTBB1023", "Beefsteak - 15lb 25ct Beef No1",      "Beefsteak"),
    # TOV
    (7,  "RTOV1008", "FTOV1008", "11lb TOV No1",                        "TOV"),
    (8,  "RTOV1132", "FTOV1132", "6x3lb TOV TS No1",                    "TOV"),
    (9,  "RTOV1133", "FTOV1133", "6x2lb TOV TS No1",                    "TOV"),
    (10, "RTOV1200", "FTOV1200", "TOV 5lb Club Pack No1",               "TOV"),
    # Campari
    (11, "RTCA1010", "FTCA1010", "Campari - 8x2lb Camp OTV No1",        "Campari"),
    (12, "RTCA1012", "FTCA1012", "Campari - 12x1lb Camp OTV No1",       "Campari"),
    (13, "RTCA1015", "FTCA1015", "Campari - 16x1lb Camp OTV No1",       "Campari"),
]

DIM_LOCATION = [
    (1, "MPL1",  "MPL"),
    (2, "MPL6-B","MPL"),
    (3, "MPL8",  "MPL"),
    (4, "MPLW",  "MPL"),
]

DIM_VENDOR = [
    (1, "SUNFRESH01",   "Sunfresh Farms"),
    (2, "HERITAGE01",   "Heritage Growers"),
    (3, "VALLEYFRESH01","Valley Fresh Growers"),
    (4, "SUNRISE01",    "Sunrise Greenhouse"),
    (5, "CARLO01",      "Carlo Farms"),
]

DIM_CUSTOMER = [
    # (CustomerKey, ShipToCode, CustomerName)
    (1,  "LOBLAW01",      "LOBLAW COMPANIES LTD"),
    (2,  "SOBEYS01",      "SOBEYS-ONTARIO"),
    (3,  "MEIJER01",      "MEIJER INC"),
    (4,  "METRO01",       "METRO ONTARIO INC"),
    (5,  "WALMART01",     "WALMART (USA)"),
    (6,  "COSTCO01",      "COSTCO US"),
    (7,  "PUBLIX01",      "PUBLIX SUPERMARKETS"),
    (8,  "ALBERTSONS01",  "ALBERTSONS SHAWS MARKET"),
    (9,  "CS01",          "C&S WHOLESALE GROCERS INC"),
    (10, "HYVEE01",       "HY-VEE INC"),
    (11, "WEGMANS01",     "WEGMANS FOOD MARKETS"),
]

# ─────────────────────────────────────────────────────────────────────────────
# FACT_INVENTORY  (one snapshot per SKU × Location at SNAPSHOT date)
# Each entry: (DateKey, SKUKey, LocationKey, TotalSupply, NetAvailable)
# Supply is distributed across SKUs so it totals to the target per alert
# ─────────────────────────────────────────────────────────────────────────────
# MPL1-Beefsteak total supply = 400  (split across 4 Beefsteak SKUs)
# MPL6B-TOV total supply      = 800  (split across 4 TOV SKUs)
# MPL8-Campari total supply   = 1200 (split across 3 Campari SKUs)
# MPLW-Beefsteak total supply = 700  (split across 3 Beefsteak SKUs)

FACT_INVENTORY_ROWS = []
# MPL1 (loc=1) — Beefsteak SKUs (1-6) — total 400
for sku_key, qty in [(1,80),(2,70),(3,70),(4,80),(5,50),(6,50)]:
    FACT_INVENTORY_ROWS.append((SNAPSHOT, sku_key, 1, qty, qty))

# MPL6-B (loc=2) — TOV SKUs (7-10) — total 800
for sku_key, qty in [(7,200),(8,250),(9,200),(10,150)]:
    FACT_INVENTORY_ROWS.append((SNAPSHOT, sku_key, 2, qty, qty))

# MPL8 (loc=3) — Campari SKUs (11-13) — total 1200
for sku_key, qty in [(11,480),(12,360),(13,360)]:
    FACT_INVENTORY_ROWS.append((SNAPSHOT, sku_key, 3, qty, qty))

# MPLW (loc=4) — Beefsteak SKUs (1,2,4) — total 700
for sku_key, qty in [(1,300),(2,200),(4,200)]:
    FACT_INVENTORY_ROWS.append((SNAPSHOT, sku_key, 4, qty, qty))

# ─────────────────────────────────────────────────────────────────────────────
# FACT_DEMAND  (GOOD orders, OutstandingQty > 0)
# (ShipDateKey, SKUKey, LocationKey, CustomerKey, SalesOrderNumber,
#  OriginalQty, OutstandingQty, UnitPrice, AllocatedFlag, SalesType)
# ─────────────────────────────────────────────────────────────────────────────
FACT_DEMAND_ROWS = [

    # ── MPL1 / Beefsteak (loc=1) ─────────────────────────────────────────────
    # LOBLAW (cust=1) ships 2026-03-23 — Tier 1 ($23-24)
    (20260323, 4, 1, 1, "SO-10001", 540, 540, 23.20, False, "GOOD"),  # RTBB1015
    (20260323, 6, 1, 1, "SO-10002", 180, 180, 24.00, False, "GOOD"),  # RTBB1023
    # SOBEYS (cust=2) ships 2026-03-24 — Tier 1 ($40)
    (20260324, 1, 1, 2, "SO-10003", 270, 270, 40.00, False, "GOOD"),  # RTBB1007
    (20260324, 6, 1, 2, "SO-10004",  90,  90, 40.00, False, "GOOD"),  # RTBB1023
    # MEIJER (cust=3) ships 2026-03-26 — Tier 3 ($16-17)
    (20260326, 3, 1, 3, "SO-10005", 360, 360, 16.85, False, "GOOD"),  # RTBB1012
    (20260326, 2, 1, 3, "SO-10006", 270, 270, 16.50, False, "GOOD"),  # RTBB1010

    # ── MPL6-B / TOV (loc=2) ─────────────────────────────────────────────────
    # METRO (cust=4) ships 2026-03-23 — Tier 1 ($22-25.50)
    (20260323, 8, 2, 4, "SO-20001", 600, 600, 25.50, False, "GOOD"),  # RTOV1132
    (20260323, 7, 2, 4, "SO-20002", 400, 400, 22.00, False, "GOOD"),  # RTOV1008
    # WALMART (cust=5) ships 2026-03-25 — Tier 2 ($18-19.50)
    (20260325, 8, 2, 5, "SO-20003", 960, 960, 19.50, False, "GOOD"),  # RTOV1132
    (20260325, 9, 2, 5, "SO-20004", 480, 480, 18.00, False, "GOOD"),  # RTOV1133
    # COSTCO (cust=6) ships 2026-03-27 — Tier 3 ($16)
    (20260327,10, 2, 6, "SO-20005", 960, 960, 16.00, False, "GOOD"),  # RTOV1200

    # ── MPL8 / Campari (loc=3) ───────────────────────────────────────────────
    # PUBLIX (cust=7) ships 2026-03-24 — Tier 1 ($26-28.50)
    (20260324,11, 3, 7, "SO-30001", 480, 480, 28.50, False, "GOOD"),  # RTCA1010
    (20260324,12, 3, 7, "SO-30002", 240, 240, 26.00, False, "GOOD"),  # RTCA1012
    # ALBERTSONS (cust=8) ships 2026-03-25 — Tier 2 ($18.75-19.50)
    (20260325,11, 3, 8, "SO-30003", 360, 360, 19.50, False, "GOOD"),  # RTCA1010
    (20260325,13, 3, 8, "SO-30004", 240, 240, 18.75, False, "GOOD"),  # RTCA1015
    # C&S (cust=9) ships 2026-03-26 — Tier 3 ($15.50)
    (20260326,11, 3, 9, "SO-30005", 480, 480, 15.50, False, "GOOD"),  # RTCA1010

    # ── MPLW / Beefsteak (loc=4) ─────────────────────────────────────────────
    # MEIJER (cust=3) ships 2026-03-23 — Tier 3 ($16.50-16.85)
    (20260323, 4, 4, 3, "SO-40001", 270, 270, 16.85, False, "GOOD"),  # RTBB1015
    (20260323, 5, 4, 3, "SO-40002", 180, 180, 16.50, False, "GOOD"),  # RTBB1017
    # HY-VEE (cust=10) ships 2026-03-25 — Tier 2 ($20.50) / Tier 1 ($22)
    (20260325, 1, 4,10, "SO-40003", 180, 180, 22.00, False, "GOOD"),  # RTBB1007
    (20260325, 2, 4,10, "SO-40004",  90,  90, 20.50, False, "GOOD"),  # RTBB1010
    # WEGMANS (cust=11) ships 2026-03-27 — Tier 1 ($25)
    (20260327, 1, 4,11, "SO-40005", 180, 180, 25.00, False, "GOOD"),  # RTBB1007
]

# ─────────────────────────────────────────────────────────────────────────────
# FACT_INBOUND
# (DeliveryDateKey, SKUKey, LocationKey, VendorKey, PONumber,
#  ExpectedQty, ReceivedQty, ReceiptStatus, TimeReceived)
# ─────────────────────────────────────────────────────────────────────────────
FACT_INBOUND_ROWS = [

    # ── Received POs (historical — for completeness) ──────────────────────────
    (20260318, 4, 1, 1, "PO-88100", 600, 600.0, "Received On Time",  "2026-03-18 08:00:00"),
    (20260319, 8, 2, 4, "PO-88110", 500, 500.0, "Received On Time",  "2026-03-19 09:00:00"),
    (20260319,11, 3, 5, "PO-88120", 800, 800.0, "Received On Time",  "2026-03-19 10:00:00"),
    (20260320, 1, 4, 2, "PO-88130", 400, 400.0, "Received Before Time","2026-03-19 14:00:00"),

    # ── MISSING POs at MPL1 (due before snapshot, not received) ─────────────
    (20260318, 4, 1, 1, "PO-88234", 480,   0.0, "Not Received", None),  # Sunfresh / Critical
    (20260320, 1, 1, 2, "PO-88301", 240,   0.0, "Not Received", None),  # Heritage / High
    (20260321, 4, 1, 1, "PO-88412", 360,   0.0, "Not Received", None),  # Sunfresh / High

    # ── MISSING POs at MPL6-B (due before snapshot, not received) ────────────
    (20260319, 8, 2, 3, "PO-88190", 600,   0.0, "Not Received", None),  # Valley Fresh / Critical
    (20260321, 8, 2, 4, "PO-88211", 800,   0.0, "Not Received", None),  # Sunrise / Critical

    # ── MISSING PO at MPL8 (due before snapshot, not received) ───────────────
    (20260320,11, 3, 5, "PO-88520", 300,   0.0, "Not Received", None),  # Carlo / High

    # ── Future inbounds — MPL1 (rebuild Beefsteak stock) ─────────────────────
    (20260325, 4, 1, 1, "PO-88600", 600,   0.0, "Pending", None),  # Sunfresh
    (20260327, 1, 1, 2, "PO-88601", 400,   0.0, "Pending", None),  # Heritage

    # ── Future inbounds — MPL6-B (rebuild TOV stock) ─────────────────────────
    (20260324, 8, 2, 4, "PO-88610", 500,   0.0, "Pending", None),  # Sunrise
    (20260326, 8, 2, 3, "PO-88611", 700,   0.0, "Pending", None),  # Valley Fresh

    # ── Future inbounds — MPL8 (rebuild Campari stock) ───────────────────────
    (20260325,11, 3, 5, "PO-88620", 400,   0.0, "Pending", None),  # Carlo
    (20260327,11, 3, 5, "PO-88621", 350,   0.0, "Pending", None),  # Carlo

    # ── Future inbounds — MPLW (rebuild Beefsteak stock) ─────────────────────
    (20260324, 1, 4, 2, "PO-88630", 300,   0.0, "Pending", None),  # Heritage
    (20260326, 4, 4, 1, "PO-88631", 250,   0.0, "Pending", None),  # Sunfresh
]

# ─────────────────────────────────────────────────────────────────────────────
# BUILD AND SAVE
# ─────────────────────────────────────────────────────────────────────────────

def save(df, name):
    path = CURATED / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  {name}.csv  ({len(df):,} rows)  ->  {path}")


def main():
    print("Generating demo star-schema data...")

    # Dim_Product
    save(pd.DataFrame(DIM_PRODUCT,
         columns=["SKUKey","SKUCode","FinSKUCode","ProductDescription","Commodity"]),
         "Dim_Product")

    # Dim_Location
    save(pd.DataFrame(DIM_LOCATION,
         columns=["LocationKey","LocationCode","LocationType"]),
         "Dim_Location")

    # Dim_Vendor
    save(pd.DataFrame(DIM_VENDOR,
         columns=["VendorKey","VendorCode","VendorName"]),
         "Dim_Vendor")

    # Dim_Customer
    save(pd.DataFrame(DIM_CUSTOMER,
         columns=["CustomerKey","ShipToCode","CustomerName"]),
         "Dim_Customer")

    # Dim_Date (cover all dates in the data)
    dates = pd.date_range("2026-03-16", "2026-04-05", freq="D")
    dim_date = pd.DataFrame({
        "DateKey":      dates.strftime("%Y%m%d").astype(int),
        "Date":         dates.strftime("%Y-%m-%d"),
        "Day":          dates.day,
        "Week":         dates.isocalendar().week.values,
        "Month":        dates.month,
        "MonthName":    dates.strftime("%B"),
        "FiscalYear":   dates.year,
    })
    save(dim_date, "Dim_Date")

    # Fact_Inventory
    fact_inv = pd.DataFrame(FACT_INVENTORY_ROWS,
        columns=["DateKey","SKUKey","LocationKey","TotalSupply","NetAvailable"])
    fact_inv["InventoryOnHand"]     = fact_inv["TotalSupply"]
    fact_inv["TransfersInExpected"] = 0
    fact_inv["TransfersInReceived"] = 0
    fact_inv["InboundExpected"]     = 0
    fact_inv["InboundReceived"]     = 0
    fact_inv["GoodSalesShipping"]   = 0
    fact_inv["Donations"]           = 0
    fact_inv["TransferShippingOut"] = 0
    col_order = ["DateKey","SKUKey","LocationKey","InventoryOnHand",
                 "TransfersInExpected","TransfersInReceived",
                 "InboundExpected","InboundReceived","TotalSupply",
                 "GoodSalesShipping","Donations","TransferShippingOut","NetAvailable"]
    save(fact_inv[col_order], "Fact_Inventory")

    # Fact_Demand
    fact_dem = pd.DataFrame(FACT_DEMAND_ROWS,
        columns=["ShipDateKey","SKUKey","LocationKey","CustomerKey",
                 "SalesOrderNumber","OriginalQty","OutstandingQty",
                 "UnitPrice","AllocatedFlag","SalesType"])
    fact_dem["ReadyDateKey"] = fact_dem["ShipDateKey"]
    save(fact_dem, "Fact_Demand")

    # Fact_Inbound
    fact_ib = pd.DataFrame(FACT_INBOUND_ROWS,
        columns=["DeliveryDateKey","SKUKey","LocationKey","VendorKey",
                 "PONumber","ExpectedQty","ReceivedQty","ReceiptStatus","TimeReceived"])
    save(fact_ib, "Fact_Inbound")

    # Fact_Transfers (empty — not needed for shortage allocation page)
    save(pd.DataFrame(columns=["ShipDateKey","SKUKey","OriginLocationKey",
                                "DestLocationKey","TransferQty"]),
         "Fact_Transfers")

    print("\nAll demo data files written.")
    print("   Now run:  cd etl/notebooks_or_jobs && python run_all.py")



if __name__ == "__main__":
    main()
