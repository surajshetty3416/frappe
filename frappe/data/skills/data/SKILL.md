---
name: Data
description: Fill DocTypes with records. Load it before you add more than about 20 records, or any demo, sample or test data, to a DocType.
---

# Records and demo data

Writing records by hand is slow: each one costs output tokens, and a thousand of them take many minutes. So describe the data and let `generate_records` make it on the server.

- More than about 20 records, or any request for demo, sample or test data: `generate_records`, prose included. Titles, abstracts, bios and notes come from text templates. Never write records yourself in `create` or `execute`, in a loop or as a list of rows.
- Exact values the data asks for go into the spec, never into records you write: given titles, names or partial records in `given`, one record per target with a link's `each`, a length rule in a text field's `words`, a count of tags in a choice's `pick`. Exact counts per group are given records or weight maps.
- `create` only for a handful of records whose every value is given, such as 3 tracks or 6 ticket types with their prices.
- To try a spec, call `generate_records` with `"preview": true`. It inserts nothing, and returns five samples and, per text field, the number of distinct values and the fewest and most words. Never insert test records to see what a spec makes.

## Steps

1. `describe` the DocType and every DocType its Link fields point to. Use the real fieldnames and the exact Select options.
2. Make the records that others link to first, such as ticket types before attendees. A link spec picks only records that exist.
3. Split the request into groups wherever values depend on each other: one call per ticket type when the price and the sale period follow the ticket, one call per track when the wording of a title follows the track, one call per status when the score range follows the status. Inside a call, a group's values are constants.
4. Write prose with `text` templates and slots: two to four templates per field, each slot a list of 5 to 15 specific phrases, so a few hundred records read as varied. A slot is drawn once per record and every text field of the record reads the same value. So the title and the abstract name the same topic. Put the facts that belong together in object slots, such as a topic's track, product and result. Set `unique` on titles, and `words` where the data gives a length.
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

Talk proposals whose title, track, abstract, tags and speaker bio agree. Slots given in one field serve every field, and tags pick from the topic's own list. Write 10 to 20 topics; the slots multiply them into distinct records.

```json
"fields": {
  "title": {"kind": "text", "unique": true,
    "templates": {"{topic.subject}: {angle}": 3, "{topic.subject} for {client}": 2, "{lesson} from {topic.subject}": 1},
    "slots": {
      "topic": [
        {"track": "Run", "product": "ERPNext", "subject": "GST E-Invoicing", "result": "cut month-end filing from three days to four hours", "tags": ["erpnext", "gst", "india", "compliance", "case-study"]},
        {"track": "Build", "product": "Insights", "subject": "CFO Dashboards", "result": "replaced {12..30} weekly spreadsheets with one dashboard", "tags": ["insights", "dashboards", "finance", "deep-dive"]}],
      "angle": ["The Hard Parts", "What We Got Wrong", "Two Years In", "A Field Guide"],
      "client": ["a 40-Plant Manufacturer", "a Pune Pharma Distributor", "a Chain of 30 Clinics"],
      "lesson": ["Five Lessons", "Field Notes", "What Broke"]}},
  "track": {"kind": "text", "template": "{topic.track}"},
  "screener_tags": {"kind": "choice", "options": "{topic.tags}", "pick": [2, 4]},
  "abstract": {"kind": "text", "words": [60, 110],
    "templates": ["We run {topic.product} for {client}. In {months} months we {topic.result}. We walk through {walk}, and you leave with {takeaway}.",
                  "{topic.subject} took {client} {months} months on {topic.product} before we {topic.result}. We cover {walk}. You take away {takeaway}."],
    "slots": {"months": ["four", "six", "nine"], "walk": ["the cut-over plan", "the data model we kept"], "takeaway": ["a checklist", "a rollout plan"]}},
  "speaker_name": {"kind": "name", "india": 0.85},
  "speaker_company": {"kind": "company", "names": ["Konkan Cloud Labs", "Nilgiri Software"]},
  "speaker_bio": {"kind": "text", "template": "{person.first_name} works on {topic.product} at {speaker_company}. {person.He} has run {2..9} rollouts."}
}
```

Write each slot list in full in the real call; the lists above are cut short. Weaker or different wording per group, such as rejected proposals, is one call per group with its own templates.

## Given values example

"40 accepted talks with these titles, tracks and formats, one per speaker, abstracts of 60 to 110 words, two to four tags." The given records fix the titles and the counts per track and format; `product` is a fact the abstract reads.

```json
{
  "doctype": "Talk Proposal",
  "count": 40,
  "given": [
    {"title": "GST E-Invoicing in ERPNext: The Hard Parts", "track": "Run", "format": "Talk 25 min", "product": "ERPNext"},
    {"title": "Insights from Zero to Dashboard", "track": "Build", "format": "Workshop 90 min", "product": "Insights"}],
  "fields": {
    "status": "Accepted",
    "speaker": {"kind": "link", "each": true},
    "speaker_name": {"kind": "text", "template": "{speaker.full_name}"},
    "abstract": {"kind": "text", "words": [60, 110],
      "templates": ["{title} is our story of running {product} for {client}. In {months} months we {result}. We walk through {walk}, the mistakes we made on the way and what we would change now, with numbers from production. You leave with {takeaway} for your own {product} projects, and a clear idea of where it fits."],
      "slots": {"client": ["a Pune pharma distributor"], "months": ["six", "nine"], "result": ["cut month-end close from six days to two"], "walk": ["the cut-over plan"], "takeaway": ["a rollout plan"]}},
    "screener_tags": {"kind": "choice", "options": ["erpnext", "insights", "case-study", "deep-dive", "india"], "pick": [2, 4]}
  }
}
```

List all 40 given records in the real call. When the preview's word counts miss the range, lengthen or shorten the templates.
