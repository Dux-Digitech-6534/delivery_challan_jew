# Copyright (c) 2026, Jew Online and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowdate, nowtime


class DeliveryChallanReceipt(Document):
	def before_validate(self):
		if not self.posting_time:
			self.posting_time = nowtime()

		if self.docstatus == 0:
			self.status = "Draft"

		if self.delivery_challan:
			challan = self.get_delivery_challan()
			self.set_challan_details(challan)
			if not self.items:
				self.set_pending_items(challan)

	def validate(self):
		challan = self.validate_delivery_challan()
		self.validate_items(challan)

	def on_submit(self):
		challan = self.validate_delivery_challan()
		receipt_rows = self.get_receipt_rows(challan)
		stock_entry = self.make_stock_entry(receipt_rows)
		stock_entry.submit()

		receipt_datetime = now()
		self.db_set(
			{
				"stock_entry": stock_entry.name,
				"received_by": frappe.session.user,
				"receipt_datetime": receipt_datetime,
				"status": "Submitted",
			},
			update_modified=False,
		)
		self.update_delivery_challan(challan, receipt_rows, stock_entry.name, receipt_datetime)

	def on_cancel(self):
		if self.stock_entry:
			stock_entry_docstatus = frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus")
			if stock_entry_docstatus != 2:
				frappe.throw(
					_("Cancel linked Stock Entry {0} before cancelling this Receipt.").format(self.stock_entry),
					title=_("Cannot Cancel Delivery Challan Receipt"),
				)

		self.db_set("status", "Cancelled", update_modified=False)

	def get_delivery_challan(self):
		return frappe.get_doc("Delivery Challan", self.delivery_challan)

	def set_challan_details(self, challan):
		self.company = challan.company
		self.source_warehouse = challan.source_warehouse
		self.transit_warehouse = challan.transit_warehouse
		self.target_warehouse = challan.target_warehouse
		self.project = challan.project
		self.cost_center = challan.cost_center

	def set_pending_items(self, challan):
		for challan_row in challan.items:
			if flt(challan_row.pending_qty) <= 0:
				continue

			self.append("items", get_receipt_item(challan_row))

	def validate_delivery_challan(self):
		if not self.delivery_challan:
			frappe.throw(_("Delivery Challan is mandatory."))

		challan = self.get_delivery_challan()
		if challan.docstatus != 1:
			frappe.throw(_("Delivery Challan {0} must be submitted.").format(challan.name))

		if not challan.dispatch_stock_entry:
			frappe.throw(_("Dispatch Material must be completed before creating a Receipt."))

		if challan.status not in ("In Transit", "Partially Received"):
			frappe.throw(
				_("Delivery Challan {0} must be In Transit or Partially Received.").format(challan.name)
			)

		return challan

	def validate_items(self, challan):
		if not self.items:
			frappe.throw(_("At least one receipt item is required."))

		challan_rows = {row.name: row for row in challan.items}
		seen_rows = set()
		has_received_qty = False

		for row in self.items:
			if not row.delivery_challan_item:
				frappe.throw(_("Delivery Challan Item reference is mandatory for receipt rows."))

			if row.delivery_challan_item in seen_rows:
				frappe.throw(_("Duplicate Delivery Challan Item row {0}.").format(row.delivery_challan_item))
			seen_rows.add(row.delivery_challan_item)

			challan_row = challan_rows.get(row.delivery_challan_item)
			if not challan_row:
				frappe.throw(_("Invalid Delivery Challan Item row {0}.").format(row.delivery_challan_item))

			self.set_row_details(row, challan_row)

			if flt(row.received_qty) < 0:
				frappe.throw(_("Received Quantity cannot be negative for item {0}.").format(row.item_code))

			if flt(row.received_qty) > 0:
				has_received_qty = True

			if flt(challan_row.pending_qty) <= 0 and flt(row.received_qty) > 0:
				frappe.throw(_("Item {0} is already fully received.").format(row.item_code))

			if flt(row.received_qty) > flt(challan_row.pending_qty):
				frappe.throw(
					_("Received Quantity for item {0} cannot exceed Pending Quantity {1}.").format(
						row.item_code, flt(challan_row.pending_qty)
					)
				)

		if not has_received_qty:
			frappe.throw(_("Enter received quantity for at least one item."))

	def set_row_details(self, row, challan_row):
		row.item_code = challan_row.item_code
		row.item_name = challan_row.item_name
		row.description = challan_row.description
		row.uom = challan_row.uom
		row.stock_uom = challan_row.stock_uom
		row.challan_qty = flt(challan_row.qty)
		row.already_received_qty = flt(challan_row.received_qty)
		row.pending_qty = flt(challan_row.pending_qty)
		row.source_warehouse = challan_row.source_warehouse
		row.transit_warehouse = challan_row.transit_warehouse
		row.target_warehouse = challan_row.target_warehouse
		row.project = challan_row.project

	def get_receipt_rows(self, challan):
		challan_rows = {row.name: row for row in challan.items}
		receipt_rows = []

		for row in self.items:
			received_qty = flt(row.received_qty)
			if received_qty <= 0:
				continue

			challan_row = challan_rows.get(row.delivery_challan_item)
			if not challan_row:
				frappe.throw(_("Invalid Delivery Challan Item row {0}.").format(row.delivery_challan_item))

			receipt_rows.append(
				{
					"receipt_row": row,
					"challan_row": challan_row,
					"qty": received_qty,
				}
			)

		if not receipt_rows:
			frappe.throw(_("Enter received quantity for at least one item."))

		return receipt_rows

	def make_stock_entry(self, receipt_rows):
		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Transfer",
				"purpose": "Material Transfer",
				"company": self.company,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time or nowtime(),
				"set_posting_time": 1,
				"from_warehouse": receipt_rows[0]["receipt_row"].transit_warehouse,
				"to_warehouse": receipt_rows[0]["receipt_row"].target_warehouse,
				"project": self.project,
				"remarks": _("Receipt against Delivery Challan {0} via {1}").format(
					self.delivery_challan, self.name
				),
			}
		)

		for row_info in receipt_rows:
			row = row_info["receipt_row"]
			stock_entry.append(
				"items",
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"description": row.description,
					"qty": flt(row_info["qty"]),
					"uom": row.uom or row.stock_uom,
					"stock_uom": row.stock_uom,
					"conversion_factor": 1,
					"s_warehouse": row.transit_warehouse,
					"t_warehouse": row.target_warehouse,
					"project": row.project or self.project,
					"cost_center": self.cost_center,
				},
			)

		stock_entry.insert(ignore_permissions=True)
		return stock_entry

	def update_delivery_challan(self, challan, receipt_rows, stock_entry_name, receipt_datetime):
		for row_info in receipt_rows:
			challan_row = row_info["challan_row"]
			received_qty = flt(challan_row.received_qty) + flt(row_info["qty"])
			pending_qty = max(flt(challan_row.qty) - received_qty, 0)

			if pending_qty <= 0:
				row_status = "Received"
			elif received_qty > 0:
				row_status = "Partially Received"
			else:
				row_status = "Pending"

			challan_row.db_set("received_qty", received_qty, update_modified=False)
			challan_row.db_set("pending_qty", pending_qty, update_modified=False)
			challan_row.db_set("row_status", row_status, update_modified=False)

		challan.reload()
		status = "Received" if all(flt(row.pending_qty) <= 0 for row in challan.items) else "Partially Received"
		receipt_entries = split_stock_entry_links(challan.receipt_stock_entries)
		if stock_entry_name not in receipt_entries:
			receipt_entries.append(stock_entry_name)

		challan.db_set(
			{
				"receipt_stock_entries": "\n".join(receipt_entries),
				"receipt_datetime": receipt_datetime,
				"received_by": frappe.session.user,
				"status": status,
			},
			update_modified=False,
		)


