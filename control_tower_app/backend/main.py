"""
Network Planning Control Tower — FastAPI Backend  v2
Adds: /api/filters, commodity+location filters on all endpoints,
      date_key selector, peak shortage, allocation resolution by commodity.
"""
import os
from typing import Optional
from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Network Planning Control Tower API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CURATED = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated")
)


def load(name: str) -> pd.DataFrame:
    path = os.path.join(CURATED, f"{name}.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail=f"Missing file: {path}")
    return pd.read_csv(path)



def dims():
    return {
        "prod": load("Dim_Product"),
        "loc":  load("Dim_Location"),
        "vend": load("Dim_Vendor"),
        "cust": load("Dim_Customer"),
    }


def filter_by_commodity(df: pd.DataFrame, dim_prod: pd.DataFrame,
                         commodity: Optional[str]) -> pd.DataFrame:
    """Restrict df to SKUKeys that belong to the given commodity."""
    if not commodity or commodity == "all":
        return df
    valid = dim_prod[dim_prod["Commodity"] == commodity]["SKUKey"].tolist()
    return df[df["SKUKey"].isin(valid)]


def filter_by_location(df: pd.DataFrame, dim_loc: pd.DataFrame,
                        location_code: Optional[str]) -> pd.DataFrame:
    """Restrict df to LocationKeys matching location_code."""
    if not location_code or location_code == "all":
        return df
    valid = dim_loc[dim_loc["LocationCode"] == location_code]["LocationKey"].tolist()
    return df[df["LocationKey"].isin(valid)]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/filters  — dropdown options for the UI
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/filters", summary="Dropdown options for all filter controls")
def get_filters():
    d         = dims()
    fact_inv  = load("Fact_Inventory")
    fact_ib   = load("Fact_Inbound")

    commodities = sorted(d["prod"]["Commodity"].dropna().unique().tolist())

    # Only expose planning-relevant location types (MPL + DC/DIRECT)
    planning_locs = d["loc"][d["loc"]["LocationType"].isin(["MPL", "DC"])]
    locations = sorted(planning_locs["LocationCode"].dropna().unique().tolist())

    inv_dates = sorted(fact_inv["DateKey"].astype(int).unique().tolist())
    exc_dates = sorted(fact_ib["DeliveryDateKey"].astype(int).unique().tolist())

    # Identify which inventory dates have at least one shortage
    shortage_dates = (
        fact_inv[fact_inv["NetAvailable"] < 0]["DateKey"]
        .astype(int).unique().tolist()
    )

    # SKU list: key + code + description + commodity, for the allocation SKU picker
    skus = (
        d["prod"][["SKUKey", "SKUCode", "ProductDescription", "Commodity"]]
        .dropna(subset=["SKUCode"])
        .sort_values(["Commodity", "SKUCode"])
        .to_dict(orient="records")
    )

    return {
        "commodities":    commodities,
        "locations":      locations,
        "inventory_dates": inv_dates,
        "delivery_dates": exc_dates,
        "shortage_dates": sorted(shortage_dates),
        "skus":           skus,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/kpis
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/kpis", summary="Headline KPIs — filterable by commodity, location, date")
def get_kpis(
    commodity:     Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
    date_key:      Optional[int] = Query(default=None,
                       description="Inventory snapshot date (YYYYMMDD). "
                                   "Defaults to latest available."),
):
    d        = dims()
    fact_inv = load("Fact_Inventory")
    fact_dem = load("Fact_Demand")
    fact_ib  = load("Fact_Inbound")

    # Apply dimension filters
    inv = filter_by_commodity(fact_inv, d["prod"], commodity)
    inv = filter_by_location(inv, d["loc"], location_code)

    # Resolve snapshot date
    available_dates = sorted(inv["DateKey"].astype(int).unique().tolist())
    if not available_dates:
        return {"error": "No data for selected filters"}

    if date_key and date_key in available_dates:
        snap = date_key
    else:
        # Default to closest date <= today; fall back to latest in data
        today_int = int(date.today().strftime("%Y%m%d"))
        past = [d_ for d_ in available_dates if d_ <= today_int]
        snap = max(past) if past else max(available_dates)

    snap_inv = inv[inv["DateKey"] == snap]

    total_supply   = float(snap_inv["TotalSupply"].sum())
    shortage_count = int((snap_inv["NetAvailable"] < 0).sum())

    # Peak shortage across all dates (for the badge)
    peak_shortage_date = None
    shortage_by_date = (
        inv.groupby("DateKey")
        .apply(lambda g: (g["NetAvailable"] < 0).sum())
    )
    if shortage_by_date.max() > 0:
        peak_shortage_date = int(shortage_by_date.idxmax())

    # Demand for selected date
    dem = load("Fact_Demand")
    dem = filter_by_commodity(dem, d["prod"], commodity)
    dem = filter_by_location(dem, d["loc"], location_code)
    snap_dem    = dem[dem["ShipDateKey"] == snap]
    total_demand = float(snap_dem["OutstandingQty"].sum())

    # Net position = supply minus outstanding demand (not NetAvailable from inventory)
    net_position = total_supply - total_demand

    # Inbound fill rate (overall, filtered)
    ib = load("Fact_Inbound")
    ib = filter_by_commodity(ib, d["prod"], commodity)
    ib = filter_by_location(ib, d["loc"], location_code)
    expected = ib["ExpectedQty"].sum()
    received = ib["ReceivedQty"].fillna(0).sum()
    fill_rate = round(received / expected * 100, 1) if expected > 0 else 0.0

    return {
        "as_of_date":          snap,
        "available_dates":     available_dates,
        "total_supply":        round(total_supply),
        "total_demand":        round(total_demand),
        "net_position":        round(net_position),
        "shortage_count":      shortage_count,
        "peak_shortage_date":  peak_shortage_date,
        "inbound_fill_rate_pct": fill_rate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/exceptions
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/exceptions", summary="Overnight inbound exceptions — filterable")
def get_exceptions(
    commodity:     Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
    delivery_date: Optional[int] = Query(default=None,
                       description="Filter to one delivery date (YYYYMMDD). "
                                   "Defaults to the most recent delivery date in the data."),
    min_variance:  int           = Query(default=1),
):
    d       = dims()
    fact_ib = load("Fact_Inbound")

    fact_ib["Shortage_Variance"] = (
        fact_ib["ExpectedQty"] - fact_ib["ReceivedQty"].fillna(0)
    )
    exc = fact_ib[fact_ib["Shortage_Variance"] >= min_variance].copy()

    # Apply filters
    exc = filter_by_commodity(exc, d["prod"], commodity)
    exc = filter_by_location(exc, d["loc"], location_code)

    # Default to the most recent delivery date if none specified
    if delivery_date:
        exc = exc[exc["DeliveryDateKey"] == delivery_date]
    else:
        latest_delivery = int(exc["DeliveryDateKey"].max()) if not exc.empty else None
        if latest_delivery:
            exc = exc[exc["DeliveryDateKey"] == latest_delivery]

    if exc.empty:
        return []

    exc = (
        exc
        .merge(d["loc"][["LocationKey", "LocationCode", "LocationType"]],
               on="LocationKey", how="left")
        .merge(d["vend"][["VendorKey", "VendorName"]], on="VendorKey", how="left")
        .merge(d["prod"][["SKUKey", "SKUCode", "Commodity"]], on="SKUKey", how="left")
    )

    po = (
        exc
        .groupby(["PONumber", "VendorName", "LocationCode", "LocationType",
                  "DeliveryDateKey"], as_index=False)
        .agg(
            Lines             = ("SKUCode",           "count"),
            ExpectedQty       = ("ExpectedQty",        "sum"),
            ReceivedQty       = ("ReceivedQty",         "sum"),
            Shortage_Variance = ("Shortage_Variance",   "sum"),
            Commodities       = ("Commodity",
                                 lambda x: ", ".join(sorted(x.dropna().unique()))),
        )
        .sort_values("Shortage_Variance", ascending=False)
        .reset_index(drop=True)
    )

    po["Fill_Rate_Pct"] = (
        po["ReceivedQty"] / po["ExpectedQty"].replace(0, float("nan")) * 100
    ).round(1).fillna(0)

    def severity(v):
        if v >= 2_000: return "Critical"
        if v >= 1_000: return "High"
        if v >=   500: return "Medium"
        return "Low"

    po["Severity"] = po["Shortage_Variance"].apply(severity)

    return po.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/forecast
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/forecast", summary="Supply vs Demand trend — filterable")
def get_forecast(
    commodity:     Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
):
    d        = dims()
    fact_inv = load("Fact_Inventory")
    fact_dem = load("Fact_Demand")

    inv = filter_by_commodity(fact_inv, d["prod"], commodity)
    inv = filter_by_location(inv, d["loc"], location_code)

    dem = filter_by_commodity(fact_dem, d["prod"], commodity)
    dem = filter_by_location(dem, d["loc"], location_code)

    supply_daily = (
        inv.groupby("DateKey", as_index=False)
        .agg(TotalSupply=("TotalSupply", "sum"), NetAvailable=("NetAvailable", "sum"))
    )
    demand_daily = (
        dem.groupby("ShipDateKey", as_index=False)
        .agg(TotalDemand=("OutstandingQty", "sum"))
        .rename(columns={"ShipDateKey": "DateKey"})
    )

    fc = (
        supply_daily.merge(demand_daily, on="DateKey", how="outer")
        .fillna(0)
        .sort_values("DateKey")
    )
    fc["Date"]         = pd.to_datetime(
        fc["DateKey"].astype(int).astype(str), format="%Y%m%d"
    ).dt.strftime("%b %d")
    fc["ShortageFlag"] = (fc["NetAvailable"] < 0).astype(int)

    return fc[["DateKey", "Date", "TotalSupply", "TotalDemand",
               "NetAvailable", "ShortageFlag"]].to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/allocations
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/allocations", summary="Tier-based allocation — filterable by commodity/location")
def get_allocations(
    sku_key:       Optional[int] = Query(default=None),
    location_key:  Optional[int] = Query(default=None),
    commodity:     Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
):
    d        = dims()
    fact_inv = load("Fact_Inventory")
    fact_dem = load("Fact_Demand")

    # ── Resolve sku_key ───────────────────────────────────────────────────────
    if sku_key is None:
        prod_pool = (
            d["prod"][d["prod"]["Commodity"] == commodity]
            if commodity and commodity != "all"
            else d["prod"]
        )
        # Find the SKU with the worst cumulative net position
        inv_pool = fact_inv[fact_inv["SKUKey"].isin(prod_pool["SKUKey"])]
        if location_key is None and location_code and location_code != "all":
            valid_locs = d["loc"][d["loc"]["LocationCode"] == location_code]["LocationKey"].tolist()
            inv_pool = inv_pool[inv_pool["LocationKey"].isin(valid_locs)]

        if inv_pool.empty:
            sku_key = 4  # fallback: RTBB1015
        else:
            worst = inv_pool.groupby("SKUKey")["NetAvailable"].sum()
            sku_key = int(worst.idxmin())

    # ── Resolve location_key ──────────────────────────────────────────────────
    if location_key is None:
        if location_code and location_code != "all":
            row = d["loc"][d["loc"]["LocationCode"] == location_code]
            location_key = int(row["LocationKey"].iloc[0]) if not row.empty else 124
        else:
            # Pick the location with the worst position for this SKU
            inv_sku = fact_inv[fact_inv["SKUKey"] == sku_key]
            if not inv_sku.empty:
                worst_loc = inv_sku.groupby("LocationKey")["NetAvailable"].sum()
                location_key = int(worst_loc.idxmin())
            else:
                location_key = 124

    # ── Demand rows ───────────────────────────────────────────────────────────
    dem = fact_dem[
        (fact_dem["SKUKey"]      == sku_key) &
        (fact_dem["LocationKey"] == location_key) &
        (fact_dem["OutstandingQty"] > 0)
    ].copy()

    if dem.empty:
        sku_desc = d["prod"][d["prod"]["SKUKey"] == sku_key]["ProductDescription"].values
        loc_code = d["loc"][d["loc"]["LocationKey"] == location_key]["LocationCode"].values
        return {
            "sku_key": sku_key, "sku_description": str(sku_desc[0]) if len(sku_desc) else "Unknown",
            "location_key": location_key, "location_code": str(loc_code[0]) if len(loc_code) else "Unknown",
            "available_supply": 0, "total_demand": 0, "shortage": 0,
            "flat_cut_rate_pct": 0, "rows": [],
        }

    dem = dem.merge(d["cust"][["CustomerKey", "CustomerName"]], on="CustomerKey", how="left")
    dem = dem.merge(d["prod"][["SKUKey", "SKUCode", "ProductDescription"]], on="SKUKey", how="left")

    def tier(price):
        if price >= 22: return "Tier 1 - High Margin"
        if price >= 18: return "Tier 2 - Standard"
        return           "Tier 3 - Flexible"

    dem["Priority_Tier"] = dem["UnitPrice"].apply(tier)

    dem_agg = (
        dem
        .groupby(["CustomerName", "Priority_Tier", "UnitPrice", "ShipDateKey"], as_index=False)
        .agg(OutstandingQty=("OutstandingQty", "sum"))
        .sort_values(["Priority_Tier", "ShipDateKey"])
    )

    # Current supply
    latest_key    = int(fact_inv[fact_inv["SKUKey"] == sku_key]["DateKey"].max())
    supply_rows   = fact_inv[
        (fact_inv["SKUKey"] == sku_key) &
        (fact_inv["LocationKey"] == location_key) &
        (fact_inv["DateKey"] == latest_key)
    ]
    available_supply = max(float(supply_rows["NetAvailable"].sum()) if not supply_rows.empty else 0, 0)
    total_demand     = float(dem_agg["OutstandingQty"].sum())
    shortage         = max(total_demand - available_supply, 0)
    flat_cut_rate    = shortage / total_demand if total_demand > 0 else 0

    tier_cut = {
        "Tier 1 - High Margin": 0.0,
        "Tier 2 - Standard":    round(min(flat_cut_rate * 0.5, 1.0), 4),
        "Tier 3 - Flexible":    round(min(flat_cut_rate * 2.0, 1.0), 4),
    }

    dem_agg["Cut_Rate"]      = dem_agg["Priority_Tier"].map(tier_cut)
    dem_agg["Suggested_Cut"] = (dem_agg["OutstandingQty"] * dem_agg["Cut_Rate"]).round().astype(int)
    dem_agg["Allocated_Qty"] = (dem_agg["OutstandingQty"] - dem_agg["Suggested_Cut"]).astype(int)
    dem_agg["Fill_Rate_Pct"] = (dem_agg["Allocated_Qty"] / dem_agg["OutstandingQty"] * 100).round(1)
    dem_agg["Date"]          = pd.to_datetime(
        dem_agg["ShipDateKey"].astype(str), format="%Y%m%d"
    ).dt.strftime("%b %d")

    sku_desc = d["prod"][d["prod"]["SKUKey"] == sku_key]["ProductDescription"].values
    loc_code = d["loc"][d["loc"]["LocationKey"] == location_key]["LocationCode"].values

    return {
        "sku_key":           sku_key,
        "sku_description":   str(sku_desc[0]) if len(sku_desc) else "Unknown",
        "location_key":      location_key,
        "location_code":     str(loc_code[0]) if len(loc_code) else "Unknown",
        "as_of_date":        latest_key,
        "available_supply":  round(available_supply),
        "total_demand":      round(total_demand),
        "shortage":          round(shortage),
        "flat_cut_rate_pct": round(flat_cut_rate * 100, 1),
        "rows":              dem_agg.to_dict(orient="records"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/risk-trace  — Vendor → Inbound → Inventory → Customer demand at risk
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/risk-trace", summary="Trace vendor inbound failures to customer revenue at risk")
def get_risk_trace(
    commodity:     Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
    min_shortage:  int           = Query(default=100,
                       description="Minimum vendor shortage (cases) to include"),
):
    d        = dims()
    fact_ib  = load("Fact_Inbound")
    fact_inv = load("Fact_Inventory")
    fact_dem = load("Fact_Demand")

    # ── Apply dimension filters ───────────────────────────────────────────────
    fact_ib  = filter_by_commodity(fact_ib,  d["prod"], commodity)
    fact_ib  = filter_by_location(fact_ib,   d["loc"],  location_code)
    fact_inv = filter_by_commodity(fact_inv, d["prod"], commodity)
    fact_inv = filter_by_location(fact_inv,  d["loc"],  location_code)
    fact_dem = filter_by_commodity(fact_dem, d["prod"], commodity)
    fact_dem = filter_by_location(fact_dem,  d["loc"],  location_code)

    # ── Step 1: Inbound failures ──────────────────────────────────────────────
    fact_ib = fact_ib.copy()
    fact_ib["Shortage"] = fact_ib["ExpectedQty"] - fact_ib["ReceivedQty"].fillna(0)
    failures = fact_ib[fact_ib["Shortage"] >= min_shortage].copy()

    if failures.empty:
        return []

    failures = (
        failures
        .merge(d["vend"][["VendorKey", "VendorName"]], on="VendorKey", how="left")
        .merge(d["prod"][["SKUKey", "SKUCode", "Commodity"]], on="SKUKey", how="left")
        .merge(d["loc"][["LocationKey", "LocationCode"]], on="LocationKey", how="left")
    )

    # ── Step 2: Inventory gaps ────────────────────────────────────────────────
    inv_gaps = fact_inv[fact_inv["NetAvailable"] < 0][
        ["SKUKey", "LocationKey", "DateKey", "NetAvailable"]
    ].copy()

    # ── Step 3: Demand at risk ────────────────────────────────────────────────
    demand = fact_dem[fact_dem["OutstandingQty"] > 0].copy()
    demand = (
        demand
        .merge(d["cust"][["CustomerKey", "CustomerName"]], on="CustomerKey", how="left")
        .merge(d["prod"][["SKUKey", "SKUCode", "Commodity"]], on="SKUKey",
               how="left", suffixes=("", "_prod"))
    )

    # ── Step 4: Link failures → inventory gaps → demand ───────────────────────
    # Join failures to inv_gaps on SKUKey + LocationKey
    linked = failures.merge(
        inv_gaps.rename(columns={"DateKey": "InvDateKey"}),
        on=["SKUKey", "LocationKey"], how="inner"
    )

    # Join to demand on SKUKey + LocationKey, demand ships after delivery failure
    linked = linked.merge(
        demand[["SKUKey", "LocationKey", "ShipDateKey",
                "CustomerName", "SalesOrderNumber",
                "OutstandingQty", "UnitPrice"]],
        on=["SKUKey", "LocationKey"], how="inner"
    )

    # Only demand that ships on or after the inbound failure date
    linked = linked[linked["ShipDateKey"] >= linked["DeliveryDateKey"]]

    if linked.empty:
        return []

    def tier(p):
        if p >= 22: return "Tier 1"
        if p >= 18: return "Tier 2"
        return           "Tier 3"

    linked["Tier"]            = linked["UnitPrice"].apply(tier)
    linked["Revenue_At_Risk"] = (linked["OutstandingQty"] * linked["UnitPrice"]).round(2)

    # Deduplicate: one row per vendor-PO + customer-order combo
    linked = linked.drop_duplicates(
        subset=["PONumber", "SalesOrderNumber"]
    )

    result = (
        linked[[
            "VendorName", "PONumber", "DeliveryDateKey",
            "Commodity", "LocationCode",
            "Shortage", "NetAvailable",
            "CustomerName", "ShipDateKey",
            "OutstandingQty", "UnitPrice", "Tier",
            "Revenue_At_Risk",
        ]]
        .sort_values("Revenue_At_Risk", ascending=False)
        .reset_index(drop=True)
    )

    # Format date fields
    result["DeliveryDate"] = pd.to_datetime(
        result["DeliveryDateKey"].astype(int).astype(str), format="%Y%m%d"
    ).dt.strftime("%b %d")
    result["ShipDate"] = pd.to_datetime(
        result["ShipDateKey"].astype(int).astype(str), format="%Y%m%d"
    ).dt.strftime("%b %d")

    return result.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────