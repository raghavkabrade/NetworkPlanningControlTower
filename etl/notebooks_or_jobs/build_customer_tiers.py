"""
build_customer_tiers.py
=======================
Calculates customer tier per Customer × Commodity based on
weighted-average unit price across all outstanding GOOD orders.

Tier logic:
  Tier 1  — avg unit price >= $22  (High Margin)
  Tier 2  — avg unit price $18–$22 (Standard)
  Tier 3  — avg unit price <  $18  (Flexible / Low Margin)

Output: data/curated/Intermediate_Customer_Tiers.csv
Columns:
  CustomerKey, CustomerName, ShipToCode, Commodity,
  AvgUnitPrice, Tier, TotalOutstandingQty, TotalRevenuePotential
"""

import os
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))

TIER_1_THRESHOLD = 22.0
TIER_2_THRESHOLD = 18.0


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def assign_tier(price: float) -> str:
    if price >= TIER_1_THRESHOLD:
        return 'Tier 1'
    if price >= TIER_2_THRESHOLD:
        return 'Tier 2'
    return 'Tier 3'


def main() -> pd.DataFrame:
    fact_demand  = load('Fact_Demand')
    dim_product  = load('Dim_Product')
    dim_customer = load('Dim_Customer')

    # GOOD sales with valid customers and outstanding demand
    demand = fact_demand[
        (fact_demand['SalesType']    == 'GOOD') &
        (fact_demand['CustomerKey']  != -1) &
        (fact_demand['OutstandingQty'] > 0) &
        (fact_demand['UnitPrice']    > 0)
    ].copy()

    demand = demand.merge(
        dim_product[['SKUKey', 'Commodity']], on='SKUKey', how='left'
    )

    # Weighted average unit price per Customer × Commodity
    demand['Revenue'] = demand['OutstandingQty'] * demand['UnitPrice']

    agg = (
        demand.groupby(['CustomerKey', 'Commodity'])
        .agg(
            TotalOutstandingQty    = ('OutstandingQty', 'sum'),
            TotalRevenuePotential  = ('Revenue',         'sum'),
        )
        .reset_index()
    )
    agg['AvgUnitPrice'] = (
        agg['TotalRevenuePotential'] / agg['TotalOutstandingQty']
    ).round(2)
    agg['Tier'] = agg['AvgUnitPrice'].apply(assign_tier)

    # Attach customer names
    agg = agg.merge(
        dim_customer[['CustomerKey', 'CustomerName', 'ShipToCode']],
        on='CustomerKey', how='left'
    )

    result = agg[[
        'CustomerKey', 'CustomerName', 'ShipToCode', 'Commodity',
        'AvgUnitPrice', 'Tier', 'TotalOutstandingQty', 'TotalRevenuePotential'
    ]].sort_values(['Commodity', 'Tier', 'CustomerName']).reset_index(drop=True)

    result['TotalRevenuePotential'] = result['TotalRevenuePotential'].round(2)

    out = os.path.join(CURATED, 'Intermediate_Customer_Tiers.csv')
    result.to_csv(out, index=False)
    print(f' Customer tiers: {len(result):,} rows  ->  {out}')
    return result


if __name__ == '__main__':
    main()
