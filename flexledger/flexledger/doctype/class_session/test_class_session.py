# Copyright (c) 2026, SriRagul and Contributors
# See license.txt

from itertools import count

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

session_type_number = count(1)
trainer_number = count(1)


def make_session_type(**kwargs):
	session_type = frappe.get_doc(
		{
			"doctype": "Session Type",
			"session_type_name": kwargs.pop(
				"session_type_name", f"Test Session Type {next(session_type_number)}"
			),
			"credits_required": kwargs.pop("credits_required", 1),
			"duration_minutes": kwargs.pop("duration_minutes", 60),
			"description": "Test session type",
		}
	)
	session_type.update(kwargs)
	session_type.insert()
	return session_type


def make_trainer(**kwargs):
	trainer = frappe.get_doc(
		{
			"doctype": "Trainer",
			"trainer_name": kwargs.pop("trainer_name", "Test Trainer"),
			"employee_id": kwargs.pop("employee_id", f"TEST-TRAINER-{next(trainer_number):04d}"),
			"phone": kwargs.pop("phone", "+91-9999999999"),
			"status": kwargs.pop("status", "Active"),
		}
	)
	trainer.update(kwargs)
	trainer.insert()
	return trainer


def make_member(**kwargs):
	member = frappe.get_doc(
		{
			"doctype": "Member",
			"member_name": kwargs.pop("member_name", "Test Member"),
			"phone": kwargs.pop("phone", "+91-9876543210"),
			"join_date": kwargs.pop("join_date", today()),
			"status": kwargs.pop("status", "Active"),
		}
	)
	member.update(kwargs)
	member.insert()
	return member


def make_package(member, **kwargs):
	package = frappe.get_doc(
		{
			"doctype": "Package Purchase",
			"member": member if isinstance(member, str) else member.name,
			"total_credits": kwargs.pop("total_credits", 10),
			"credits_used": kwargs.pop("credits_used", 0),
			"amount_paid": kwargs.pop("amount_paid", 1000),
			"purchase_date": kwargs.pop("purchase_date", today()),
			"expiry_date": kwargs.pop("expiry_date", add_days(today(), 60)),
			"status": kwargs.pop("status", "Active"),
		}
	)
	package.update(kwargs)
	package.insert()
	return package


def make_session(session_type, trainer, attendees, insert=True, **kwargs):
	rows = []
	for attendee in attendees:
		member = attendee["member"]
		package = attendee["package_purchase"]
		rows.append(
			{
				"member": member if isinstance(member, str) else member.name,
				"package_purchase": package if isinstance(package, str) else package.name,
				"attendance_status": attendee.get("attendance_status", "Booked"),
			}
		)

	session = frappe.get_doc(
		{
			"doctype": "Class Session",
			"session_type": session_type.name,
			"trainer": trainer.name,
			"session_date": kwargs.pop("session_date", add_days(today(), 1)),
			"start_time": kwargs.pop("start_time", "10:00:00"),
			"status": kwargs.pop("status", "Draft"),
			"attendees": rows,
		}
	)
	session.update(kwargs)
	if insert:
		session.insert()
	return session


def package_balance(package):
	return frappe.db.get_value(
		"Package Purchase", package.name, ["credits_used", "credits_remaining", "status"], as_dict=True
	)


