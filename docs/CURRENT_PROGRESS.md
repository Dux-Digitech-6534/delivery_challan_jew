# Current Progress

## Project

Custom Frappe/ERPNext v16 app: `delivery_challan_custom`

Development site: `erp.jewonline.in`

## Completed

- Created the Frappe app `delivery_challan_custom` on the development server.
- Installed the app on `erp.jewonline.in`.
- Generated Frappe DocTypes through Frappe/bench generation flow:
  - `Delivery Challan`
  - `Delivery Challan Item`
- Copied generated files back to the local workspace for editing.
- Implemented Phase 1 material-only workflow:
  - Submit sets business status to `Pending Dispatch`.
  - Submit does not create stock movement.
  - Dispatch creates and submits a Stock Entry Material Transfer from source warehouse to transit warehouse.
  - Receipt creates and submits a Stock Entry Material Transfer from transit warehouse to target warehouse.
  - Partial receipt updates row and document status.
  - Close Shortage supports shortage/loss Material Issue from transit warehouse.
  - Close Shortage supports return Material Transfer from transit warehouse to source warehouse.
- Added mobile-friendly form actions:
  - Add Material dialog.
  - Receive Material dialog.
  - Dispatch Material action.
  - Close Shortage action.
- Added company-aware warehouse filtering:
  - Parent warehouse fields show only non-group warehouses for the selected company.
  - Child table warehouse fields use the same company filter.
  - Add Material dialog warehouse fields use the same company filter.
  - Server-side validation blocks group warehouses and warehouses from another company.
- Added Frappe server workflow note:
  - Clear cache after changes.
  - Build assets after JS changes.
  - Reload Gunicorn/bench processes after backend changes.

## Verified

- `bench --site erp.jewonline.in migrate` completed after DocType generation.
- `bench build --app delivery_challan_custom` completed after JS changes.
- `bench --site erp.jewonline.in clear-cache` completed after deployments.
- Gunicorn was gracefully reloaded after backend and frontend changes.
- Site health check returned HTTP `200`.
- Browser verification confirmed the site is up.

## Pending Manual Tests

- Create a Delivery Challan with one item.
- Submit and confirm no Stock Entry is created.
- Dispatch material and confirm Stock Entry moves source to transit.
- Receive full quantity and confirm status becomes `Received`.
- Receive partial quantity and confirm status becomes `Partially Received`.
- Close shortage as `Book as Shortage / Loss`.
- Close shortage as `Return to Source Warehouse`.
- Confirm Stock Entry links are stored on the Delivery Challan.

## Known Limitations

- Serial and batch-controlled item handling is not yet implemented.
- Asset movement is intentionally not implemented in Phase 1.
- Material indent integration is intentionally not implemented in Phase 1.
- Barcode scanning is intentionally not implemented in Phase 1.
- Advanced reports and dashboards are intentionally not implemented in Phase 1.
