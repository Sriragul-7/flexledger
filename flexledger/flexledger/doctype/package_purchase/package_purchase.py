# Copyright (c) 2026, SriRagul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PackagePurchase(Document):
	def validate(self):
		if (self.credits_used or 0) > (self.total_credits or 0):
			frappe.throw(
				f"Credits Used ({self.credits_used}) can not be more than Total Credits ({self.total_credits})"
			)

		self.credits_remaining = (self.total_credits or 0) - (self.credits_used or 0)

	def before_print(self, settings=None):
		self.print_summary = f"{self.member} - {self.total_credits} credits"
