"""
build_safety_stock.py
=====================
Calculates safety stock per MPL Location × Commodity.

Formula:  SafetyStock = ceil(AvgDailyDemand × LeadTimeDays / ROUND_TO) × ROUND_TO
          where AvgDailyDemand = mean of daily OutstandingQty across all ship dates
                LeadTimeDays   = 1.5  (configurable below)
                ROUND_TO       = 50 cases

Output: data/curated/Intermediate_Safety_Stock.csv
Columns:
  LocationCode, Commodity, AvgDailyDemand, LeadTimeDays, SafetyStock
"""

import os
import math
import pandas as pd

# -- Config --------------------------------------------------------------------
CURATED       = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'curated'))
LEAD_TIME     = 1.5   # days
ROUND_TO      = 50    # round up to nearest N cases
MIN_SS        = 50    # minimum safety stock even if demand is very low

def load(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(CURATED, f'{name}.csv'))


def main() -> pd.DataFrame:
    fact_demand  = load('Fact_Demand')
    dim_product  = load('Dim_Product')
    dim_location = load('Dim_Location')

    # MPL locations only (planning locations)
    mpl_locs = dim_location[dim_location['LocationType'] == 'MPL'][['LocationKey', 'LocationCode']]

    # GOOD sales with outstanding demand
    demand = fact_demand[
        (fact_demand['SalesType'] == 'GOOD') &
        (fact_demand['OutstandingQty'] > 0)
    ].copy()

    # Attach commodity and MPL location
    demand = demand.merge(dim_product[['SKUKey', 'Commodity']], on='SKUKey', how='left')
    demand = demand.merge(mpl_locs, on='LocationKey', how='inner')

    # Daily demand per Location × Commodity × ShipDate
    daily = (
        demand.groupby(['LocationCode', 'Commodity', 'ShipDateKey'])['OutstandingQty']
        .sum()
        .reset_index(name='DailyDemand')
    )

    # Average daily demand across all ship dates
    avg = (
        daily.groupby(['LocationCode', 'Commodity'])['DailyDemand']
        .mean()
        .reset_index(name='AvgDailyDemand')
    )

    avg['LeadTimeDays']    = LEAD_TIME
    avg['SafetyStock_Raw'] = avg['AvgDailyDemand'] * LEAD_TIME
    avg['SafetyStock']     = avg['SafetyStock_Raw'].apply(
        lambda x: max(math.ceil(x / ROUND_TO) * ROUND_TO, MIN_SS)
    ).astype(int)

    result = avg[['LocationCode', 'Commodity', 'AvgDailyDemand', 'LeadTimeDays', 'SafetyStock']].copy()
    result['AvgDailyDemand'] = result['AvgDailyDemand'].round(1)

    out = os.path.join(CURATED, 'Intermediate_Safety_Stock.csv')
    result.to_csv(out, index=False)
    print(f' Safety stock: {len(result):,} rows  ->  {out}')
    return result


if __name__ == '__main__':
    main()
