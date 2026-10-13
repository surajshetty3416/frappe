---
name: Email
description: Make or change an email, such as a confirmation, an acceptance or an announcement, an email group of recipients, and the automation that sends an email when a record is created or changes. Use for any request for an email, a newsletter, an announcement or a mailing list.
---

# Emails

An email is an Email Template drawn on the HTML canvas, saved with save_email_template. The tool writes it as Gmail and Outlook need it: a 600px column of tables with inline styles. The subject and the text take Jinja against a record as `doc`.

## Steps

1. Run `describe` on the DocType each email is about. Use its real fieldnames and exact Select options.
2. Save each email with save_email_template. Check `sample_subject` and `sample_text` in the result.
3. Make the automations that send them (see Sending).
4. For an announcement to many people, fill an email group (see Announcements).

## One style for every email

Write the header and the footer once, and copy them into every email of a set unchanged. Change only the body. The header carries the same lockup as the event's other artifacts, such as its badge: the name and the date line. Every email opens with a greeting.

```yaml
el: body
style: {background: '#ffffff', fontFamily: Helvetica, color: '#111827', borderRadius: 8px, --backdrop: '#f4f4f5'}
c:
  - el: div
    name: Header
    style: {background: '#0f172a', padding: 24px 32px, borderRadius: 8px 8px 0 0}
    c:
      - el: h1
        text: Frappeverse 2027
        style: {color: '#ffffff', fontSize: 22px, fontWeight: '700'}
      - el: p
        text: 20–21 Aug · Mumbai
        style: {color: '#ffffff', opacity: '0.7', fontSize: 13px}
  - el: div
    name: Body
    style: {padding: 32px, display: flex, flexDirection: column, gap: 16px}
    c:
      - el: p
        text: "Hi {{ (doc.full_name or '').split(' ')[0] }},"
        style: {fontSize: 16px, lineHeight: '1.6'}
      - el: p
        text: "Your {{ doc.ticket_type }} ticket is confirmed. Your ticket code is <b>{{ doc.ticket_code }}</b>."
        style: {fontSize: 16px, lineHeight: '1.6'}
      - el: a
        name: Button
        text: See the schedule
        attrs: {href: /frappeverse/schedule}
        style: {background: '#2563eb', color: '#ffffff', padding: 12px 20px, borderRadius: 6px, fontWeight: '600', fontSize: 15px}
  - el: div
    name: Footer
    style: {padding: 20px 32px, borderTop: '1px solid #e5e7eb'}
    c:
      - el: p
        text: 20 and 21 August 2027 · Nehru Centre, Worli, Mumbai
        style: {fontSize: 13px, color: '#6b7280'}
```

- A flex column with `gap` stacks blocks. A flex row with `gap` makes columns.
- A link with a `background` is a button. A path such as /frappeverse/schedule becomes the site's full URL.
- `--backdrop` on the root is the color around the 600px column.
- Use Helvetica or Arial. Write colors as values: email clients ignore CSS variables, grids, icons and SVG, so the tool refuses them. QR codes are SVG: they belong on a print format.

## Jinja

- A field: `{{ doc.ticket_code }}`. A first name: `{{ (doc.full_name or '').split(' ')[0] }}`.
- The subject is Jinja too: `Your talk is in: {{ doc.title }}`.
- Quote every value that starts with `{`. Inside it, use single quotes.
- `doctype` in save_email_template is the DocType the email is about, such as Attendee or Talk Proposal.

## Sending

An Automation Flow sends a template with a `SendNotification` step. Create it with the `create` tool. `recipients` takes the record's email field as Jinja.

When a record is created:

```json
{
  "title": "Confirm new attendees",
  "enabled": 1,
  "document_type": "Attendee",
  "trigger_type": "Doc Created",
  "actions": [
    {
      "step_type": "Action",
      "action_type": "SendNotification",
      "params": {"channel": "Email", "recipients": ["{{ doc.email }}"], "email_template": "Registration Confirmed"}
    }
  ]
}
```

When a field changes to a value, such as a proposal's status to Accepted: `"trigger_type": "Field Value Changed"`, `"trigger_field": "status"`, `"to_value": "Accepted"`, and `"recipients": ["{{ doc.speaker_email }}"]`.

## Announcements

An announcement is an Email Template sent to an Email Group.

1. Save the template with the people's DocType as `doctype`. A group email renders against each member, which has only `email`, so write the announcement without names or other fields. Open it with "Hi there,".
2. Fill the group with fill_email_group: its title and the DocType. It adds a member per record with an email, and skips those already in it.
3. Send it with send_email_template only when the person says to send it. Until then it stays unsent.
