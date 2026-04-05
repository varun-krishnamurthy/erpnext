import frappe


def execute():
	# handle type casting for is_cancelled field
	module_doctypes = (
		("stock", "Stock Ledger Entry"),
		("stock", "Serial No"),
		("accounts", "GL Entry"),
	)

	for module, doctype in module_doctypes:
		if (
			not frappe.db.has_column(doctype, "is_cancelled")
			or frappe.db.get_column_type(doctype, "is_cancelled").lower() == "int(1)"
		):
			continue

		frappe.db.sql(
			f"""
				UPDATE `tab{doctype}`
				SET is_cancelled = 0
				WHERE COALESCE(is_cancelled::text, '') IN ('', 'No', '0')
			"""
		)
		frappe.db.sql(
			f"""
				UPDATE `tab{doctype}`
				SET is_cancelled = 1
				WHERE COALESCE(is_cancelled::text, '') IN ('Yes', '1')
			"""
		)

		frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
