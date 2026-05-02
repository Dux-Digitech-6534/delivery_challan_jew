// Copyright (c) 2026, Jew Online and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Challan", {
	refresh(frm) {
		frm.trigger("set_queries");
		frm.trigger("set_fixed_transit_warehouse");
		frm.trigger("set_primary_actions");
		frm.trigger("toggle_sections");
	},

	company(frm) {
		frm.trigger("set_queries");
		clear_wrong_company_warehouses(frm);
		frm.trigger("set_fixed_transit_warehouse");
	},

	source_warehouse(frm) {
		frm.trigger("set_missing_row_warehouses");
	},

	target_warehouse(frm) {
		frm.trigger("set_missing_row_warehouses");
	},

	transit_warehouse(frm) {
		frm.trigger("set_missing_row_warehouses");
	},

	set_primary_actions(frm) {
		frm.add_custom_button(__("Add Material"), () => show_add_material_dialog(frm));

		if (frm.doc.docstatus === 1 && frm.doc.status === "Pending Dispatch" && !frm.doc.dispatch_stock_entry) {
			frm.add_custom_button(__("Dispatch Material"), () => dispatch_material(frm));
		}

		if (
			frm.doc.docstatus === 1 &&
			["In Transit", "Partially Received"].includes(frm.doc.status)
		) {
			frm.add_custom_button(__("Receive Material"), () => show_receive_dialog(frm));
		}

		if (frm.doc.docstatus === 1 && frm.doc.status === "Partially Received") {
			frm.add_custom_button(__("Close Shortage"), () => show_close_shortage_dialog(frm));
		}
	},

	set_missing_row_warehouses(frm) {
		(frm.doc.items || []).forEach((row) => {
			if (!row.source_warehouse && frm.doc.source_warehouse) {
				frappe.model.set_value(row.doctype, row.name, "source_warehouse", frm.doc.source_warehouse);
			}
			if (!row.target_warehouse && frm.doc.target_warehouse) {
				frappe.model.set_value(row.doctype, row.name, "target_warehouse", frm.doc.target_warehouse);
			}
			if (!row.transit_warehouse && frm.doc.transit_warehouse) {
				frappe.model.set_value(row.doctype, row.name, "transit_warehouse", frm.doc.transit_warehouse);
			}
		});
	},

	set_queries(frm) {
		["source_warehouse", "target_warehouse"].forEach((fieldname) => {
			frm.set_query(fieldname, () => get_warehouse_query(frm));
			frm.set_query(fieldname, "items", () => get_warehouse_query(frm));
		});
	},

	set_fixed_transit_warehouse(frm) {
		if (!frm.doc.company) {
			return;
		}

		frappe.call({
			method:
				"delivery_challan_custom.delivery_challan_custom.doctype.delivery_challan.delivery_challan.get_transit_warehouse",
			args: { company: frm.doc.company },
			callback(r) {
				if (r.message && frm.doc.transit_warehouse !== r.message) {
					frm.set_value("transit_warehouse", r.message);
				}
			},
		});
	},

	toggle_sections(frm) {
		const has_dispatch = Boolean(frm.doc.dispatch_stock_entry || frm.doc.dispatch_datetime || frm.doc.dispatched_by);
		const has_receipt = Boolean(frm.doc.receipt_stock_entries || frm.doc.receipt_datetime || frm.doc.received_by);
		const has_shortage = Boolean(frm.doc.shortage_stock_entry || frm.doc.shortage_reason || frm.doc.status === "Partially Received");

		frm.toggle_display("stock_entry_section", has_dispatch || has_receipt || has_shortage);
		frm.toggle_display("dispatch_stock_entry", has_dispatch);
		frm.toggle_display("dispatched_by", has_dispatch);
		frm.toggle_display("dispatch_datetime", has_dispatch);
		frm.toggle_display("receipt_stock_entries", has_receipt);
		frm.toggle_display("received_by", has_receipt);
		frm.toggle_display("receipt_datetime", has_receipt);
		frm.toggle_display("shortage_section", has_shortage);
		frm.toggle_display("shortage_stock_entry", has_shortage);
		frm.toggle_display("shortage_closure_type", has_shortage);
		frm.toggle_display("shortage_reason", has_shortage);
	},
});

