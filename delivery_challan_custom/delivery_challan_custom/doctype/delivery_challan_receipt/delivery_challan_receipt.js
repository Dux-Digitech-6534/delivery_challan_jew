// Copyright (c) 2026, Jew Online and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Challan Receipt", {
	refresh(frm) {
		frm.set_query("delivery_challan", () => ({
			filters: {
				docstatus: 1,
				status: ["in", ["In Transit", "Partially Received"]],
			},
		}));

		frm.set_df_property("items", "cannot_add_rows", 1);
	},

	delivery_challan(frm) {
		if (!frm.doc.__islocal || !frm.doc.delivery_challan || (frm.doc.items || []).length) {
			return;
		}

		frappe.call({
			method:
				"delivery_challan_custom.delivery_challan_custom.doctype.delivery_challan_receipt.delivery_challan_receipt.make_delivery_challan_receipt",
			args: { delivery_challan_name: frm.doc.delivery_challan },
			freeze: true,
			freeze_message: __("Preparing receipt..."),
			callback(r) {
				if (!r.exc && r.message) {
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			},
		});
	},
});