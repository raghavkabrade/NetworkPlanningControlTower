"""
build_network_alerts.py
=======================
Calculates network shortage alerts at MPL Location × Commodity level.

Supply  = TotalSupply from Fact_Inventory at latest snapshot date, summed by Location × Commodity
Demand  = sum of OutstandingQty from Fact_Demand across all GOOD orders, by Location × Commodity
Shortage = max(Demand - Supply, 0)
Severity = Critical / High / Medium / Low based on shortage magnitude and % of demand

Outputs:
  Intermediate_Network_Alerts.csv     — one row per alert (location × commodity)
  Intermediate_Alert_Customers.csv    — customer + SKU detail rows per alert
"""

import os
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def severity(shortage: float, total_demand: float) -> str:
    pct = shortage / total_demand if total_demand > 0 else 0
    if shortage >= 2_000 or pct >= 0.50:
        return 'Critical'
    if shortage >= 1_000 or pct >= 0.30:
        return 'High'
    if shortage >= 500  or pct >= 0.15:
        return 'Medium'
    return 'Low'


def make_alert_id(location_code: str, commodity: str) -> str:
    return f"{location_code}-{commodity.replace(' ', '')}"


def main():
    fact_inv  = load('Fact_Inventory')
    fact_dem  = load('Fact_Demand')
    dim_prod  = load('Dim_Product')
    dim_loc   = load('Dim_Location')
    dim_cust  = load('Dim_Customer')

    mpl_locs = dim_loc[
        dim_loc['LocationType'] == 'MPL'
    ][['LocationKey', 'LocationCode']]

    # -- Supply: latest inventory snapshot ------------------------------------─
    latest_date = int(fact_inv['DateKey'].max())
    snap = fact_inv[fact_inv['DateKey'] == latest_date].copy()
    snap = snap.merge(mpl_locs,                          on='LocationKey', how='inner')
    snap = snap.merge(dim_prod[['SKUKey', 'Commodity']], on='SKUKey',      how='left')

    supply = (
        snap.groupby(['LocationCode', 'Commodity'])['TotalSupply']
        .sum().reset_index()
        .rename(columns={'TotalSupply': 'AvailableSupply'})
    )

    # -- Demand: all outstanding GOOD orders ------------------------------------
    dem = fact_dem[
        (fact_dem['SalesType']     == 'GOOD') &
        (fact_dem['OutstandingQty']  > 0) &
        (fact_dem['CustomerKey']    != -1)
    ].copy()

    dem = dem.merge(mpl_locs,                                                       on='LocationKey', how='inner')
    dem = dem.merge(dim_prod[['SKUKey', 'SKUCode', 'ProductDescription', 'Commodity']], on='SKUKey', how='left')
    dem = dem.merge(dim_cust[['CustomerKey', 'CustomerName', 'ShipToCode']],            on='CustomerKey', how='left')

    demand_agg = (
        dem.groupby(['LocationCode', 'Commodity'])['OutstandingQty']
        .sum().reset_index()
        .rename(columns={'OutstandingQty': 'TotalDemand'})
    )

    # -- Build alerts (shortage > 0 only) --------------------------------------
    alerts = supply.merge(demand_agg, on=['LocationCode', 'Commodity'], how='inner')
    alerts['Shortage']     = (alerts['TotalDemand'] - alerts['AvailableSupply']).clip(lower=0).round(0).astype(int)
    alerts                 = alerts[alerts['Shortage'] > 0].copy()
    alerts['FlatCutRate']  = (alerts['Shortage'] / alerts['TotalDemand']).round(4)
    alerts['Severity']     = alerts.apply(lambda r: severity(r['Shortage'], r['TotalDemand']), axis=1)
    alerts['AlertID']      = alerts.apply(lambda r: make_alert_id(r['LocationCode'], r['Commodity']), axis=1)
    alerts['SnapshotDate'] = latest_date
    alerts['AvailableSupply'] = alerts['AvailableSupply'].round(0).astype(int)
    alerts['TotalDemand']     = alerts['TotalDemand'].round(0).astype(int)
    alerts = alerts.sort_values('Shortage', ascending=False).reset_index(drop=True)

    out_alerts = os.path.join(CURATED, 'Intermediate_Network_Alerts.csv')
    alerts.to_csv(out_alerts, index=False)
    print(f' Network alerts: {len(alerts):,} rows  ->  {out_alerts}')

    # -- Customer × SKU breakdown per alert ------------------------------------
    alert_meta = alerts[['LocationCode', 'Commodity', 'AlertID', 'FlatCutRate']].copy()
    cust_dem   = dem.merge(alert_meta, on=['LocationCode', 'Commodity'], how='inner')

    # Format ShipDate
    cust_dem['ShipDate'] = pd.to_datetime(
        cust_dem['ShipDateKey'].astype(str), format='%Y%m%d'
    ).dt.strftime('%Y-%m-%d')

    # Aggregate to customer × SKU × ship date grain
    cust_detail = (
        cust_dem.groupby([
            'AlertID', 'LocationCode', 'Commodity',
            'CustomerKey', 'CustomerName', 'ShipToCode', 'ShipDate',
            'SKUKey', 'SKUCode', 'ProductDescription', 'FlatCutRate'
        ]).agg(
            OrderedQty = ('OutstandingQty', 'sum'),
            UnitPrice  = ('UnitPrice',       'mean'),
        ).reset_index()
    )
    cust_detail['UnitPrice']  = cust_detail['UnitPrice'].round(2)
    cust_detail['OrderedQty'] = cust_detail['OrderedQty'].round(0).astype(int)

    out_cust = os.path.join(CURATED, 'Intermediate_Alert_Customers.csv')
    cust_detail.to_csv(out_cust, index=False)
    print(f' Alert customers: {len(cust_detail):,} rows  ->  {out_cust}')

    return alerts, cust_detail


if __name__ == '__main__':
    main()
