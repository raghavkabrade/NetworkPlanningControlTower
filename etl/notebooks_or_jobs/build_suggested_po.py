"""
build_suggested_po.py
=====================
Builds a daily inventory timeline per MPL Location × Commodity for each
active network alert. Projects opening inventory forward using expected
inbound POs and outstanding demand by ship date.

Columns per day:
  Date, OpeningInventory, Inbound, InboundVendors, Demand,
  EndInventory, Buffer, SafetyStock, SuggestedPOQty

SuggestedPOQty = ceil((SafetyStock - EndInventory) / ROUND_TO) * ROUND_TO
                 when EndInventory < SafetyStock, else 0

Output: data/curated/Intermediate_Suggested_PO.csv
"""

import os
import math
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED  = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))
ROUND_TO = 50
HORIZON  = 14  # days to project forward


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def suggested_po(end_inv: float, safety_stock: float) -> int:
    gap = safety_stock - end_inv
    if gap <= 0:
        return 0
    return math.ceil(gap / ROUND_TO) * ROUND_TO


def main() -> pd.DataFrame:
    fact_inv  = load('Fact_Inventory')
    fact_dem  = load('Fact_Demand')
    fact_ib   = load('Fact_Inbound')
    dim_prod  = load('Dim_Product')
    dim_loc   = load('Dim_Location')
    dim_vend  = load('Dim_Vendor')
    ss        = load('Intermediate_Safety_Stock')
    alerts    = load('Intermediate_Network_Alerts')

    mpl_locs = dim_loc[dim_loc['LocationType'] == 'MPL'][['LocationKey', 'LocationCode']]

    # -- Opening inventory: latest snapshot per Location × Commodity ------------
    latest_date = int(fact_inv['DateKey'].max())
    snap = fact_inv[fact_inv['DateKey'] == latest_date].copy()
    snap = snap.merge(mpl_locs, on='LocationKey', how='inner')
    snap = snap.merge(dim_prod[['SKUKey', 'Commodity']], on='SKUKey', how='left')

    opening = (
        snap.groupby(['LocationCode', 'Commodity'])['TotalSupply']
        .sum().reset_index()
        .rename(columns={'TotalSupply': 'OpeningInventory'})
    )

    # -- Future inbounds: pending POs (ReceivedQty < ExpectedQty) --------------
    ib = fact_ib.copy()
    ib['ReceivedQty'] = ib['ReceivedQty'].fillna(0)
    ib['PendingQty']  = (ib['ExpectedQty'] - ib['ReceivedQty']).clip(lower=0)
    ib = ib[ib['PendingQty'] > 0]
    ib = ib.merge(mpl_locs, on='LocationKey', how='inner')
    ib = ib.merge(dim_prod[['SKUKey', 'Commodity']], on='SKUKey', how='left')
    ib = ib.merge(dim_vend[['VendorKey', 'VendorName']], on='VendorKey', how='left')

    ib['DeliveryDate'] = pd.to_datetime(
        ib['DeliveryDateKey'].astype(str), format='%Y%m%d'
    ).dt.strftime('%Y-%m-%d')

    inbound_daily = (
        ib.groupby(['LocationCode', 'Commodity', 'DeliveryDate'])
        .agg(
            Inbound        = ('PendingQty', 'sum'),
            InboundVendors = ('VendorName', lambda x: ', '.join(sorted(x.dropna().unique()))),
        )
        .reset_index()
    )

    # -- Future demand: outstanding GOOD orders by ship date ------------------─
    dem = fact_dem[
        (fact_dem['SalesType']    == 'GOOD') &
        (fact_dem['OutstandingQty'] > 0) &
        (fact_dem['CustomerKey']  != -1)
    ].copy()
    dem = dem.merge(mpl_locs, on='LocationKey', how='inner')
    dem = dem.merge(dim_prod[['SKUKey', 'Commodity']], on='SKUKey', how='left')

    dem['ShipDate'] = pd.to_datetime(
        dem['ShipDateKey'].astype(str), format='%Y%m%d'
    ).dt.strftime('%Y-%m-%d')

    demand_daily = (
        dem.groupby(['LocationCode', 'Commodity', 'ShipDate'])['OutstandingQty']
        .sum().reset_index()
        .rename(columns={'ShipDate': 'Date', 'OutstandingQty': 'Demand'})
    )
    inbound_daily = inbound_daily.rename(columns={'DeliveryDate': 'Date'})

    # -- Build timeline for each alert ----------------------------------------─
    snapshot_dt = pd.to_datetime(str(latest_date), format='%Y%m%d')
    date_range  = [
        (snapshot_dt + pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(1, HORIZON + 1)
    ]

    rows = []
    for _, alert in alerts.iterrows():
        loc  = alert['LocationCode']
        comm = alert['Commodity']
        aid  = alert['AlertID']

        open_inv_val = opening.loc[
            (opening['LocationCode'] == loc) & (opening['Commodity'] == comm),
            'OpeningInventory'
        ]
        open_inv = float(open_inv_val.values[0]) if len(open_inv_val) else 0.0

        ss_val = ss.loc[
            (ss['LocationCode'] == loc) & (ss['Commodity'] == comm),
            'SafetyStock'
        ]
        safety_stock = int(ss_val.values[0]) if len(ss_val) else 0

        running_inv = open_inv
        for dt in date_range:
            ib_row = inbound_daily.loc[
                (inbound_daily['LocationCode'] == loc) &
                (inbound_daily['Commodity']    == comm) &
                (inbound_daily['Date']         == dt)
            ]
            dem_row = demand_daily.loc[
                (demand_daily['LocationCode'] == loc) &
                (demand_daily['Commodity']    == comm) &
                (demand_daily['Date']         == dt)
            ]

            inbound_qty     = float(ib_row['Inbound'].values[0])        if len(ib_row)  else 0.0
            inbound_vendors = ib_row['InboundVendors'].values[0]        if len(ib_row)  else ''
            demand_qty      = float(dem_row['Demand'].values[0])        if len(dem_row) else 0.0

            end_inv    = running_inv + inbound_qty - demand_qty
            buffer     = end_inv - safety_stock
            po_suggest = suggested_po(end_inv, safety_stock)

            rows.append({
                'AlertID':         aid,
                'LocationCode':    loc,
                'Commodity':       comm,
                'Date':            dt,
                'OpeningInventory': round(running_inv, 0),
                'Inbound':         round(inbound_qty, 0),
                'InboundVendors':  inbound_vendors,
                'Demand':          round(demand_qty, 0),
                'EndInventory':    round(end_inv, 0),
                'SafetyStock':     safety_stock,
                'Buffer':          round(buffer, 0),
                'SuggestedPOQty':  po_suggest,
            })

            running_inv = end_inv

    result = pd.DataFrame(rows)
    result['OpeningInventory'] = result['OpeningInventory'].astype(int)
    result['Inbound']          = result['Inbound'].astype(int)
    result['Demand']           = result['Demand'].astype(int)
    result['EndInventory']     = result['EndInventory'].astype(int)
    result['Buffer']           = result['Buffer'].astype(int)

    out = os.path.join(CURATED, 'Intermediate_Suggested_PO.csv')
    result.to_csv(out, index=False)
    print(f' Suggested PO timeline: {len(result):,} rows  ->  {out}')
    return result


if __name__ == '__main__':
    main()
