#!/usr/bin/env python3
"""
build_star_schema.py
--------------------------------------------------------------------------------
ETL pipeline: reads raw Excel files -> builds star schema CSVs -> saves to
data/curated/

Raw sources (actual sheet structures discovered from files):
  Cm_inbound/  -> sheet "Data",     header row 4,  cols 5-17
  Sales/        -> sheet "Sales",    header row 1,  cols 1-26
  planning/     -> sheet "Report",   wide pivot,    29-row SKU blocks, cols 7-21

Outputs (data/curated/):
  Dim_Date.csv        Dim_Product.csv    Dim_Location.csv
  Dim_Vendor.csv      Dim_Customer.csv
  Fact_Inbound.csv    Fact_Demand.csv
  Fact_Inventory.csv  Fact_Transfers.csv

Schema note
-----------
Output names map to documented schema as follows:
  Fact_Inbound   -> FactInboundReceipts      (docs/03_data_dictionary.md)
  Fact_Demand    -> FactSales/FactCustomerOrders
  Fact_Inventory -> FactPlanningPosition
  Fact_Transfers -> Transfer movements derived from planning (not in docs schema
                   as a standalone table; documented as columns inside
                   FactPlanningPosition). Extracted here as a separate fact to
                   support Network Planning Tower analysis. If the docs schema
                   is updated, this table should be merged back into
                   Fact_Inventory.

All relationships use surrogate integer keys, never business text fields.
Filter direction is always dimension -> fact (single direction).
No fact-to-fact joins.
--------------------------------------------------------------------------------
"""

import os
import re
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")

# -- Paths ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]          # …/category-manager-analytics/
RAW  = ROOT / "data" / "raw"
OUT  = ROOT / "data" / "curated"
OUT.mkdir(parents=True, exist_ok=True)

INBOUND_FILE  = RAW / "Cm_inbound" / "CM-Inbound Report NEW - Rec cutoff.xlsm"
SALES_FILE    = RAW / "Sales"       / "Beefsteak Sales.xlsx"
PLANNING_FILE = RAW / "planning"    / "MPL1 Planning Report V 24.8.12 (w Piker).xlsm"

# -- Planning Report structure constants ---------------------------------------
# Each SKU occupies exactly 29 rows; the first SKU header is at row index 4.
BLOCK_SIZE        = 29
FIRST_BLOCK_ROW   = 4
DATE_COL_START    = 7    # date columns start at column index 7

# Metric row offsets within each 29-row SKU block (relative to the SKU header)
METRIC = {
    "InventoryOnHand":    1,
    "TransfersInExpected":2,
    "TransfersInReceived":3,
    "InboundExpected":    4,
    "InboundReceived":    5,
    "TotalSupply":        8,   # Total = IOH + Inbound + TransfersIn + ProductionOut
    "GoodSalesShipping":  9,   # Demand (good sales)
    "Donations":         15,   # PIKER/DONATE SALES TOTAL
    "TransferShippingOut":16,  # Total outbound transfers
    "NetAvailable":      27,   # +/- Available (Ready Time)
}

# Transfer-to-destination offsets inside each block
TRANSFER_DEST_OFFSETS = {
    "MPL1":       17,
    "MPL2_INV":   18,
    "MPL3":       19,
    "MPL6-B":     20,
    "MPL8":       21,
    "MPL9":       22,
    "MPLW":       23,
    "FOURSEASON": 24,
    "FRE-AB":     25,
}


# ==============================================================================
# SECTION 1 – RAW DATA LOADERS
# ==============================================================================

