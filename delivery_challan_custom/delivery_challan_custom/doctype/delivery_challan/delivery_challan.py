# Copyright (c) 2026, Jew Online and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowdate, nowtime


class DeliveryChallan(Document):
	def before_validate(self):
		if not self.posting_time:
			self.posting_time = nowtime()

		if self.docstatus == 0:
			self.status = "Draft"

		if self.company:
			self.transit_warehouse = get_transit_warehouse(self.company)

		for row in self.items:
			self.set_missing_item_details(row)
			self.set_row_defaults(row)

	def validate(self):
		self.validate_material_challan()
		self.validate_warehouses()
		self.validate_items()

	def on_submit(self):
		self.db_set("status", "Pending Dispatch", update_modified=False)

	def on_cancel(self):
		linked_entries = self.get_linked_stock_entries()
		if linked_entries:
			frappe.throw(
				_("Cancel linked Stock Entry documents first: {0}").format(", ".join(linked_entries)),
				title=_("Cannot Cancel Delivery Challan"),
			)

		self.db_set("status", "Cancelled", update_modified=False)

	def validate_material_challan(self):
		if self.movement_category != "Material":
			frappe.throw(_("Only Material movement is allowed in Phase 1."))

	def validate_warehouses(self):
		if not self.source_warehouse or not self.target_warehouse or not self.transit_warehouse:
			frappe.throw(_("Source Warehouse, Target Warehouse, and Transit Warehouse are mandatory."))

		expected_transit_warehouse = get_transit_warehouse(self.company)
		if self.transit_warehouse != expected_transit_warehouse:
			frappe.throw(_("Transit Warehouse is fixed as {0} for Company {1}.").format(expected_transit_warehouse, self.company))

		for warehouse in (self.source_warehouse, self.target_warehouse, self.transit_warehouse):
			self.validate_warehouse_company(warehouse)

		if self.source_warehouse == self.transit_warehouse:
			frappe.throw(_("Source Warehouse and Transit Warehouse must be different."))

		if self.target_warehouse == self.transit_warehouse:
			frappe.throw(_("Target Warehouse and Transit Warehouse must be different."))

	def validate_warehouse_company(self, warehouse):
		warehouse_details = frappe.get_cached_value("Warehouse", warehouse, ["company", "is_group"], as_dict=True)
		if not warehouse_details:
			frappe.throw(_("Warehouse {0} does not exist.").format(warehouse))

		if warehouse_details.is_group:
			frappe.throw(_("Please select a non-group Warehouse: {0}.").format(warehouse))

		if warehouse_details.company and warehouse_details.company != self.company:
			frappe.throw(_("Warehouse {0} does not belong to Company {1}.").format(warehouse, self.company))

	def validate_items(self):
		if not self.items:
			frappe.throw(_("At least one material item is required."))

		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Quantity must be greater than zero for item {0}.").format(row.item_code))

			if flt(row.received_qty) < 0:
				frappe.throw(_("Received Quantity cannot be negative for item {0}.").format(row.item_code))

			if flt(row.received_qty) > flt(row.qty):
				frappe.throw(_("Received Quantity cannot exceed Quantity for item {0}.").format(row.item_code))

			for fieldname in ("source_warehouse", "target_warehouse", "transit_warehouse"):
				if not row.get(fieldname):
					frappe.throw(_("{0} is mandatory for item {1}.").format(row.meta.get_label(fieldname), row.item_code))
				self.validate_warehouse_company(row.get(fieldname))

			if row.source_warehouse == row.transit_warehouse:
				frappe.throw(_("Source Warehouse and Transit Warehouse must be different for item {0}.").format(row.item_code))

			if row.target_warehouse == row.transit_warehouse:
				frappe.throw(_("Target Warehouse and Transit Warehouse must be different for item {0}.").format(row.item_code))

	def set_missing_item_details(self, row):
		if not row.item_code:
			return

		item = frappe.get_cached_value("Item", row.item_code, ["item_name", "description", "stock_uom"], as_dict=True)
		if not item:
			return

		row.item_name = row.item_name or item.item_name
		row.description = row.description or item.description
		row.stock_uom = row.stock_uom or item.stock_uom
		row.uom = row.uom or item.stock_uom

	def set_row_defaults(self, row):
		row.source_warehouse = row.source_warehouse or self.source_warehouse
		row.target_warehouse = row.target_warehouse or self.target_warehouse
		row.transit_warehouse = self.transit_warehouse
		row.project = row.project or self.project
		row.received_qty = flt(row.received_qty)
		row.pending_qty = flt(row.qty) - flt(row.received_qty)

		if row.pending_qty <= 0 and flt(row.qty) > 0:
			row.pending_qty = 0
			row.row_status = "Received"
		elif flt(row.received_qty) > 0:
			row.row_status = "Partially Received"
		else:
			row.row_status = row.row_status or "Pending"

	def get_linked_stock_entries(self):
		entries = []
		if self.dispatch_stock_entry:
			entries.append(self.dispatch_stock_entry)
		if self.shortage_stock_entry:
			entries.append(self.shortage_stock_entry)
		entries.extend(_split_stock_entry_links(self.receipt_stock_entries))
		return entries


