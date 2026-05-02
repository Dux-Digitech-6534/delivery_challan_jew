# Phase 1 - Material Delivery Challan

## Goal

Implement Material Delivery Challan only.

Do not implement:

- asset movement
- material indent integration
- barcode scanning
- advanced dashboard
- production deployment automation

## App name

delivery_challan_custom

## Site

erp.jewonline.in

## Required DocTypes

### Delivery Challan

Type:

Submittable parent DocType

Module:

Delivery Challan Custom

Suggested field list:

1. naming_series
   - Type: Select
   - Default: DC-.YYYY.-.#####
   - Required

2. company
   - Type: Link
   - Options: Company
   - Required

3. posting_date
   - Type: Date
   - Default: Today
   - Required

4. posting_time
   - Type: Time

5. movement_category
   - Type: Select
   - Options: Material
   - Default: Material
   - Required

6. source_warehouse
   - Type: Link
   - Options: Warehouse
   - Required

7. target_warehouse
   - Type: Link
   - Options: Warehouse
   - Required

8. transit_warehouse
   - Type: Link
   - Options: Warehouse
   - Required

9. project
   - Type: Link
   - Options: Project

10. cost_center
    - Type: Link
    - Options: Cost Center

11. vehicle_no
    - Type: Data

12. driver_name
    - Type: Data

13. driver_mobile
    - Type: Data

14. transporter
    - Type: Data

15. lr_no
    - Type: Data

16. dispatch_from_address
    - Type: Small Text

17. dispatch_to_address
    - Type: Small Text

18. dispatched_by
    - Type: Link
    - Options: User
    - Read Only

19. received_by
    - Type: Link
    - Options: User
    - Read Only

20. dispatch_datetime
    - Type: Datetime
    - Read Only

21. receipt_datetime
    - Type: Datetime
    - Read Only

22. status
    - Type: Select
    - Options:
      Draft
      Pending Dispatch
      In Transit
      Partially Received
      Received
      Closed with Shortage
      Cancelled
    - Default: Draft
    - Read Only where possible

23. dispatch_stock_entry
    - Type: Link
    - Options: Stock Entry
    - Read Only

24. receipt_stock_entries
    - Type: Small Text
    - Read Only
    - Note: Store newline-separated Stock Entry links initially. This can later become a child table if needed.

25. shortage_stock_entry
    - Type: Link
    - Options: Stock Entry
    - Read Only

26. shortage_closure_type
    - Type: Select
    - Options:
      Book as Shortage / Loss
      Return to Source Warehouse

27. shortage_reason
    - Type: Small Text

28. remarks
    - Type: Small Text

29. items
    - Type: Table
    - Options: Delivery Challan Item
    - Required

### Delivery Challan Item

Type:

Child Table

Suggested fields:

1. item_code
   - Type: Link
   - Options: Item
   - Required
   - In List View

2. item_name
   - Type: Data
   - Read Only
   - In List View

3. description
   - Type: Text Editor

4. uom
   - Type: Link
   - Options: UOM
   - In List View

5. stock_uom
   - Type: Link
   - Options: UOM
   - Read Only

6. qty
   - Type: Float
   - Required
   - In List View

7. received_qty
   - Type: Float
   - Default: 0
   - In List View

8. pending_qty
   - Type: Float
   - Read Only
   - In List View

9. source_warehouse
   - Type: Link
   - Options: Warehouse
   - Required

10. target_warehouse
    - Type: Link
    - Options: Warehouse
    - Required

11. transit_warehouse
    - Type: Link
    - Options: Warehouse
    - Required

12. project
    - Type: Link
    - Options: Project

13. remarks
    - Type: Small Text

14. row_status
    - Type: Select
    - Options:
      Pending
      Partially Received
      Received
      Short Closed
    - Default: Pending
    - Read Only where possible

## Status flow

Draft
→ Submit
→ Pending Dispatch
→ Dispatch Material
→ In Transit
→ Receive Material
→ Partially Received or Received
→ Close Shortage if required

## Submit behavior

On submit:

- set status = Pending Dispatch
- do not create Stock Entry
- validate items
- validate warehouses
- validate qty > 0

## Cancel behavior

Cancel behavior should be handled carefully.

Initial Phase 1 behavior:

- If no backend Stock Entry exists, allow cancellation.
- If backend Stock Entry exists, cancellation should either:
  - prevent cancellation and show linked Stock Entry information
  - or require linked Stock Entries to be cancelled first

Do not automatically cancel linked Stock Entries until this is explicitly reviewed.