frappe.ui.form.on("Delivery Challan Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db.get_value("Item", row.item_code, ["item_name", "description", "stock_uom"]).then((r) => {
			const item = r.message || {};
			frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
			frappe.model.set_value(cdt, cdn, "description", item.description);
			frappe.model.set_value(cdt, cdn, "stock_uom", item.stock_uom);
			frappe.model.set_value(cdt, cdn, "uom", row.uom || item.stock_uom);
		});
	},

	qty(frm, cdt, cdn) {
		update_pending_qty(cdt, cdn);
	},

	received_qty(frm, cdt, cdn) {
		update_pending_qty(cdt, cdn);
	},
});

function show_add_material_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Material"),
		fields: [
			{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item", reqd: 1 },
			{ fieldname: "qty", label: __("Quantity"), fieldtype: "Float", reqd: 1 },
			{
				fieldname: "source_warehouse",
				label: __("Source Warehouse"),
				fieldtype: "Link",
				options: "Warehouse",
				default: frm.doc.source_warehouse,
				get_query: () => get_warehouse_query(frm),
				reqd: 1,
			},
			{
				fieldname: "target_warehouse",
				label: __("Target Warehouse"),
				fieldtype: "Link",
				options: "Warehouse",
				default: frm.doc.target_warehouse,
				get_query: () => get_warehouse_query(frm),
				reqd: 1,
			},
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Small Text" },
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			if (flt(values.qty) <= 0) {
				frappe.throw(__("Quantity must be greater than zero."));
			}

			frappe.db.get_value("Item", values.item_code, ["item_name", "description", "stock_uom"]).then((r) => {
				const item = r.message || {};
				const row = frm.add_child("items");
				row.item_code = values.item_code;
				row.item_name = item.item_name;
				row.description = item.description;
				row.stock_uom = item.stock_uom;
				row.uom = item.stock_uom;
				row.qty = values.qty;
				row.received_qty = 0;
				row.pending_qty = values.qty;
				row.source_warehouse = values.source_warehouse;
				row.target_warehouse = values.target_warehouse;
				row.transit_warehouse = frm.doc.transit_warehouse;
				row.project = frm.doc.project;
				row.remarks = values.remarks;
				row.row_status = "Pending";
				frm.refresh_field("items");
				dialog.hide();
			});
		},
	});

	dialog.show();
}