def load_inbound_raw() -> pd.DataFrame:
    """
    Read the CM-Inbound XLSM.

    Sheet "Data":
      Row 4 (0-indexed) contains the real column headers.
      Columns 0-4 are Jet Reports macro directives; columns 5-17 are data.
    """
    print("  Loading inbound data …")
    raw = pd.read_excel(INBOUND_FILE, sheet_name="Data", header=None)

    # Row 4 holds real headers; data starts at row 5
    headers = raw.iloc[4, 5:18].tolist()          # cols 5-17
    data    = raw.iloc[5:, 5:18].copy()
    data.columns = headers
    data = data.dropna(how="all").reset_index(drop=True)

    # Rename to match data dictionary
    rename = {
        "Delivery Date":     "DeliveryDate",
        "Location":          "LocationCode",
        "PO Number":         "PONumber",
        "Vendor Code":       "VendorCode",
        "Vendor":            "VendorName",
        "Item No.":          "SKUCode",
        "Commodity":         "Commodity",
        "Description":       "ProductDescription",
        "Expected Qty":      "ExpectedQty",
        "Received Quantity": "ReceivedQty",
        "Time Received":     "TimeReceived",
        "Status":            "ReceiptStatus",
        "Color":             "Color",
    }
    data = data.rename(columns=rename)

    # Type coercion
    data["DeliveryDate"] = pd.to_datetime(data["DeliveryDate"], errors="coerce")
    data["ExpectedQty"]  = pd.to_numeric(data["ExpectedQty"],  errors="coerce")
    data["ReceivedQty"]  = pd.to_numeric(data["ReceivedQty"],  errors="coerce")

    # Drop rows with no SKU or date
    data = data.dropna(subset=["SKUCode", "DeliveryDate"]).reset_index(drop=True)

    print(f"    -> {len(data):,} inbound rows loaded")
    return data


def load_sales_raw() -> pd.DataFrame:
    """
    Read the Beefsteak Sales XLSX.

    Sheet "Sales":
      Row 0 (0-indexed) is a Jet Reports macro directive.
      Row 1 contains the real column headers.
      Column 0 is a macro column; real data is in columns 1-26.
    """
    print("  Loading sales data …")
    raw = pd.read_excel(SALES_FILE, sheet_name="Sales", header=None)

    headers = raw.iloc[1, 1:27].tolist()
    data    = raw.iloc[2:, 1:27].copy()
    data.columns = headers
    data = data.dropna(how="all").reset_index(drop=True)

    rename = {
        "Shipping Location":      "LocationCode",
        "Vendor Name":            "VendorName",
        "Shipment Date":          "ShipmentDate",
        "Ready Date":             "ReadyDate",
        "Customer Sales Type":    "SalesType",
        "Source ID":              "SalesOrderNumber",
        "Destination Name":       "CustomerName",
        "Dest. Ship-to Code":     "ShipToCode",
        "Item No.":               "SKUCode",
        "Description":            "ProductDescription",
        "Description 2":          "Commodity",
        "Original Quantity":      "OriginalQty",
        "Outstanding Quantity":   "OutstandingQty",
        "Finished Quantity":      "FinishedQty",
        "Unit Price":             "UnitPrice",
        "Not Fully Allocated":    "NotFullyAllocated",
        "Allocation":             "Allocation",
        "Allocation Notes":       "AllocationNotes",
        "External Document No.":  "ExternalDocNo",
        "Ready Date Status":      "ReadyDateStatus",
        "Order Created Date Time":"OrderCreatedDateTime",
    }
    data = data.rename(columns={k: v for k, v in rename.items() if k in data.columns})

    # Type coercion
    data["ShipmentDate"] = pd.to_datetime(data["ShipmentDate"], errors="coerce")
    data["ReadyDate"]    = pd.to_datetime(data["ReadyDate"],    errors="coerce")
    data["OriginalQty"]  = pd.to_numeric(data["OriginalQty"],   errors="coerce")
    data["OutstandingQty"] = pd.to_numeric(data["OutstandingQty"], errors="coerce")
    data["UnitPrice"]    = pd.to_numeric(data["UnitPrice"],     errors="coerce")

    # AllocatedFlag: "No" in NotFullyAllocated means fully allocated -> True
    if "NotFullyAllocated" in data.columns:
        data["AllocatedFlag"] = data["NotFullyAllocated"].str.strip().str.upper() == "NO"
    else:
        data["AllocatedFlag"] = False

    data = data.dropna(subset=["SKUCode", "ShipmentDate"]).reset_index(drop=True)

    print(f"    -> {len(data):,} sales rows loaded")
    return data