@frappe.whitelist()
def dispatch_material(delivery_challan_name):
	doc = _get_submitted_challan(delivery_challan_name)

	if doc.status != "Pending Dispatch":
		frappe.throw(_("Only Delivery Challans in Pending Dispatch status can be dispatched."))

	if doc.dispatch_stock_entry:
		frappe.throw(_("Dispatch Stock Entry {0} is already linked.").format(doc.dispatch_stock_entry))

	doc.validate_warehouses()
	doc.validate_items()

	stock_entry = _make_stock_entry(
		doc=doc,
		purpose="Material Transfer",
		rows=[
			{
				"item": row,
				"qty": flt(row.qty),
				"s_warehouse": row.source_warehouse,
				"t_warehouse": row.transit_warehouse,
			}
			for row in doc.items
		],
		remarks=_("Dispatch against Delivery Challan {0}").format(doc.name),
	)

	stock_entry.submit()

	doc.db_set(
		{
			"dispatch_stock_entry": stock_entry.name,
			"dispatch_datetime": now(),
			"dispatched_by": frappe.session.user,
			"status": "In Transit",
		}
	)

	for row in doc.items:
		row.db_set("pending_qty", flt(row.qty) - flt(row.received_qty), update_modified=False)
		row.db_set("row_status", "Pending", update_modified=False)

	return {"stock_entry": stock_entry.name, "status": "In Transit"}


@frappe.whitelist()
def receive_material(delivery_challan_name, received_items):
	doc = _get_submitted_challan(delivery_challan_name)

	if doc.status not in ("In Transit", "Partially Received"):
		frappe.throw(_("Only In Transit or Partially Received Delivery Challans can be received."))

	if not doc.dispatch_stock_entry:
		frappe.throw(_("Dispatch Material must be completed before receipt."))

	received_items = _parse_json(received_items)
	row_qty_map = {item.get("name"): flt(item.get("received_qty")) for item in received_items}
	rows = []

	for row in doc.items:
		new_qty = row_qty_map.get(row.name, 0)
		if new_qty <= 0:
			continue

		pending_qty = flt(row.qty) - flt(row.received_qty)
		if new_qty > pending_qty:
			frappe.throw(_("Received quantity for item {0} cannot exceed pending quantity.").format(row.item_code))

		rows.append(
			{
				"item": row,
				"qty": new_qty,
				"s_warehouse": row.transit_warehouse,
				"t_warehouse": row.target_warehouse,
			}
		)

	if not rows:
		frappe.throw(_("Enter received quantity for at least one item."))

	stock_entry = _make_stock_entry(
		doc=doc,
		purpose="Material Transfer",
		rows=rows,
		remarks=_("Receipt against Delivery Challan {0}").format(doc.name),
	)
	stock_entry.submit()

	for row_info in rows:
		row = row_info["item"]
		received_qty = flt(row.received_qty) + flt(row_info["qty"])
		pending_qty = flt(row.qty) - received_qty
		row_status = "Received" if pending_qty <= 0 else "Partially Received"
		row.db_set("received_qty", received_qty, update_modified=False)
		row.db_set("pending_qty", max(pending_qty, 0), update_modified=False)
		row.db_set("row_status", row_status, update_modified=False)

	doc.reload()
	status = "Received" if all(flt(row.pending_qty) <= 0 for row in doc.items) else "Partially Received"
	receipt_entries = _split_stock_entry_links(doc.receipt_stock_entries)
	receipt_entries.append(stock_entry.name)
	doc.db_set(
		{
			"receipt_stock_entries": "\n".join(receipt_entries),
			"receipt_datetime": now(),
			"received_by": frappe.session.user,
			"status": status,
		}
	)

	return {"stock_entry": stock_entry.name, "status": status}


