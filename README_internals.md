# FlexLedger Internals

## B2c

self.save() inside validate() starts a save inside another save, and the new save runs validate() again, so it is infinite loops . Saving a Package Purchase from validate() is also wrong. Validation only checks and throws; credits are changed in on_submit().

## B2d

Every document stores a modified timestamp. When the first person saves, that timestamp changes. The second person still have the copy they opened earlier, so on save Frappe sees the mismatch and show "Document has been modified after you have opened it". and it does not overwrite.

## C3

fetch_from cannot cross from a child row through the parent into another document, so parent.session_type.credits_required does not work. credits_charged is set in validate() instead (class_session.py:38).

## C3

frappe.rename_doc() renames the record and updates every Link field that pointed at it, so the rest of the data still works. Raw SQL UPDATE leaves dead links behind. merge=True must not be used for a rename, because it joins two records into one.

## D2

`frappe.db.get_all()` ignores permissions and `permission_query_conditions`, so `unsafe_get_members()` in `api.py` returns every field of every Member to anyone who calls it. `frappe.get_list()` applies both, which is what `safe_get_members()` uses. Anything a user can reach must use `get_list()`.

## E1

`on_update()` runs at the end of a save. Calling `self.save()` there starts another save, which fires `on_update()` again, and it never stops. Fix: change the field in `validate()`, or use `self.db_set()` / `frappe.db.set_value()`, and let the current save finish.

## E2

`merge=True` combines two records and moves all references to the target, deleting the source. A rename only changes the name, so leave it off.

## E3

`frappe.db.get_single_value()` reads one column and does not build a document. `frappe.get_doc()` loads every field. One value needs `get_single_value`, several fields or a method need `get_doc` (`class_session.py:106`).

## H1

`frappe.call()` is async: it returns before the answer arrives, and `validate()` does not wait for it, so the save is decided without the balance. Balances are fetched in `onload`/`refresh` for the UI, the real check stays server side in `validate()` (`class_session.py:35`).

## I1

f-string:

frappe.db.sql(f"""SELECT name FROM `tabPackage Purchase` WHERE member = {member}""")

parameterized:

frappe.db.sql("SELECT name FROM `tabPackage Purchase` WHERE member = %s", (member,))


`member` comes from a request. The f-string puts it into the SQL text, so a value like `x OR 1=1` changes what the query returns. The parameterized form passes the value to the database driver, where it can only be read as data. That is what `transfer_package()` uses (`api.py:38`).

## J1

`frappe.get_all()` in the print template runs a query during rendering and mixes data access with the layout. `before_print()` runs the query in Python and sets `doc.print_summary`, and the template only reads `{{ doc.print_summary }}`. Same output, one place to look.

## K2


sessions = frappe.get_all("Class Session", fields=["name", "trainer"])
for s in sessions:
    trainer = frappe.get_doc("Trainer", s.trainer)
    print(trainer.trainer_name, trainer.phone)


One query for the sessions plus one per session, so 100 sessions means 101 queries.


sessions = frappe.get_all("Class Session", fields=["name", "trainer"])
trainers = {t.name: t for t in frappe.get_all("Trainer", fields=["name", "trainer_name", "phone"])}
for s in sessions:
    print(trainers[s.trainer].trainer_name, trainers[s.trainer].phone)


Fetch the trainers in bulk first, then match in memory: 2 queries total.

## N1

`on_submit()` writes to Package Purchase rows the user may not be allowed to edit (`class_session.py:96`). It is acceptable because the session already passed the permission check and `validate()` approved the amount against the package that member owns, so the user never picks the row or the amount. A whitelisted method taking any package and any amount would not be acceptable.

## N1

Hiding a field in JavaScript only changes the form. The value is still in the document and in the database, and a direct API call can still read or write it. Real restrictions are server side: field permissions and `get_list()`.