## Dispatch behavior

Add custom button:

Dispatch Material

Visible when:

- docstatus = 1
- status = Pending Dispatch
- dispatch_stock_entry is empty

Action:

- validate source_warehouse, target_warehouse, transit_warehouse
- validate child rows
- create Stock Entry with purpose Material Transfer
- for each item:
  - s_warehouse = row source_warehouse
  - t_warehouse = row transit_warehouse
  - item_code = row item_code
  - qty = row qty
  - uom = row uom
  - conversion_factor = 1 unless properly fetched
- submit Stock Entry
- set dispatch_stock_entry
- set dispatch_datetime = now
- set dispatched_by = current user
- set status = In Transit
- save Delivery Challan

## Receive behavior

Add custom button:

Receive Material

Visible when:

- docstatus = 1
- status is In Transit or Partially Received

Action:

- open dialog
- show each item:
  - item name
  - dispatched qty
  - already received qty
  - pending qty
  - new received qty
- validate new received qty > 0 for at least one row
- validate new received qty <= pending qty
- create Stock Entry with purpose Material Transfer
- for each row with new received qty:
  - s_warehouse = row transit_warehouse
  - t_warehouse = row target_warehouse
  - qty = new received qty
- submit Stock Entry
- update received_qty = existing received_qty + new received_qty
- update pending_qty = qty - received_qty
- update row_status
- append Stock Entry name to receipt_stock_entries
- set receipt_datetime = now
- set received_by = current user
- if all pending qty = 0:
  - status = Received
- else:
  - status = Partially Received
- save Delivery Challan

## Close Shortage behavior

Add custom button:

Close Shortage

Visible when:

- docstatus = 1
- status = Partially Received

Dialog fields:

- closure_type
  - Book as Shortage / Loss
  - Return to Source Warehouse
- shortage_reason

Validation:

- shortage_reason is mandatory
- there must be pending quantity

If closure_type = Book as Shortage / Loss:

- create Stock Entry with purpose Material Issue
- for each item with pending qty:
  - s_warehouse = row transit_warehouse
  - item_code = row item_code
  - qty = pending qty

If closure_type = Return to Source Warehouse:

- create Stock Entry with purpose Material Transfer
- for each item with pending qty:
  - s_warehouse = row transit_warehouse
  - t_warehouse = row source_warehouse
  - item_code = row item_code
  - qty = pending qty

After successful Stock Entry:

- submit Stock Entry
- set shortage_stock_entry
- set shortage_closure_type
- set shortage_reason
- set row_status = Short Closed for rows with pending qty
- set pending_qty = 0 logically
- set status = Closed with Shortage
- save Delivery Challan

## Mobile-friendly Add Material behavior

Add custom button:

Add Material

Dialog fields:

1. item_code
2. qty
3. source_warehouse
4. target_warehouse
5. transit_warehouse
6. remarks

Defaults:

- source_warehouse from parent source_warehouse
- target_warehouse from parent target_warehouse
- transit_warehouse from parent transit_warehouse

On Add:

- fetch item_name
- fetch stock_uom
- set uom = stock_uom unless there is better ERPNext logic
- add row to items child table
- set qty
- set received_qty = 0
- set pending_qty = qty
- set warehouses
- set row_status = Pending
- refresh child table

## Server-side methods required

Suggested whitelisted methods:

- dispatch_material(delivery_challan_name)
- receive_material(delivery_challan_name, received_items)
- close_shortage(delivery_challan_name, closure_type, shortage_reason)

These methods should:

- load Delivery Challan
- validate docstatus and status
- create Stock Entry safely
- submit Stock Entry
- update Delivery Challan fields
- commit only through Frappe normal document save/submit flow

## Tests

Manual tests on erp.jewonline.in:

1. Create Delivery Challan with one item.
2. Submit.
3. Confirm status = Pending Dispatch.
4. Confirm no Stock Entry created.
5. Click Dispatch Material.
6. Confirm Stock Entry Source to Transit is created and submitted.
7. Confirm status = In Transit.
8. Receive full quantity.
9. Confirm Stock Entry Transit to Target is created and submitted.
10. Confirm status = Received.
11. Create second challan.
12. Dispatch.
13. Receive partial quantity.
14. Confirm status = Partially Received.
15. Close shortage as Book as Shortage / Loss.
16. Confirm Material Issue from Transit Warehouse is created.
17. Create third challan.
18. Dispatch.
19. Receive partial quantity.
20. Close shortage as Return to Source Warehouse.
21. Confirm Material Transfer from Transit to Source is created.