---
name: Data
description: Fill DocTypes with records. Load it before you add more than about 20 records, or any demo, sample or test data, to a DocType.
---

# Records and demo data

Writing records by hand is slow: each one costs output tokens, and a thousand of them take many minutes. So describe the data and let `generate_records` make it on the server.

- More than about 20 records, or any request for demo, sample or test data: `generate_records`, prose included. Titles, abstracts, bios and notes come from text templates. Never write records yourself in `create` or `execute`, in a loop or as a list of rows.
- Literal records only for a handful the user names or a later step refers to by name, such as 3 tracks, 6 ticket types with given prices, or the accepted talks listed by title: `create`.
- To try a spec, call `generate_records` with `"preview": true`. It inserts nothing, and returns five samples and the number of distinct values per text field. Never insert test records to see what a spec makes.

## Steps

1. `describe` the DocType and every DocType its Link fields point to. Use the real fieldnames and the exact Select options.
2. Make the records that others link to first, such as ticket types before attendees. A link spec picks only records that exist.
3. Split the request into groups wherever values depend on each other: one call per ticket type when the price and the sale period follow the ticket, one call per track when the wording of a title follows the track, one call per status when the score range follows the status. Inside a call, a group's values are constants.
4. Write prose with `text` templates and slots: two to four templates per field, each slot a list of 5 to 15 specific phrases, so a few hundred records read as varied. A slot is drawn once per record and every text field of the record reads the same value. So the title and the abstract name the same topic. Put the facts that belong together in object slots, such as a topic's track, product, result and tags. Set `unique` on titles.
5. Preview a prose spec once, read the samples and the distinct counts, then insert with the same spec.
6. When a call fails, the error names each fix. Correct the spec and call again; nothing was saved.

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

## Prose example

Talk proposals whose title, track, abstract, tags and speaker bio agree. Slots given in one field serve every field. Write 10 to 20 topics; the slots multiply them into distinct records.

```json
"fields": {
  "title": {"kind": "text", "unique": true,
    "templates": {"{topic.subject}: {angle}": 3, "{topic.subject} for {client}": 2, "{lesson} from {topic.subject}": 1},
    "slots": {
      "topic": [
        {"track": "Run", "product": "ERPNext", "subject": "GST E-Invoicing", "result": "cut month-end filing from three days to four hours", "tags": "erpnext, india"},
        {"track": "Build", "product": "Insights", "subject": "CFO Dashboards", "result": "replaced {12..30} weekly spreadsheets with one dashboard", "tags": "insights, case-study"}],
      "angle": ["The Hard Parts", "What We Got Wrong", "Two Years In", "A Field Guide"],
      "client": ["a 40-Plant Manufacturer", "a Pune Pharma Distributor", "a Chain of 30 Clinics"],
      "lesson": ["Five Lessons", "Field Notes", "What Broke"]}},
  "track": {"kind": "text", "template": "{topic.track}"},
  "screener_tags": {"kind": "text", "template": "{topic.tags}"},
  "abstract": {"kind": "text",
    "templates": ["We run {topic.product} for {client}. In {months} months we {topic.result}. We walk through {walk}, and you leave with {takeaway}.",
                  "{topic.subject} took {client} {months} months on {topic.product} before we {topic.result}. We cover {walk}. You take away {takeaway}."],
    "slots": {"months": ["four", "six", "nine"], "walk": ["the cut-over plan", "the data model we kept"], "takeaway": ["a checklist", "a rollout plan"]}},
  "speaker_name": {"kind": "name", "india": 0.85},
  "speaker_company": {"kind": "company", "names": ["Konkan Cloud Labs", "Nilgiri Software"]},
  "speaker_bio": {"kind": "text", "template": "{person.first_name} works on {topic.product} at {speaker_company}. {person.He} has run {2..9} rollouts."}
}
```

Write each slot list in full in the real call; the lists above are cut short. Weaker or different wording per group, such as rejected proposals, is one call per group with its own templates.
