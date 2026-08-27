# Pack v1 — janaavaaz-in-2026.1

A pack is a folder of CSVs plus manifest.yaml. The API never hard-codes a district list.
Canonical key is LGD district code.
Maps grounding may propose lat/lng. Ledger stores lgd_code. LGD wins.
If no indicator row exists for (lgd, sector), brief MUST set insufficient_official_data=true.