function dispatch_material(frm) {
	frappe.confirm(__("Create and submit Stock Entry for dispatch to Transit Warehouse?"), () => {
		frappe.call({
			method:
				"delivery_challan_custom.delivery_challan_custom.doctype.delivery_challan.delivery_challan.dispatch_material",
			args: { delivery_challan_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Dispatching material..."),
			callback(r) {
				if (!r.exc) {
					frappe.show_alert({
						message: __("Dispatch Stock Entry {0} created.", [r.message.stock_entry]),
						indicator: "green",
					});
					frm.reload_doc();
				}
			},
		});
	});
}

function show_receive_dialog(frm) {
	const data = (frm.doc.items || [])
		.map((row) => ({
			name: row.name,
			item_code: row.item_code,
			item_name: row.item_name,
			qty: flt(row.qty),
			received_qty: flt(row.received_qty),
			pending_qty: flt(row.qty) - flt(row.received_qty),
			new_received_qty: 0,
		}))
		.filter((row) => row.pending_qty > 0);

	if (!data.length) {
		frappe.msgprint(__("No pending quantity is available to receive."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Receive Material"),
		size: "extra-large",
		fields: [
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Items"),
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: true,
				data,
				fields: [
					{ fieldname: "name", fieldtype: "Data", hidden: 1 },
					{
						fieldname: "item_code",
						label: __("Item"),
						fieldtype: "Link",
						options: "Item",
						read_only: 1,
						in_list_view: 1,
						columns: 2,
					},
					{
						fieldname: "item_name",
						label: __("Item Name"),
						fieldtype: "Data",
						read_only: 1,
						in_list_view: 1,
						columns: 2,
					},
					{
						fieldname: "qty",
						label: __("Dispatched"),
						fieldtype: "Float",
						read_only: 1,
						in_list_view: 1,
						columns: 1,
					},
					{
						fieldname: "received_qty",
						label: __("Received"),
						fieldtype: "Float",
						read_only: 1,
						in_list_view: 1,
						columns: 1,
					},
					{
						fieldname: "pending_qty",
						label: __("Pending"),
						fieldtype: "Float",
						read_only: 1,
						in_list_view: 1,
						columns: 1,
					},
					{
						fieldname: "new_received_qty",
						label: __("New Receipt"),
						fieldtype: "Float",
						in_list_view: 1,
						columns: 1,
					},
				],
			},
		],
		primary_action_label: __("Receive"),
		primary_action(values) {
			const received_items = (values.items || [])
				.filter((row) => flt(row.new_received_qty) > 0)
				.map((row) => ({ name: row.name, received_qty: flt(row.new_received_qty) }));

			if (!received_items.length) {
				frappe.throw(__("Enter received quantity for at least one item."));
			}

			frappe.call({
				method:
					"delivery_challan_custom.delivery_challan_custom.doctype.delivery_challan.delivery_challan.receive_material",
				args: {
					delivery_challan_name: frm.doc.name,
					received_items,
				},
				freeze: true,
				freeze_message: __("Receiving material..."),
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Receipt Stock Entry {0} created.", [r.message.stock_entry]),
							indicator: "green",
						});
						dialog.hide();
						frm.reload_doc();
					}
				},
			});
		},
	});

	dialog.show();
}

function show_close_shortage_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Close Shortage"),
		fields: [
			{
				fieldname: "closure_type",
				label: __("Closure Type"),
				fieldtype: "Select",
				options: "\nBook as Shortage / Loss\nReturn to Source Warehouse",
				reqd: 1,
			},
			{ fieldname: "shortage_reason", label: __("Shortage Reason"), fieldtype: "Small Text", reqd: 1 },
		],
		primary_action_label: __("Close Shortage"),
		primary_action(values) {
			frappe.call({
				method:
					"delivery_challan_custom.delivery_challan_custom.doctype.delivery_challan.delivery_challan.close_shortage",
				args: {
					delivery_challan_name: frm.doc.name,
					closure_type: values.closure_type,
					shortage_reason: values.shortage_reason,
				},
				freeze: true,
				freeze_message: __("Closing shortage..."),
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Shortage Stock Entry {0} created.", [r.message.stock_entry]),
							indicator: "green",
						});
						dialog.hide();
						frm.reload_doc();
					}
				},
			});
		},
	});

	dialog.show();
}

function update_pending_qty(cdt, cdn) {
	const row = locals[cdt][cdn];
	const pending_qty = Math.max(flt(row.qty) - flt(row.received_qty), 0);
	frappe.model.set_value(cdt, cdn, "pending_qty", pending_qty);
}

function get_warehouse_query(frm) {
	const filters = {
		is_group: 0,
	};

	if (frm.doc.company) {
		filters.company = frm.doc.company;
	}

	return { filters };
}

function clear_wrong_company_warehouses(frm) {
	["source_warehouse", "target_warehouse", "transit_warehouse"].forEach((fieldname) => {
		frm.set_value(fieldname, null);
	});

	(frm.doc.items || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "source_warehouse", null);
		frappe.model.set_value(row.doctype, row.name, "target_warehouse", null);
		frappe.model.set_value(row.doctype, row.name, "transit_warehouse", null);
	});
}
