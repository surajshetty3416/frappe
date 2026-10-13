---
name: Data
description: Fill DocTypes with records. Load it before you add more than about 20 records, or any demo, sample or test data, to a DocType.
---

# Records and demo data

Writing records by hand is slow: each one costs output tokens, and a thousand of them take many minutes. So describe the data and let `generate_records` make it on the server.

- More than about 20 records, or any request for demo, sample or test data: `generate_records`. Never `create` with a long list, and never `execute` with a loop or hand-written rows.
- A handful of specific records, such as 3 tracks or 6 ticket types with given prices: `create`.

## Steps

1. `describe` the DocType and every DocType its Link fields point to. Use the real fieldnames and the exact Select options.
2. Make the records that others link to first, such as ticket types before attendees. A link spec picks only records that exist.
3. Split the request into groups wherever values depend on each other: one call per ticket type when the price and the sale period follow the ticket, one call per track when the wording of a title follows the track, one call per status when the score range follows the status. Inside a call, a group's values are constants.
4. Write prose with `text` templates and slots: several templates, each slot a list of 5 to 15 specific phrases, so a few hundred records read as varied. Never write each record's text yourself.
5. When a call fails, the error names each fix. Correct the spec and call again; nothing was saved.
6. Reply with the count per DocType.

## Example

"Add 300 demo attendees for Frappeverse, mostly from India, registrations rising toward 20 August". Attendee has full_name, email, company, ticket_type (Link Ticket Type), ticket_code (unique), status (Select: Registered, Cancelled), registered_on and checked_in.

```json
{
  "doctype": "Attendee",
  "count": 300,
  "seed": 7,
  "fields": {
    "full_name": {"kind": "name", "india": 0.88, "women": 0.45},
    "company": {"kind": "company", "pool": 40},
    "email": {"kind": "email", "free": 0.15},
    "ticket_type": {"kind": "link", "weights": {"Early Bird": 3, "Standard": 5, "Student": 1}},
    "ticket_code": {"kind": "text", "template": "FV27-{code:6}", "unique": true},
    "status": {"kind": "choice", "options": {"Registered": 97, "Cancelled": 3}},
    "registered_on": {"kind": "date", "from": "2027-03-01", "to": "2027-08-19", "skew": "rising", "weekdays": [3, 3, 2, 2, 2, 1, 1]},
    "checked_in": {"kind": "choice", "options": {"1": 85, "0": 15}}
  }
}
```

When a field follows the ticket, such as amount_paid, make one call per ticket type instead, with `"ticket_type": "Standard"` and `"amount_paid": "{ticket_type.price}"` as a text spec, or the price as a constant.

Exact counts per period: `"registered_on": {"kind": "date", "ranges": [["2027-03-01", "2027-03-07", 110], ["2027-03-08", "2027-03-14", 70]]}`.

Check-ins busiest at 09:30: `"checked_in_at": {"kind": "datetime", "from": "2027-08-20", "to": "2027-08-20", "times": [["08:30", "09:00", 70], ["09:00", "09:30", 190], ["09:30", "10:00", 300], ["10:00", "11:00", 220]]}`.

Proposal titles for one track:

```json
"title": {"kind": "text", "unique": true,
  "templates": {"{verb} {product} at {scale}": 3, "{lesson} from {story}": 2},
  "slots": {
    "verb": ["Scaling", "Running", "Migrating to", "Testing"],
    "product": ["ERPNext Manufacturing", "Frappe HR Payroll", "Helpdesk", "Insights Dashboards"],
    "scale": ["{3..40} Plants", "{200..3000} Employees", "a Family Business"],
    "lesson": ["What Broke", "Five Lessons", "The Hard Parts"],
    "story": ["Moving off Tally", "a v13 to v15 Upgrade", "GST E-Invoicing"]}}
```