def load_planning_raw() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Read and parse the Planning Report XLSM, sheet "Report".

    Returns:
      fact_inventory  – long-format planning position per SKU × Date
      fact_transfers  – long-format transfer shipments per SKU × Destination × Date
      location_code   – the location this report covers (e.g. "MPL1")
    """
    print("  Loading planning data …")
    raw = pd.read_excel(PLANNING_FILE, sheet_name="Report", header=None)

    # -- Extract location ------------------------------------------------------
    location_str  = str(raw.iloc[1, 6])          # e.g. "Location: MPL1"
    location_code = location_str.split(":")[-1].strip() if ":" in location_str else "UNKNOWN"

    # -- Extract date columns --------------------------------------------------
    date_row   = raw.iloc[2, DATE_COL_START:]
    date_cols  = []    # (col_index, date_value)
    for idx, val in date_row.items():
        if pd.notna(val):
            try:
                date_cols.append((idx, pd.to_datetime(val)))
            except Exception:
                pass

    if not date_cols:
        raise ValueError("No date columns found in planning Report sheet.")

    print(f"    -> Location: {location_code}, date range: "
          f"{date_cols[0][1].date()} -> {date_cols[-1][1].date()} "
          f"({len(date_cols)} days)")

    # -- Build SKU-to-finished mapping from Report (cols 3 & 4) ---------------
    sku_map_rows = []   # (raw_sku, fin_sku, description)
    n_rows = len(raw)

    row_idx = FIRST_BLOCK_ROW
    while row_idx + BLOCK_SIZE <= n_rows + 1:
        raw_sku = raw.iloc[row_idx, 3]
        fin_sku = raw.iloc[row_idx, 4]
        label   = str(raw.iloc[row_idx, 6])

        if pd.isna(raw_sku):
            row_idx += 1
            continue

        # Extract description from label string, e.g.
        # "RTBB1007|FTBB1007 (Beefsteak - 15lb 22ct Beef No1)"
        desc_match = re.search(r"\((.+)\)$", label)
        description = desc_match.group(1) if desc_match else label
        sku_map_rows.append({
            "RawSKUCode": str(raw_sku).strip(),
            "FinSKUCode": str(fin_sku).strip() if pd.notna(fin_sku) else str(raw_sku).strip(),
            "ProductDescription": description,
        })
        row_idx += BLOCK_SIZE

    sku_map = pd.DataFrame(sku_map_rows).drop_duplicates("RawSKUCode")

    # -- Parse each SKU block into long-format rows ----------------------------
    inv_rows   = []   # Fact_Inventory rows
    trans_rows = []   # Fact_Transfers rows

    row_idx = FIRST_BLOCK_ROW
    while row_idx + BLOCK_SIZE <= n_rows + 1:
        raw_sku = raw.iloc[row_idx, 3]
        if pd.isna(raw_sku):
            row_idx += 1
            continue

        raw_sku = str(raw_sku).strip()

        for col_idx, snap_date in date_cols:

            def _val(offset: int) -> float:
                """Safely read a numeric cell from the current block."""
                r = row_idx + offset
                if r >= n_rows:
                    return 0.0
                v = raw.iloc[r, col_idx]
                return float(v) if pd.notna(v) else 0.0

            inv_rows.append({
                "LocationCode":       location_code,
                "SKUCode":            raw_sku,
                "SnapshotDate":       snap_date,
                "InventoryOnHand":    _val(METRIC["InventoryOnHand"]),
                "TransfersInExpected":_val(METRIC["TransfersInExpected"]),
                "TransfersInReceived":_val(METRIC["TransfersInReceived"]),
                "InboundExpected":    _val(METRIC["InboundExpected"]),
                "InboundReceived":    _val(METRIC["InboundReceived"]),
                "TotalSupply":        _val(METRIC["TotalSupply"]),
                "GoodSalesShipping":  _val(METRIC["GoodSalesShipping"]),
                "Donations":          _val(METRIC["Donations"]),
                "TransferShippingOut":_val(METRIC["TransferShippingOut"]),
                "NetAvailable":       _val(METRIC["NetAvailable"]),
            })

            for dest, offset in TRANSFER_DEST_OFFSETS.items():
                qty = _val(offset)
                if qty != 0.0:
                    trans_rows.append({
                        "OriginLocationCode": location_code,
                        "DestLocationCode":   dest,
                        "SKUCode":            raw_sku,
                        "ShipDate":           snap_date,
                        "TransferQty":        qty,
                    })

        row_idx += BLOCK_SIZE

    fact_inventory = pd.DataFrame(inv_rows)
    fact_transfers = pd.DataFrame(trans_rows) if trans_rows else pd.DataFrame(
        columns=["OriginLocationCode","DestLocationCode","SKUCode","ShipDate","TransferQty"]
    )

    print(f"    -> {len(fact_inventory):,} inventory rows, "
          f"{len(fact_transfers):,} transfer rows parsed")

    return fact_inventory, fact_transfers, sku_map


# ==============================================================================
# SECTION 2 – DIMENSION BUILDERS
# ==============================================================================

def _make_surrogate(df: pd.DataFrame, key_col: str, key_name: str) -> pd.DataFrame:
    """Assign a sequential surrogate integer key starting at 1."""
    df = df.drop_duplicates(subset=[key_col]).reset_index(drop=True)
    df.insert(0, key_name, range(1, len(df) + 1))
    return df


def build_dim_product(inbound: pd.DataFrame,
                      sales: pd.DataFrame,
                      sku_map: pd.DataFrame) -> pd.DataFrame:
    """
    DimProduct – one row per unique SKU (raw item number as business key).

    The planning Report is the authoritative source for the raw->finished
    mapping and product descriptions. Inbound uses raw codes; Sales uses
    finished codes, which are back-mapped here.
    """
    print("  Building Dim_Product …")

    # -- Raw-SKU master from planning (most complete) --------------------------
    base = sku_map[["RawSKUCode","FinSKUCode","ProductDescription"]].copy()

    # Commodity: derive from description prefix (e.g. "Beefsteak", "Campari")
    base["Commodity"] = base["ProductDescription"].str.extract(r"^([^-]+)").iloc[:,0].str.strip()

    # Pack weight / count: infer from description where possible
    base["PackWeight"] = base["ProductDescription"].str.extract(r"(\d+(?:\.\d+)?)\s*lb").iloc[:,0]
    base["CountCt"]    = base["ProductDescription"].str.extract(r"(\d+)ct").iloc[:,0]
    base["Grade"]      = base["ProductDescription"].str.extract(r"(No\d+)").iloc[:,0]

    # ProductGroup: first two alpha chars of RawSKUCode (BB, CA, DE, RM …)
    base["ProductGroup"] = base["RawSKUCode"].str.extract(r"^RT([A-Z]+)").iloc[:,0]

    # -- Supplement with any inbound SKUs not already in planning -------------
    inbound_skus = (
        inbound[["SKUCode","Commodity","ProductDescription"]]
        .rename(columns={"SKUCode":"RawSKUCode"})
        .drop_duplicates("RawSKUCode")
    )
    new_inbound = inbound_skus[~inbound_skus["RawSKUCode"].isin(base["RawSKUCode"])]
    if not new_inbound.empty:
        new_inbound = new_inbound.copy()
        new_inbound["FinSKUCode"]  = new_inbound["RawSKUCode"]
        new_inbound["PackWeight"]  = None
        new_inbound["CountCt"]     = None
        new_inbound["Grade"]       = None
        new_inbound["ProductGroup"]= new_inbound["RawSKUCode"].str.extract(r"^RT([A-Z]+)").iloc[:,0]
        base = pd.concat([base, new_inbound], ignore_index=True)

    # -- Supplement with any finished-SKU-only sales items --------------------
    fin_to_raw = dict(zip(sku_map["FinSKUCode"], sku_map["RawSKUCode"]))
    sales_skus = sales["SKUCode"].dropna().unique()
    unmapped   = [s for s in sales_skus
                  if s not in fin_to_raw and s not in base["RawSKUCode"].values]
    if unmapped:
        extra = pd.DataFrame({
            "RawSKUCode":         unmapped,
            "FinSKUCode":         unmapped,
            "ProductDescription": [None] * len(unmapped),
            "Commodity":          [None] * len(unmapped),
            "PackWeight":         [None] * len(unmapped),
            "CountCt":            [None] * len(unmapped),
            "Grade":              [None] * len(unmapped),
            "ProductGroup":       [None] * len(unmapped),
        })
        base = pd.concat([base, extra], ignore_index=True)

    dim = _make_surrogate(base, "RawSKUCode", "SKUKey")
    dim = dim.rename(columns={"RawSKUCode":"SKUCode"})
    cols = ["SKUKey","SKUCode","FinSKUCode","ProductDescription","Commodity",
            "PackWeight","CountCt","Grade","ProductGroup"]
    dim = dim[[c for c in cols if c in dim.columns]]
    print(f"    -> {len(dim):,} products")
    return dim


def build_dim_location(inbound: pd.DataFrame,
                       sales: pd.DataFrame,
                       planning_loc: str,
                       trans_dests: list) -> pd.DataFrame:
    """
    DimLocation – one row per unique location code found across all sources.
    LocationType is inferred from the code pattern.
    """
    print("  Building Dim_Location …")

    codes = set()
    codes.update(inbound["LocationCode"].dropna().unique())
    codes.update(sales["LocationCode"].dropna().unique())
    if "ShipToCode" in sales.columns:
        codes.update(sales["ShipToCode"].dropna().unique())
    codes.add(planning_loc)
    codes.update(trans_dests)

    def _type(code: str) -> str:
        c = str(code).upper()
        if c.startswith("MPL"):  return "MPL"
        if c in ("DIRECT",):     return "DC"
        if re.match(r"^[A-Z]{2,}\d", c): return "Customer"
        return "Unknown"

    rows = [{"LocationCode": c, "LocationType": _type(c), "Region": None}
            for c in sorted(codes)]
    df   = pd.DataFrame(rows)
    dim  = _make_surrogate(df, "LocationCode", "LocationKey")
    print(f"    -> {len(dim):,} locations")
    return dim


def build_dim_vendor(inbound: pd.DataFrame) -> pd.DataFrame:
    """DimVendor – one row per unique vendor from inbound receipts."""
    print("  Building Dim_Vendor …")
    df = (inbound[["VendorCode","VendorName"]]
          .dropna(subset=["VendorCode"])
          .drop_duplicates("VendorCode"))
    dim = _make_surrogate(df, "VendorCode", "VendorKey")
    print(f"    -> {len(dim):,} vendors")
    return dim


def build_dim_customer(sales: pd.DataFrame) -> pd.DataFrame:
    """DimCustomer – one row per unique ship-to from sales."""
    print("  Building Dim_Customer …")
    cols = {c for c in ["CustomerName","ShipToCode","SalesType"] if c in sales.columns}
    if "ShipToCode" not in sales.columns:
        print("    -> ShipToCode not found; Dim_Customer will be empty")
        return pd.DataFrame(columns=["CustomerKey","ShipToCode","CustomerName","CustomerType"])

    df = (sales[list(cols)]
          .rename(columns={"SalesType":"CustomerType"})
          .dropna(subset=["ShipToCode"])
          .drop_duplicates("ShipToCode"))
    dim = _make_surrogate(df, "ShipToCode", "CustomerKey")
    print(f"    -> {len(dim):,} customers")
    return dim


def build_dim_date(all_dates: list) -> pd.DataFrame:
    """
    DimDate – full calendar table spanning all dates observed in facts.
    Fiscal year is assumed to start in January (adjust if needed).
    """
    print("  Building Dim_Date …")
    all_dates_clean = [d for d in all_dates if pd.notna(d)]
    if not all_dates_clean:
        raise ValueError("No valid dates found across fact sources.")

    min_date = min(all_dates_clean).normalize()
    max_date = max(all_dates_clean).normalize()
    date_range = pd.date_range(min_date, max_date, freq="D")

    dim = pd.DataFrame({
        "DateKey":      date_range.strftime("%Y%m%d").astype(int),
        "Date":         date_range,
        "Day":          date_range.day,
        "Week":         date_range.isocalendar().week.values,
        "Month":        date_range.month,
        "MonthName":    date_range.strftime("%B"),
        "FiscalMonth":  date_range.strftime("FY%y-M%m"),
        "FiscalQuarter":date_range.to_period("Q").astype(str),
        "FiscalYear":   date_range.year,
    })
    print(f"    -> {len(dim):,} dates ({min_date.date()} -> {max_date.date()})")
    return dim


# ==============================================================================
# SECTION 3 – FACT BUILDERS
# ==============================================================================

def _lookup_key(df: pd.DataFrame, source_col: str, dim: pd.DataFrame,
                dim_biz_col: str, dim_key_col: str,
                default: int = -1) -> pd.Series:
    """Left-join a surrogate key from a dimension table."""
    mapping = dim.set_index(dim_biz_col)[dim_key_col]
    return df[source_col].map(mapping).fillna(default).astype(int)


def build_fact_inbound(inbound: pd.DataFrame,
                       dim_product:  pd.DataFrame,
                       dim_location: pd.DataFrame,
                       dim_vendor:   pd.DataFrame,
                       dim_date:     pd.DataFrame) -> pd.DataFrame:
    """
    Fact_Inbound -> FactInboundReceipts
    Grain: PO line × SKU × Location × Delivery Date
    """
    print("  Building Fact_Inbound …")

    # Map finished-SKU codes from inbound back to raw via dim_product
    fin_to_raw = dict(zip(dim_product["FinSKUCode"], dim_product["SKUCode"]))

    f = inbound.copy()
    f["SKUCode_resolved"] = f["SKUCode"].map(
        lambda x: fin_to_raw.get(x, x)   # inbound already uses raw codes; this is a safety pass
    )
    f["DeliveryDateKey"] = (
        f["DeliveryDate"].dt.strftime("%Y%m%d").astype(int)
    )

    f["SKUKey"]      = _lookup_key(f, "SKUCode_resolved", dim_product,  "SKUCode",      "SKUKey")
    f["LocationKey"] = _lookup_key(f, "LocationCode",     dim_location, "LocationCode", "LocationKey")
    f["VendorKey"]   = _lookup_key(f, "VendorCode",       dim_vendor,   "VendorCode",   "VendorKey")

    # Validate DateKey exists in DimDate
    valid_dates = set(dim_date["DateKey"])
    f = f[f["DeliveryDateKey"].isin(valid_dates)]

    fact = f[[
        "DeliveryDateKey","SKUKey","LocationKey","VendorKey",
        "PONumber","ExpectedQty","ReceivedQty","ReceiptStatus","TimeReceived",
    ]].copy()

    print(f"    -> {len(fact):,} rows")
    return fact


def build_fact_demand(sales: pd.DataFrame,
                      dim_product:  pd.DataFrame,
                      dim_location: pd.DataFrame,
                      dim_customer: pd.DataFrame,
                      dim_date:     pd.DataFrame) -> pd.DataFrame:
    """
    Fact_Demand -> FactSales / FactCustomerOrders
    Grain: Sales order line × SKU × Location × Ship Date
    """
    print("  Building Fact_Demand …")

    # Sales uses FinSKUCode (e.g. FTBB1007); map -> raw via dim_product
    fin_to_raw = dict(zip(dim_product["FinSKUCode"], dim_product["SKUCode"]))

    f = sales.copy()
    f["SKUCode_resolved"] = f["SKUCode"].map(lambda x: fin_to_raw.get(x, x))
    f["ShipDateKey"]  = f["ShipmentDate"].dt.strftime("%Y%m%d").astype(int)
    f["ReadyDateKey"] = f["ReadyDate"].dt.strftime("%Y%m%d").fillna("0").astype(int)

    f["SKUKey"]      = _lookup_key(f, "SKUCode_resolved", dim_product,  "SKUCode",      "SKUKey")
    f["LocationKey"] = _lookup_key(f, "LocationCode",     dim_location, "LocationCode", "LocationKey")
    f["CustomerKey"] = (
        _lookup_key(f, "ShipToCode", dim_customer, "ShipToCode", "CustomerKey")
        if "ShipToCode" in f.columns and len(dim_customer) > 0
        else pd.Series(-1, index=f.index, dtype=int)
    )

    valid_dates = set(dim_date["DateKey"])
    f = f[f["ShipDateKey"].isin(valid_dates)]

    fact = f[[
        "ShipDateKey","ReadyDateKey","SKUKey","LocationKey","CustomerKey",
        "SalesOrderNumber","OriginalQty","OutstandingQty","UnitPrice",
        "AllocatedFlag","SalesType",
    ]].copy()

    print(f"    -> {len(fact):,} rows")
    return fact


def build_fact_inventory(planning_long: pd.DataFrame,
                         dim_product:   pd.DataFrame,
                         dim_location:  pd.DataFrame,
                         dim_date:      pd.DataFrame) -> pd.DataFrame:
    """
    Fact_Inventory -> FactPlanningPosition
    Grain: SKU × Location × Date (daily snapshot)
    """
    print("  Building Fact_Inventory …")

    f = planning_long.copy()
    f["DateKey"] = f["SnapshotDate"].dt.strftime("%Y%m%d").astype(int)

    f["SKUKey"]      = _lookup_key(f, "SKUCode",      dim_product,  "SKUCode",      "SKUKey")
    f["LocationKey"] = _lookup_key(f, "LocationCode", dim_location, "LocationCode", "LocationKey")

    valid_dates = set(dim_date["DateKey"])
    f = f[f["DateKey"].isin(valid_dates)]

    fact = f[[
        "DateKey","SKUKey","LocationKey",
        "InventoryOnHand","TransfersInExpected","TransfersInReceived",
        "InboundExpected","InboundReceived","TotalSupply",
        "GoodSalesShipping","Donations","TransferShippingOut","NetAvailable",
    ]].copy()

    print(f"    -> {len(fact):,} rows")
    return fact


def build_fact_transfers(planning_transfers: pd.DataFrame,
                         dim_product:        pd.DataFrame,
                         dim_location:       pd.DataFrame,
                         dim_date:           pd.DataFrame) -> pd.DataFrame:
    """
    Fact_Transfers – outbound transfer shipments by SKU × origin × destination × date.
    Derived from the "Shipping TO [location]" rows in the planning Report sheet.

    Note: not explicitly a standalone table in docs/04_star_schema.md.
    Transfer movements are documented as columns in FactPlanningPosition.
    This table is generated to support Network Planning Tower granularity
    (which destination, how much, on which date).
    """
    print("  Building Fact_Transfers …")

    if planning_transfers.empty:
        print("    -> No transfer rows found; writing empty file")
        return planning_transfers

    f = planning_transfers.copy()
    f["ShipDateKey"] = f["ShipDate"].dt.strftime("%Y%m%d").astype(int)

    f["SKUKey"]           = _lookup_key(f, "SKUCode",             dim_product,  "SKUCode",      "SKUKey")
    f["OriginLocationKey"]= _lookup_key(f, "OriginLocationCode",  dim_location, "LocationCode", "LocationKey")
    f["DestLocationKey"]  = _lookup_key(f, "DestLocationCode",    dim_location, "LocationCode", "LocationKey")

    valid_dates = set(dim_date["DateKey"])
    f = f[f["ShipDateKey"].isin(valid_dates)]

    fact = f[[
        "ShipDateKey","SKUKey","OriginLocationKey","DestLocationKey","TransferQty",
    ]].copy()

    print(f"    -> {len(fact):,} rows")
    return fact


# ==============================================================================
# SECTION 4 – SAVE & VALIDATE
# ==============================================================================

def save_csv(df: pd.DataFrame, name: str) -> None:
    path = OUT / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  OK {name}.csv  ({len(df):,} rows, {len(df.columns)} cols) -> {path}")


def validate(dims: dict, facts: dict) -> None:
    """Basic referential integrity checks (warn only, do not raise)."""
    print("\n-- Validation ---------------------------------------------------")
    checks = [
        # (fact_name, fact_fk_col, dim_name, dim_pk_col)
        ("Fact_Inbound",   "SKUKey",          "Dim_Product",  "SKUKey"),
        ("Fact_Inbound",   "LocationKey",     "Dim_Location", "LocationKey"),
        ("Fact_Inbound",   "VendorKey",       "Dim_Vendor",   "VendorKey"),
        ("Fact_Inbound",   "DeliveryDateKey", "Dim_Date",     "DateKey"),
        ("Fact_Demand",    "SKUKey",          "Dim_Product",  "SKUKey"),
        ("Fact_Demand",    "LocationKey",     "Dim_Location", "LocationKey"),
        ("Fact_Demand",    "ShipDateKey",     "Dim_Date",     "DateKey"),
        ("Fact_Inventory", "SKUKey",          "Dim_Product",  "SKUKey"),
        ("Fact_Inventory", "LocationKey",     "Dim_Location", "LocationKey"),
        ("Fact_Inventory", "DateKey",         "Dim_Date",     "DateKey"),
    ]
    all_ok = True
    for fname, fk, dname, pk in checks:
        if fname not in facts or dname not in dims:
            continue
        orphans = ~facts[fname][fk].isin(dims[dname][pk])
        n_orphans = orphans.sum()
        if n_orphans:
            print(f"  WARN  {fname}.{fk}: {n_orphans:,} orphan keys not in {dname}.{pk}")
            all_ok = False
    if all_ok:
        print("  All referential integrity checks passed.")


# ==============================================================================
# SECTION 5 – MAIN ORCHESTRATION
# ==============================================================================

def main() -> None:
    print("=" * 70)
    print("Network Planning Tower – Star Schema ETL")
    print("=" * 70)

    # -- 1. Load raw data ------------------------------------------------------
    print("\n[1/4] Loading raw data")
    inbound                            = load_inbound_raw()
    sales                              = load_sales_raw()
    plan_inventory, plan_transfers, sku_map = load_planning_raw()

    planning_location = plan_inventory["LocationCode"].iloc[0] if len(plan_inventory) else "MPL1"
    transfer_dests    = list(TRANSFER_DEST_OFFSETS.keys())

    # -- 2. Build dimensions ---------------------------------------------------
    print("\n[2/4] Building dimension tables")
    dim_product  = build_dim_product(inbound, sales, sku_map)
    dim_location = build_dim_location(inbound, sales, planning_location, transfer_dests)
    dim_vendor   = build_dim_vendor(inbound)
    dim_customer = build_dim_customer(sales)

    # Collect all dates for DimDate
    all_dates = (
        list(inbound["DeliveryDate"].dropna())
        + list(sales["ShipmentDate"].dropna())
        + list(sales["ReadyDate"].dropna())
        + list(plan_inventory["SnapshotDate"].dropna())
    )
    dim_date = build_dim_date(all_dates)

    # -- 3. Build facts --------------------------------------------------------
    print("\n[3/4] Building fact tables")
    fact_inbound   = build_fact_inbound(inbound, dim_product, dim_location, dim_vendor, dim_date)
    fact_demand    = build_fact_demand(sales, dim_product, dim_location, dim_customer, dim_date)
    fact_inventory = build_fact_inventory(plan_inventory, dim_product, dim_location, dim_date)
    fact_transfers = build_fact_transfers(plan_transfers, dim_product, dim_location, dim_date)

    # -- 4. Save ---------------------------------------------------------------
    print(f"\n[4/4] Saving CSVs -> {OUT}")
    dims  = {
        "Dim_Date":     dim_date,
        "Dim_Product":  dim_product,
        "Dim_Location": dim_location,
        "Dim_Vendor":   dim_vendor,
        "Dim_Customer": dim_customer,
    }
    facts = {
        "Fact_Inbound":   fact_inbound,
        "Fact_Demand":    fact_demand,
        "Fact_Inventory": fact_inventory,
        "Fact_Transfers": fact_transfers,
    }
    for name, df in {**dims, **facts}.items():
        save_csv(df, name)

    validate(dims, facts)

    print("\n" + "=" * 70)
    print("ETL complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
