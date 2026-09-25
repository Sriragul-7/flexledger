# FlexLedger Internals

## B2c

Bug 1: self.save() inside validate() calls validate() again, so it loops forever.
Bug 2: updating the Package Purchase inside validate() changes another document before this one is even saved. If the save fails later, the credits are already changed. Validate should only calculate and check.

def validate(self):
    self.total_charged = sum(r.credits_charged for r in self.attendees)

The Package Purchase update is done in on_submit().

## B2d

Every document has a modified timestamp. When the first person saves, the timestamp changes. The second person still has the old copy, so when they save Frappe sees the timestamps don't match and shows "Document has been modified after you have opened it". It does not overwrite, the second person should reload first.

## C3

fetch_from cannot go from a child row to the parent and then to another document, so parent.session_type.credits_required does not work. credits_charged is set in validate() in the controller instead.

## C3 (rename)

Yes, member on Package Purchase updates automatically. frappe.rename_doc() changes the name and also updates every Link field that pointed to the old name.

## D2

frappe.get_all() ignores permissions, so if a low-privilege user calls the whitelisted method they get every row and every field. frappe.get_list() checks permissions and permission_query_conditions, so the user only gets what they are allowed to see.

## E1

on_update() runs after a save. If you call self.save() inside it, that save runs on_update() again and it never stops. Fix: use self.db_set() or frappe.db.set_value() to change the field, or set it in validate() before the save.

## E2

merge=True joins two records into one. All links to the old record move to the new one and the old one is deleted. It is dangerous because if the two records are not really the same thing (two different members), their data gets mixed and you cannot undo it.

## E3

The second one, frappe.db.get_value(). It reads only one column. In a loop, get_doc would load the whole document again and again for one number.

## H1

frappe.call() is async. It returns before the server answers, but validate does not wait, so the save goes ahead without the result. Async fetches are done in onload, refresh or field change events. The real balance check stays in the server validate().

## I1

f-string:

frappe.db.sql(f"SELECT name FROM `tabPackage Purchase` WHERE member = '{member}'")

parameterized:

frappe.db.sql("SELECT name FROM `tabPackage Purchase` WHERE member = %s", (member,))

With the f-string, whatever the user sends becomes part of the SQL, so someone can send x' OR '1'='1 and get all rows (SQL injection). With the parameterized one the value is only treated as data. So always use the parameterized one.

## J1

frappe.get_all() inside the template runs a query while the page is rendering, so data logic and layout get mixed. With before_print() the query is done in Python, the result is saved on doc.print_summary, and the template just prints it.

## K2

The loop runs one get_doc query for every session, so 100 sessions means 101 queries.

sessions = frappe.get_all("Class Session", fields=["name", "trainer"])
trainers = {t.name: t for t in frappe.get_all("Trainer", fields=["name", "trainer_name", "phone"])}
for s in sessions:
    print(trainers[s.trainer].trainer_name, trainers[s.trainer].phone)

Now it is 2 queries in total.
