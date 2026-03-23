# Data Model — Category Manager Control Tower

## Key Insight: Two SKU Universes

Before looking at the joins, one structural fact drives everything in this model:

| Prefix | Meaning | Appears In |
|---|---|---|
| `RT*` | Raw / Bulk SKU — unprocessed commodity | cm_inbound, planning_inventory, planning_transfers |
| `FT*` | Finished / Packed SKU — packed, ready to sell | planning_sales, planning_production, sales |

The production step (`planning_production`) is the **bridge** — it consumes `RT*` raw material and outputs `FT*` finished SKUs. Every shortage alert and pack schedule recommendation ultimately traces back through this bridge.

---

## Entity Relationship Diagram

```mermaid
erDiagram

    CM_INBOUND {
        date    DeliveryDate       PK
        string  Location           PK
        string  PONumber           PK
        string  VendorCode
        string  Vendor
        string  ItemNo_RT          FK
        string  Commodity
        string  Description
        float   ExpectedQty
        float   ReceivedQty
        string  Status
    }

    PLANNING_INVENTORY {
        string  ItemNo_RT          PK
        string  Location           PK
        date    WorkDate           PK
        float   Quantity
        date    ShipmentDate
        string  OrderNo
    }

    PLANNING_TRANSFERS {
        string  DocumentNo         PK
        string  ItemNo_RT          FK
        string  TransferFromCode   FK
        string  TransferToCode     FK
        date    ReadyDate
        date    ReceiptDate
        float   QtyShipped
        float   QtyOutstanding
        float   QtyInTransit
        float   QtyReceived
    }

    PLANNING_PURCHASES {
        string  DocumentNo         PK
        string  ItemNo_RT          FK
        string  LocationCode       FK
        string  VendorName
        date    ExpectedReceiptDate
        float   Quantity
    }

    PLANNING_PRODUCTION {
        string  ProdOrderNo        PK
        string  ItemNo_FT          FK
        string  LocationCode       FK
        date    EndingDate
        float   PlannedQty
        float   RemainingQty
        float   FinishedQty
        string  ProductionReason
    }

    PLANNING_SALES {
        string  DocumentNo         PK
        string  ItemNo_FT          FK
        string  LocationCode       FK
        string  CustomerName
        float   OutstandingQty
        date    ReadyDate
        string  CustomerSalesType
    }

    SALES {
        string  SourceID           PK
        string  ItemNo_FT          FK
        string  ShippingLocation   FK
        string  DestinationName
        date    ShipmentDate
        date    ReadyDate
        float   OriginalQty
        float   OutstandingQty
        float   UnitPrice
        string  CustomerSalesType
        string  AllocationFlag
    }

    NET_AVAILABLE_INVENTORY {
        string  ItemNo             PK
        string  Location           PK
        date    Date               PK
        float   InventoryOnHand
        float   InboundExpected
        float   TransfersIn
        float   TransfersOut
        float   PackedOutput
        float   Demand
        float   NetAvailable
    }

    SHORTAGE_ALERTS {
        string  ItemNo             PK
        string  Location           PK
        date    ShortageDate       PK
        float   Demand
        float   Supply
        float   Gap
        string  Severity
    }

    PACK_SCHEDULE {
        string  ItemNo_FT          PK
        string  Location           PK
        date    PackDate           PK
        date    ShipDate
        float   SuggestedPackQty
        float   FeasiblePackQty
        float   RawLbsRequired
        float   RawLbsAvailable
        bool    RawConstrained
        string  Severity
    }

    %% Raw material joins (RT* SKUs)
    PLANNING_INVENTORY   ||--o{ CM_INBOUND          : "ItemNo_RT + Location"
    PLANNING_INVENTORY   ||--o{ PLANNING_TRANSFERS   : "ItemNo_RT + Location"
    PLANNING_INVENTORY   ||--o{ PLANNING_PURCHASES   : "ItemNo_RT + LocationCode"

    %% Production bridge: RT → FT
    PLANNING_INVENTORY   ||--o{ PLANNING_PRODUCTION  : "Location (raw consumed → finished output)"

    %% Finished goods joins (FT* SKUs)
    PLANNING_PRODUCTION  ||--o{ PLANNING_SALES       : "ItemNo_FT + LocationCode"
    PLANNING_PRODUCTION  ||--o{ SALES                : "ItemNo_FT + ShippingLocation"
    PLANNING_SALES       ||--o{ SALES                : "DocumentNo = SourceID"

    %% Outputs derived from above
    PLANNING_INVENTORY   ||--|| NET_AVAILABLE_INVENTORY : "base inventory position"
    CM_INBOUND           ||--|| NET_AVAILABLE_INVENTORY : "adds expected inbound"
    PLANNING_TRANSFERS   ||--|| NET_AVAILABLE_INVENTORY : "adds/subtracts transfers"
    PLANNING_PRODUCTION  ||--|| NET_AVAILABLE_INVENTORY : "adds packed output"
    PLANNING_SALES       ||--|| NET_AVAILABLE_INVENTORY : "subtracts demand"
    SALES                ||--|| NET_AVAILABLE_INVENTORY : "subtracts demand (full detail)"

    NET_AVAILABLE_INVENTORY ||--|| SHORTAGE_ALERTS   : "where NetAvailable < threshold"
    NET_AVAILABLE_INVENTORY ||--|| PACK_SCHEDULE      : "drives suggested pack qty"
    PLANNING_INVENTORY      ||--|| PACK_SCHEDULE      : "raw material constraint check"
```

