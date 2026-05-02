# Delivery Challan Custom App - Project Specification

## Objective

Build a custom Delivery Challan app for ERPNext v16.

The Delivery Challan will act as a single operational platform for:

1. Material movement / warehouse transfer
2. Asset movement in a later phase

The app should support:

- dispatch details
- vehicle details
- source and target warehouse details
- item details
- receiver acknowledgement
- partial receipt
- shortage closure
- stock movement through standard ERPNext Stock Entry

## Core principle

Delivery Challan is not the stock ledger document.

Delivery Challan = operational dispatch and receipt control document

Stock Entry = actual ERPNext stock movement document

Asset Movement = actual ERPNext asset movement document, later phase

## Why custom Delivery Challan is required

ERPNext already has Stock Entry and Asset Movement.

However, operational users need one simple form for:

- preparing challan
- printing challan
- entering vehicle details
- dispatching material
- receiving material
- tracking partial delivery
- closing shortage
- future material indent integration
- future asset movement integration

Therefore, this app will wrap standard ERPNext movement documents behind a more practical operational workflow.

## Phase roadmap

### Phase 1 - Material Delivery Challan

Build:

- Delivery Challan parent DocType
- Delivery Challan Item child table
- mobile-friendly Add Material dialog
- Dispatch Material action
- Receive Material action
- Close Shortage action
- Stock Entry creation and linking

### Phase 2 - Asset Movement

Add:

- Delivery Challan Asset Item child table
- Asset dispatch and receipt workflow
- Asset Movement creation

Do not implement Phase 2 until specifically asked.

### Phase 3 - Material Indent Integration

Add:

- link to future Material Indent app
- reference fields
- requested quantity
- dispatched quantity
- received quantity
- balance quantity

Do not implement Phase 3 until specifically asked.

## Phase 1 movement model

Use the Transit Warehouse model.

Flow:

Draft
→ Submit
→ Pending Dispatch
→ Dispatch Material
→ In Transit
→ Receive Material
→ Partially Received / Received
→ Close Shortage if required

## Difference between DocStatus and business status

Frappe DocStatus:

- Draft
- Submitted
- Cancelled

Delivery Challan business status:

- Draft
- Pending Dispatch
- In Transit
- Partially Received
- Received
- Closed with Shortage
- Cancelled

## Submit behavior

When Delivery Challan is submitted:

- Frappe docstatus becomes Submitted.
- Business status becomes Pending Dispatch.
- No Stock Entry should be created.
- Stock should not move at submit stage.

Reason:

Submit only means challan has been approved/locked and is ready for dispatch. Actual vehicle dispatch may happen later.

## Dispatch behavior

When user clicks Dispatch Material:

- Validate source warehouse, target warehouse, transit warehouse.
- Validate all child rows.
- Create Stock Entry with purpose Material Transfer.
- Move material from Source Warehouse to Transit Warehouse.
- Link the created Stock Entry to Delivery Challan.
- Set dispatch datetime.
- Set dispatched by.
- Set business status as In Transit.

## Receipt behavior

When receiver clicks Receive Material:

- Show mobile-friendly receipt dialog.
- Display dispatched quantity, already received quantity, pending quantity.
- User enters newly received quantity.
- Validate newly received quantity does not exceed pending quantity.
- Create Stock Entry with purpose Material Transfer.
- Move material from Transit Warehouse to Target Warehouse.
- Update received quantity.
- Update pending quantity.
- If all items fully received, set status as Received.
- If some quantity pending, set status as Partially Received.

## Close Shortage behavior

Close Shortage is available only when status is Partially Received.

When user clicks Close Shortage, ask how pending quantity should be closed:

1. Book as Shortage / Loss
2. Return to Source Warehouse

### Book as Shortage / Loss

Create Stock Entry with purpose Material Issue.

Source warehouse:

Transit Warehouse

Quantity:

pending quantity

Result:

Pending quantity is removed from transit stock as shortage/loss.

### Return to Source Warehouse

Create Stock Entry with purpose Material Transfer.

Source warehouse:

Transit Warehouse

Target warehouse:

Original Source Warehouse

Quantity:

pending quantity

Result:

Pending quantity returns to source warehouse.

After either action:

- clear pending quantity logically
- set row status as Short Closed
- set Delivery Challan status as Closed with Shortage
- save shortage reason and shortage stock entry

## Warehouse logic

Parent Delivery Challan must have:

- source_warehouse
- target_warehouse
- transit_warehouse

Child table must also have:

- source_warehouse
- target_warehouse
- transit_warehouse

When adding an item, row warehouses should default from parent-level warehouses.

User must be able to override source/target/transit warehouse at row level.

Reason:

Most items may be going from one source to one target. But some items may need a different row-level warehouse.

## Mobile-first entry requirement

Child tables are difficult to use on mobile.

Therefore, mobile users should not be forced to work in the standard child table grid.

Phase 1 must add a custom button:

Add Material

This opens a simple dialog with:

- item
- quantity
- source warehouse
- target warehouse
- transit warehouse
- remarks

On Add:

- item row is inserted into the child table automatically
- item name and UOM are fetched
- warehouses are copied from the dialog
- child table refreshes

The child table remains visible for desktop users, but mobile users primarily use Add Material.

## Receipt mobile requirement

Receiver should not directly edit the wide child table grid.

Add button:

Receive Material

Dialog should show:

- item
- dispatched quantity
- already received quantity
- pending quantity
- newly received quantity

On receive:

- update child table in background
- create backend Stock Entry
- update status

## Important restrictions

- Do not directly update Stock Ledger Entry.
- Do not directly update Bin.
- Do not create Asset Movement in Phase 1.
- Do not create Material Indent logic in Phase 1.
- Do not move stock to target warehouse during dispatch.
- Do not move stock on Delivery Challan submit.
- Use Stock Entry only for stock movement.

## Future asset movement concept

Later, Delivery Challan may have a separate child table:

Delivery Challan Asset Item

Fields may include:

- asset
- asset name
- current location
- target location
- current custodian
- target custodian
- condition on dispatch
- condition on receipt
- received
- remarks

On receiver acceptance, system will create Asset Movement.

This is not part of Phase 1.

## Future material indent concept

Later, Delivery Challan may be created against Material Indent.

Possible future fields:

- reference doctype
- reference name
- material indent
- material indent item
- requested quantity
- dispatched quantity
- received quantity
- balance quantity

This is not part of Phase 1.