@frappe.whitelist()
def make_delivery_challan_receipt(delivery_challan_name):
	challan = get_receivable_challan(delivery_challan_name)
	receipt = frappe.new_doc("Delivery Challan Receipt")
	receipt.naming_series = "DCR-.YYYY.-.#####"
	receipt.delivery_challan = challan.name
	receipt.company = challan.company
	receipt.posting_date = nowdate()
	receipt.posting_time = nowtime()
	receipt.status = "Draft"
	receipt.source_warehouse = challan.source_warehouse
	receipt.transit_warehouse = challan.transit_warehouse
	receipt.target_warehouse = challan.target_warehouse
	receipt.project = challan.project
	receipt.cost_center = challan.cost_center

	for challan_row in challan.items:
		if flt(challan_row.pending_qty) <= 0:
			continue
		receipt.append("items", get_receipt_item(challan_row))

	if not receipt.items:
		frappe.throw(_("No pending quantity is available to receive."))

	return receipt.as_dict()


def get_receivable_challan(delivery_challan_name):
	challan = frappe.get_doc("Delivery Challan", delivery_challan_name)
	if challan.docstatus != 1:
		frappe.throw(_("Delivery Challan must be submitted."))

	if not challan.dispatch_stock_entry:
		frappe.throw(_("Dispatch Material must be completed before creating a Receipt."))

	if challan.status not in ("In Transit", "Partially Received"):
		frappe.throw(_("Only In Transit or Partially Received Delivery Challans can be received."))

	return challan


def get_receipt_item(challan_row):
	return {
		"delivery_challan_item": challan_row.name,
		"item_code": challan_row.item_code,
		"item_name": challan_row.item_name,
		"description": challan_row.description,
		"uom": challan_row.uom,
		"stock_uom": challan_row.stock_uom,
		"challan_qty": flt(challan_row.qty),
		"already_received_qty": flt(challan_row.received_qty),
		"pending_qty": flt(challan_row.pending_qty),
		"received_qty": 0,
		"source_warehouse": challan_row.source_warehouse,
		"transit_warehouse": challan_row.transit_warehouse,
		"target_warehouse": challan_row.target_warehouse,
		"project": challan_row.project,
		"remarks": challan_row.remarks,
	}


def split_stock_entry_links(value):
	return [entry for entry in (value or "").splitlines() if entry]