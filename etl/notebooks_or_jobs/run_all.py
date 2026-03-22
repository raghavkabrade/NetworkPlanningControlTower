"""
run_all.py
==========
Master ETL runner — executes all build scripts in dependency order.

Execution order:
  1. build_safety_stock       (reads: Fact_Demand, Dim_Product, Dim_Location)
  2. build_customer_tiers     (reads: Fact_Demand, Dim_Product, Dim_Customer)
  3. build_missing_pos        (reads: Fact_Inbound, Dim_Location, Dim_Vendor, Dim_Product)
  4. build_network_alerts     (reads: Fact_Inventory, Fact_Demand, Dim_*)
  5. build_allocation_engine  (reads: Intermediate_Network_Alerts, Intermediate_Alert_Customers)
  6. build_suggested_po       (reads: Fact_Inventory, Fact_Inbound, Fact_Demand,
                                       Intermediate_Safety_Stock, Intermediate_Network_Alerts)
"""

import time

from build_safety_stock      import main as safety_stock
from build_customer_tiers    import main as customer_tiers
from build_missing_pos       import main as missing_pos
from build_network_alerts    import main as network_alerts
from build_allocation_engine import main as allocation_engine
from build_suggested_po      import main as suggested_po


def run():
    steps = [
        ('Safety Stock',       safety_stock),
        ('Customer Tiers',     customer_tiers),
        ('Missing POs',        missing_pos),
        ('Network Alerts',     network_alerts),
        ('Allocation Engine',  allocation_engine),
        ('Suggested PO',       suggested_po),
    ]

    t_total = time.time()
    for name, fn in steps:
        print(f'\n--- {name} ---')
        t0 = time.time()
        fn()
        print(f'   ({time.time() - t0:.1f}s)')

    print(f'\nAll steps complete  ({time.time() - t_total:.1f}s total)')


if __name__ == '__main__':
    run()