---

## Join Keys Reference

| Join | Left Table | Left Key | Right Table | Right Key | Type |
|---|---|---|---|---|---|
| Raw inventory ↔ Inbound | planning_inventory | ItemNo + Location | cm_inbound | Item No. + Location | 1:M |
| Raw inventory ↔ Transfers | planning_inventory | ItemNo + Location | planning_transfers | Item No. + Transfer-from Code | 1:M |
| Raw inventory ↔ Purchases | planning_inventory | ItemNo + Location Code | planning_purchases | Item No. + Location Code | 1:M |
| Raw ↔ Production (bridge) | planning_inventory | Location | planning_production | Location Code | 1:M |
| Production ↔ Sales (planning) | planning_production | Item No. + Location Code | planning_sales | Item No. + Location Code | 1:M |
| Production ↔ Sales (actuals) | planning_production | Item No. + Location Code | sales | Item No. + Shipping Location | 1:M |
| Planning sales ↔ Sales actuals | planning_sales | Document No. | sales | Source ID | 1:1 |

---

## Data Flow: From Source to Output

```
LAYER 1 — RAW MATERIAL POSITION
┌─────────────────────┐     ┌──────────────────────┐     ┌───────────────────────┐
│  planning_inventory  │     │     cm_inbound        │     │  planning_purchases   │
│  (RT* on-hand stock) │     │  (RT* inbound POs)   │     │  (RT* open POs)       │
│  ItemNo, Location,   │     │  Item No., Location,  │     │  Item No., Location,  │
│  WorkDate, Quantity  │     │  ExpectedQty, Status  │     │  ExpectedReceiptDate  │
└────────┬────────────┘     └──────────┬───────────┘     └──────────┬────────────┘
         │                             │                              │
         └─────────────────────────────┴──────────────────────────────┘
                                       │
                              JOIN on ItemNo + Location
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │  Raw Material Position  │
                          │  On Hand + Expected In  │
                          │  - Already Committed    │
                          └────────────┬───────────┘
                                       │
                                       ▼
LAYER 2 — PRODUCTION BRIDGE (RT* → FT*)
                          ┌────────────────────────┐
                          │  planning_production    │
                          │  (FT* pack runs)        │
                          │  ItemNo_FT, Location,   │
                          │  Quantity, RemainingQty  │
                          └────────────┬───────────┘
                                       │
              Consumes RT* bulk  →  Outputs FT* finished cases
                                       │
LAYER 3 — TRANSFERS (RT* between facilities)
         ┌─────────────────────────────┘
         │    ┌───────────────────────┐
         │    │  planning_transfers   │
         │    │  Item No., From, To   │
         │    │  QtyShipped, InTransit│
         │    └──────────┬────────────┘
         │               │
         └───────────────┘
                         │
                         ▼
LAYER 4 — DEMAND
         ┌───────────────────────────────────────────┐
         │                                           │
┌────────┴───────────┐                   ┌───────────┴───────────┐
│  planning_sales     │                   │       sales            │
│  (FT* open orders)  │ ◄── DocumentNo ──► │  (FT* full order line) │
│  OutstandingQty     │   = Source ID     │  OriginalQty,          │
│  ReadyDate,         │                   │  OutstandingQty,       │
│  CustomerSalesType  │                   │  UnitPrice, Allocation │
└────────┬───────────┘                   └───────────┬───────────┘
         │                                           │
         └─────────────────────┬─────────────────────┘
                               │
                               ▼
LAYER 5 — NET AVAILABLE INVENTORY (calculated)
┌──────────────────────────────────────────────────────────────┐
│  NetAvailable = Inventory On Hand                             │
│              + Expected Inbound (cm_inbound)                 │
│              + Packed Output (planning_production)           │
│              + Transfers In (planning_transfers)             │
│              - Transfers Out (planning_transfers)            │
│              - Demand (planning_sales / sales)               │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
┌──────────────────────┐         ┌─────────────────────────┐
│   SHORTAGE ALERTS     │         │    PACK SCHEDULE         │
│  Where NetAvailable   │         │  Suggested pack qty to   │
│  < Safety Stock       │         │  cover the gap, checked  │
│  → Severity flagging  │         │  against raw material    │
│  → Customer allocation│         │  availability (Layer 1)  │
└──────────────────────┘         └─────────────────────────┘
```

---

## Notes on Data Gaps

The model above works end-to-end for shortage detection and customer allocation.
The pack schedule engine additionally requires three inputs **not yet in the raw files**:

| Missing Input | Blocks | Workaround |
|---|---|---|
| Raw material availability (lbs) | Pack feasibility check | Use planning_inventory Quantity as proxy (cases, not lbs) |
| SKU yield rate (cases/lb) | Raw lbs required calculation | Estimate from pack weight in Description field |
| Shelf life per SKU | JIT pack window | Default to 10 days until confirmed |
