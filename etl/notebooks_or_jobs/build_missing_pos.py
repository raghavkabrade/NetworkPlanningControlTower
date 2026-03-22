"""
build_missing_pos.py
====================
Identifies inbound POs that are missing or partially received at MPL locations.
A PO is 'missing' when ReceivedQty < ExpectedQty (any positive shortage variance).

Aggregates to PO × Location × DeliveryDate grain with total shortage, severity, and commodity list.

Output: data/curated/Intermediate_Missing_POs.csv
Columns:
  PONumber, VendorName, LocationCode, DeliveryDate,
  ExpectedQty, ReceivedQty, ShortageQty, FillRatePct,
  Commodities, Severity
"""

import os
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def severity(shortage: float) -> str:
    if shortage >= 2_000:
        return 'Critical'
    if shortage >= 1_000:
        return 'High'
    if shortage >= 500:
        return 'Medium'
    return 'Low'


def main() -> pd.DataFrame:
    fact_ib  = load('Fact_Inbound')
    dim_loc  = load('Dim_Location')
    dim_vend = load('Dim_Vendor')
    dim_prod = load('Dim_Product')

    mpl_locs = dim_loc[
        dim_loc['LocationType'] == 'MPL'
    ][['LocationKey', 'LocationCode']]

    # Use the inventory snapshot date as "today" — only flag POs already due
    fact_inv   = load('Fact_Inventory')
    snapshot   = int(fact_inv['DateKey'].max())

    ib = fact_ib.copy()
    ib['ReceivedQty'] = ib['ReceivedQty'].fillna(0)
    ib['ShortageQty'] = ib['ExpectedQty'] - ib['ReceivedQty']

    # Only rows with a positive shortage AND delivery date <= snapshot (already due)
    missing = ib[(ib['ShortageQty'] > 0) & (ib['DeliveryDateKey'] <= snapshot)].copy()
    missing = missing.merge(mpl_locs,                          on='LocationKey',    how='inner')
    missing = missing.merge(dim_vend[['VendorKey', 'VendorName']], on='VendorKey', how='left')
    missing = missing.merge(dim_prod[['SKUKey', 'Commodity']],     on='SKUKey',    how='left')

    missing['DeliveryDate'] = pd.to_datetime(
        missing['DeliveryDateKey'].astype(str), format='%Y%m%d'
    ).dt.strftime('%Y-%m-%d')

    # Aggregate to PO × Location × DeliveryDate
    po_agg = (
        missing.groupby(['PONumber', 'VendorName', 'LocationCode', 'DeliveryDate'])
        .agg(
            ExpectedQty  = ('ExpectedQty',  'sum'),
            ReceivedQty  = ('ReceivedQty',  'sum'),
            ShortageQty  = ('ShortageQty',  'sum'),
            Commodities  = ('Commodity', lambda x: ', '.join(sorted(x.dropna().unique()))),
        )
        .reset_index()
    )

    po_agg['FillRatePct'] = (
        po_agg['ReceivedQty'] / po_agg['ExpectedQty'].replace(0, float('nan')) * 100
    ).round(1).fillna(0)

    po_agg['Severity'] = po_agg['ShortageQty'].apply(severity)

    po_agg['ExpectedQty'] = po_agg['ExpectedQty'].round(0).astype(int)
    po_agg['ReceivedQty'] = po_agg['ReceivedQty'].round(0).astype(int)
    po_agg['ShortageQty'] = po_agg['ShortageQty'].round(0).astype(int)

    po_agg = po_agg.sort_values(
        ['LocationCode', 'ShortageQty'], ascending=[True, False]
    ).reset_index(drop=True)

    out = os.path.join(CURATED, 'Intermediate_Missing_POs.csv')
    po_agg.to_csv(out, index=False)
    print(f' Missing POs: {len(po_agg):,} rows  ->  {out}')
    return po_agg


if __name__ == '__main__':
    main()
