"""
build_allocation_engine.py
==========================
Applies tier-based cut logic to every customer × SKU row within each network alert.

Tier assignment (per SKU unit price):
  Tier 1 (>=22): 0% cut
  Tier 2 (18–22): flatRate × 0.5 cut  (protected partial cut)
  Tier 3 (<18):  flatRate × 2.0 cut   (capped at 100%)

Revenue comparison:
  FlatRevenue = what we'd earn if every customer took the same flat % cut
  TierRevenue = what we earn with the tiered cut model
  RevenueSaved = TierRevenue - FlatRevenue  (always >= 0)

Outputs:
  Intermediate_Allocation_Engine.csv   — one row per alert × customer × SKU
  Intermediate_Alert_Revenue.csv       — revenue summary per alert
"""

import os
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))

TIER_1_PRICE = 22.0
TIER_2_PRICE = 18.0
TIER_RANK    = {'Tier 1': 0, 'Tier 2': 1, 'Tier 3': 2}


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def assign_tier(price: float) -> str:
    if price >= TIER_1_PRICE:
        return 'Tier 1'
    if price >= TIER_2_PRICE:
        return 'Tier 2'
    return 'Tier 3'


def cut_rate(tier: str, flat_rate: float) -> float:
    if tier == 'Tier 1':
        return 0.0
    if tier == 'Tier 2':
        return min(flat_rate * 0.5, 1.0)
    return min(flat_rate * 2.0, 1.0)


def main():
    alerts   = load('Intermediate_Network_Alerts')
    cust_det = load('Intermediate_Alert_Customers')

    # -- Tier and cut calculation per SKU row ----------------------------------
    cust_det['Tier']     = cust_det['UnitPrice'].apply(assign_tier)
    cust_det['CutRate']  = cust_det.apply(
        lambda r: cut_rate(r['Tier'], r['FlatCutRate']), axis=1
    ).round(4)

    cust_det['SuggestedCut']   = (cust_det['OrderedQty'] * cust_det['CutRate']).round(0).astype(int)
    cust_det['SuggestedAlloc'] = cust_det['OrderedQty'] - cust_det['SuggestedCut']
    cust_det['FillPct']        = (
        cust_det['SuggestedAlloc'] / cust_det['OrderedQty'].replace(0, 1) * 100
    ).round(1)

    # Revenue metrics
    cust_det['TierRevenue'] = (cust_det['SuggestedAlloc'] * cust_det['UnitPrice']).round(2)
    cust_det['FlatAlloc']   = (cust_det['OrderedQty'] * (1 - cust_det['FlatCutRate'])).round(0).astype(int)
    cust_det['FlatRevenue'] = (cust_det['FlatAlloc']   * cust_det['UnitPrice']).round(2)
    cust_det['RevenueSaved'] = (cust_det['TierRevenue'] - cust_det['FlatRevenue']).round(2)

    # -- Highest tier per customer (for row highlight) ------------------------─
    def highest_tier(group):
        return group.loc[group['Tier'].map(TIER_RANK).idxmin(), 'Tier']

    cust_tier = (
        cust_det.groupby(['AlertID', 'CustomerKey', 'CustomerName'])
        .apply(highest_tier)
        .reset_index(name='HighestTier')
    )
    cust_det = cust_det.merge(
        cust_tier, on=['AlertID', 'CustomerKey', 'CustomerName'], how='left'
    )

    out_alloc = os.path.join(CURATED, 'Intermediate_Allocation_Engine.csv')
    cust_det.to_csv(out_alloc, index=False)
    print(f' Allocation engine: {len(cust_det):,} rows  ->  {out_alloc}')

    # -- Revenue summary per alert --------------------------------------------─
    rev = (
        cust_det.groupby('AlertID')
        .agg(
            TotalTierRevenue  = ('TierRevenue',  'sum'),
            TotalFlatRevenue  = ('FlatRevenue',  'sum'),
            TotalRevenueSaved = ('RevenueSaved', 'sum'),
        )
        .reset_index()
    )
    rev = rev.round(0).astype({
        'TotalTierRevenue': int, 'TotalFlatRevenue': int, 'TotalRevenueSaved': int
    })

    out_rev = os.path.join(CURATED, 'Intermediate_Alert_Revenue.csv')
    rev.to_csv(out_rev, index=False)
    print(f' Alert revenue:    {len(rev):,} rows  ->  {out_rev}')

    return cust_det, rev


if __name__ == '__main__':
    main()
