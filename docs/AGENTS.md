# AGENTS.md

## Project

This project is for a Frappe/ERPNext v16 custom app named:

delivery_challan_custom

Development site:

erp.jewonline.in

Development server:

frappe@187.127.132.58

Bench path on server:

~/frappe-bench

## Main objective

Build a custom Delivery Challan app for ERPNext v16.

The Delivery Challan is an operational dispatch and receipt control document. It should not directly modify stock ledger, Bin, or asset records.

Standard ERPNext backend documents must be used:

- Material movement: Stock Entry
- Asset movement: Asset Movement, in a later phase only

## Current phase

Current implementation phase is:

Phase 1 - Material Delivery Challan only

Do not implement these yet:

- Asset movement
- Material indent integration
- Barcode scanning
- Separate mobile app
- Advanced dashboard
- Advanced report
- Production deployment automation

## Very important Frappe creation rule

Do not manually create DocType folders and JSON files from scratch.

Whenever a new DocType, child DocType, Page, Report, Workspace, Print Format, or similar Frappe object is required:

1. First generate it using Frappe's own tools on the dev server.
2. Preferred methods:
   - bench --site erp.jewonline.in console with Python script
   - bench new-app for app creation
   - Frappe UI / Developer Mode where suitable
3. Only after Frappe has generated the files, edit the generated files.

Reason:

System-generated Frappe files create the correct folder structure, __init__.py files, JSON structure, JS files, PY controller files, and metadata.

This rule is strict.

## Development workflow

The user is developing locally first.

Workflow:

1. Prepare planning/spec files locally.
2. Let Codex generate or edit code locally.
3. Use the dev server to generate Frappe objects using bench console.
4. Pull/copy generated files back if required.
5. Let Codex edit the generated files.
6. Copy files to server using scp or Git.
7. Run migration/build commands on dev server.
8. Test on erp.jewonline.in.
9. Commit and push to GitHub only after successful testing.

## Safety rules

- Do not directly update Stock Ledger Entry.
- Do not directly update Bin.
- Do not directly update Asset records.
- Do not bypass ERPNext accounting or stock logic.
- Always create proper Stock Entry for material movement.
- Asset Movement is for later phases only.
- Do not make stock move on Delivery Challan submit.
- Do not move stock to target warehouse until receiver accepts.

## Required implementation approach

Delivery Challan = operational control document

Stock Entry = actual stock movement document

Phase 1 material movement must use the Transit Warehouse model:

1. On Submit:
   - Delivery Challan becomes submitted.
   - Business status becomes Pending Dispatch.
   - No Stock Entry is created.

2. On Dispatch:
   - Create Stock Entry Material Transfer.
   - Move material from Source Warehouse to Transit Warehouse.
   - Status becomes In Transit.

3. On Receipt:
   - Create Stock Entry Material Transfer.
   - Move received quantity from Transit Warehouse to Target Warehouse.
   - Status becomes Partially Received or Received.

4. On Close Shortage:
   - Either book pending quantity as shortage/loss from Transit Warehouse.
   - Or return pending quantity from Transit Warehouse to Source Warehouse.

## Coding style

- Follow Frappe/ERPNext v16 conventions.
- Keep business logic in Python controller methods and whitelisted functions.
- Keep mobile-friendly form actions in client-side JS.
- Use clear fieldnames.
- Use safe validations.
- Do not perform large unrelated refactors.
- Do not change existing apps unless specifically required.

## Before coding

Before making changes, inspect:

- existing app structure
- Frappe/ERPNext Stock Entry patterns
- generated DocType files
- hooks.py
- modules.txt
- pyproject.toml or setup files if present

Then explain:

- files to be created
- files to be changed
- server commands needed
- test plan

## After coding

Always provide:

- changed files
- migration commands
- build commands if needed
- test steps
- rollback notes
- known limitations