class IntegrationTestClassSession(IntegrationTestCase):
	"""
	Integration tests for ClassSession.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		# No tearDown(): IntegrationTestCase (v16's FrappeTestCase) runs the class inside one
		# open transaction and rolls everything back in _rollback_db when the tests are done,
		# so the records these factories insert disappear on their own. Deleting them per test
		# would only hide leaks instead of proving the rollback covers them.
		super().setUp()

	def test_happy_path_session_saves_as_draft(self):
		"""A valid session whose attendees are inside their balance must save as a draft.

		This is the everyday front-desk path: if it does not save, nobody can schedule
		a class, so it is the first thing that has to keep working.
		"""
		session_type = make_session_type(credits_required=1)
		trainer = make_trainer()
		member = make_member(member_name="Test Happy Member")
		package = make_package(member, total_credits=10)

		session = make_session(session_type, trainer, [{"member": member, "package_purchase": package}])

		self.assertEqual(session.docstatus, 0)
		self.assertEqual(session.status, "Draft")
		self.assertEqual(session.attendees[0].credits_charged, 1)

	def test_balance_boundary_exact_passes_one_credit_short_fails(self):
		"""Exactly enough credits must pass, one credit short must fail naming that member.

		Members are told their balance at the desk, so the error has to name the person
		who is short; and a member with the exact balance must never be turned away.
		"""
		session_type = make_session_type(credits_required=2)
		trainer = make_trainer()

		perfect_member = make_member(member_name="Test Perfect Member")
		perfect_package = make_package(perfect_member, total_credits=2)
		make_session(session_type, trainer, [{"member": perfect_member, "package_purchase": perfect_package}])

		short_member = make_member(member_name="Test Short Member")
		short_package = make_package(short_member, total_credits=2, credits_used=1)
		short_session = make_session(
			session_type,
			trainer,
			[{"member": short_member, "package_purchase": short_package}],
			insert=False,
		)

		with self.assertRaises(frappe.ValidationError) as error:
			short_session.insert()

		self.assertIn(short_member.name, str(error.exception))

	def test_credits_used_stops_at_total_credits(self):
		"""credits_used may reach total_credits exactly, but never pass it.

		Usage above the total would sell credits the studio never charged for, so the
		Package Purchase itself refuses the value and a fully used package can not be
		charged again.
		"""
		member = make_member(member_name="Test Boundary Member")
		package = make_package(member, total_credits=5, credits_used=5)
		self.assertEqual(package.credits_remaining, 0)

		package.credits_used = 6
		with self.assertRaises(frappe.ValidationError):
			package.save()

		package.reload()
		self.assertEqual(package.credits_used, 5)

		session_type = make_session_type(credits_required=1)
		trainer = make_trainer()
		empty_session = make_session(
			session_type, trainer, [{"member": member, "package_purchase": package}], insert=False
		)
		with self.assertRaises(frappe.ValidationError):
			empty_session.insert()

	def test_credits_remaining_is_total_minus_used(self):
		"""credits_remaining must equal total_credits - credits_used exactly.

		That one number drives the balance check, the receipt and the low-balance
		alert, so an off-by-one here silently corrupts every decision made from it.
		"""
		member = make_member(member_name="Test Arithmetic Member")
		package = make_package(member, total_credits=10, credits_used=3)

		self.assertEqual(package.credits_remaining, 7)

		package.credits_used = 4
		package.save()
		package.reload()

		self.assertEqual(package.credits_remaining, 6)
		self.assertEqual(package.credits_remaining, package.total_credits - package.credits_used)

	def test_submit_blocked_until_completed_then_deducts(self):
		"""A Booked row blocks submit; once finalized, submit deducts credits_charged from the right package.

		Submitting before attendance is final charges members for a class that never
		happened, and the deduction has to hit the package read fresh from the database
		so we are not asserting against a stale in-memory document.
		"""
		session_type = make_session_type(credits_required=3)
		trainer = make_trainer()
		member = make_member(member_name="Test Submit Member")
		package = make_package(member, total_credits=10)

		session = make_session(
			session_type,
			trainer,
			[{"member": member, "package_purchase": package}],
			status="Completed",
		)

		with self.assertRaises(frappe.ValidationError):
			session.submit()

		session.reload()
		session.attendees[0].attendance_status = "Attended"
		session.save()
		session.submit()

		charged = session.attendees[0].credits_charged
		used, remaining = frappe.db.get_value("Package Purchase", package.name, ["credits_used", "credits_remaining"])

		self.assertEqual(charged, 3)
		self.assertEqual(used, 3)
		self.assertEqual(remaining, 7)

	def test_cancel_restores_every_charged_package(self):
		"""After submit, cancelling must return each charged package to its pre-submit balance.

		Classes do get cancelled, and members who paid for those credits must come out
		of it with exactly what they went in with, status included.
		"""
		session_type = make_session_type(credits_required=2)
		trainer = make_trainer()
		member = make_member(member_name="Test Cancel Member")
		package = make_package(member, total_credits=10)

		balance_before = package_balance(package)

		session = make_session(
			session_type,
			trainer,
			[{"member": member, "package_purchase": package, "attendance_status": "Attended"}],
			status="Completed",
		)
		session.submit()

		balance_after_submit = package_balance(package)
		self.assertEqual(balance_after_submit.credits_used, 2)
		self.assertNotEqual(balance_after_submit, balance_before)

		session.cancel()

		self.assertEqual(package_balance(package), balance_before)

	def test_submit_deduction_runs_only_once(self):
		"""Running the submit-time deduction a second time must not charge the member twice.

		Retries and double firing have shipped real double charges in ledger systems,
		so the submit path has to guard itself rather than trust the caller.
		"""
		session_type = make_session_type(credits_required=1)
		trainer = make_trainer()
		member = make_member(member_name="Test Guard Member")
		package = make_package(member, total_credits=10)

		session = make_session(
			session_type,
			trainer,
			[{"member": member, "package_purchase": package, "attendance_status": "Attended"}],
			status="Completed",
		)
		session.submit()

		used_after_submit = frappe.db.get_value("Package Purchase", package.name, "credits_used")
		self.assertEqual(used_after_submit, 1)

		session.reload()
		session.on_submit()

		self.assertEqual(session.credits_deducted, 1)
		self.assertEqual(
			frappe.db.get_value("Package Purchase", package.name, "credits_used"), used_after_submit
		)
		self.assertEqual(frappe.db.get_value("Package Purchase", package.name, "credits_remaining"), 9)