@frappe.whitelist()
def close_shortage(delivery_challan_name, closure_type, shortage_reason):
	doc = _get_submitted_challan(delivery_challan_name)

	if doc.status != "Partially Received":
		frappe.throw(_("Only Partially Received Delivery Challans can be short closed."))

	if closure_type not in ("Book as Shortage / Loss", "Return to Source Warehouse"):
		frappe.throw(_("Invalid shortage closure type."))

	if not shortage_reason:
		frappe.throw(_("Shortage Reason is mandatory."))

	rows = []
	for row in doc.items:
		pending_qty = flt(row.qty) - flt(row.received_qty)
		if pending_qty <= 0:
			continue

		rows.append(
			{
				"item": row,
				"qty": pending_qty,
				"s_warehouse": row.transit_warehouse,
				"t_warehouse": row.source_warehouse if closure_type == "Return to Source Warehouse" else None,
			}
		)

	if not rows:
		frappe.throw(_("There is no pending quantity to close."))

	purpose = "Material Transfer" if closure_type == "Return to Source Warehouse" else "Material Issue"
	stock_entry = _make_stock_entry(
		doc=doc,
		purpose=purpose,
		rows=rows,
		remarks=_("Shortage closure against Delivery Challan {0}: {1}").format(doc.name, shortage_reason),
	)
	stock_entry.submit()

	for row_info in rows:
		row = row_info["item"]
		row.db_set("pending_qty", 0, update_modified=False)
		row.db_set("row_status", "Short Closed", update_modified=False)

	doc.db_set(
		{
			"shortage_stock_entry": stock_entry.name,
			"shortage_closure_type": closure_type,
			"shortage_reason": shortage_reason,
			"status": "Closed with Shortage",
		}
	)

	return {"stock_entry": stock_entry.name, "status": "Closed with Shortage"}


@frappe.whitelist()
def get_transit_warehouse(company):
	if not company:
		frappe.throw(_("Company is required to identify Transit Warehouse."))

	warehouses = frappe.get_all(
		"Warehouse",
		filters={
			"company": company,
			"is_group": 0,
			"warehouse_name": ["like", "%Transit%"],
		},
		pluck="name",
		order_by="name asc",
		limit=1,
	)

	if not warehouses:
		frappe.throw(_("Create one non-group Transit Warehouse for Company {0}.").format(company))

	return warehouses[0]


def _get_submitted_challan(delivery_challan_name):
	doc = frappe.get_doc("Delivery Challan", delivery_challan_name)
	if doc.docstatus != 1:
		frappe.throw(_("Delivery Challan must be submitted."))
	return doc


def _make_stock_entry(doc, purpose, rows, remarks):
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": purpose,
			"purpose": purpose,
			"company": doc.company,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"set_posting_time": 1,
			"project": doc.project,
			"remarks": remarks,
		}
	)

	if purpose == "Material Transfer":
		stock_entry.from_warehouse = rows[0]["s_warehouse"] if rows else None
		stock_entry.to_warehouse = rows[0]["t_warehouse"] if rows else None
	elif purpose == "Material Issue":
		stock_entry.from_warehouse = rows[0]["s_warehouse"] if rows else None

	for row_info in rows:
		row = row_info["item"]
		item_row = {
			"item_code": row.item_code,
			"item_name": row.item_name,
			"description": row.description,
			"qty": flt(row_info["qty"]),
			"uom": row.uom or row.stock_uom,
			"stock_uom": row.stock_uom,
			"conversion_factor": 1,
			"s_warehouse": row_info["s_warehouse"],
			"t_warehouse": row_info.get("t_warehouse"),
			"project": row.project or doc.project,
			"cost_center": doc.cost_center,
		}
		stock_entry.append("items", item_row)

	stock_entry.insert(ignore_permissions=True)
	return stock_entry


def _parse_json(value):
	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			frappe.throw(_("Invalid JSON payload."))
	return value or []


def _split_stock_entry_links(value):
	return [entry for entry in (value or "").splitlines() if entry]
