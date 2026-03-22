# Category Manager Analytics – Cloud + Power BI + Claude

## Overview
This repository contains an end‑to‑end analytics solution that ingests operational planning data, models it into a governed star schema, publishes a Power BI semantic model, and enables a Claude‑based assistant to support category manager decision‑making.

The solution is designed to:
- Consolidate inbound, sales, and planning data
- Preserve correct business granularity (SKU × Location × Date)
- Enable reliable Power BI reporting and KPIs
- Provide a structured context for Claude to generate accurate, explainable insights

This repo intentionally separates **data, model, documentation, and AI context** to avoid ambiguity and prevent incorrect assumptions.

---

## Business Problem
Category managers and planners need to answer questions such as:
- Do we have enough inventory to meet demand?
- Which SKUs are at risk of shortage or over‑supply?
- How reliable is inbound supply by vendor?
- Where are donations or waste increasing?
- How do supply, demand, and planning decisions connect?

These questions require **multiple datasets**, consistent definitions, and a **time‑aware analytical model**.

---

## Source Data (Inputs)
The solution is built from three primary operational sources:

1. **Inbound / CM Inbound Report**
   - Purchase orders and receipts
   - Expected vs received quantities
   - Vendor, SKU, location, delivery timing

2. **Sales / Orders (e.g., Beefsteak Sales)**
   - Customer demand and order quantities
   - Allocations, outstanding quantities
   - Ship and ready dates

3. **SKU Master**
   - Valid SKU list and attributes
   - Commodity, pack size, count, grade

All source definitions and column meanings are documented in: