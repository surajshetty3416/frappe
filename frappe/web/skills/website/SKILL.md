---
name: Website
description: Build or change the public website, its pages, the live records a page shows, a form that saves a document, or a chat where visitors talk to an agent. Use for any request for a web page, a site, a registration or submission form, or a public assistant.
---

# Building the website

A web page is a Builder Page at a route. Its blocks render on the server, so a visitor gets plain HTML. A page stays a draft until publish_web_page. Every tool here changes the draft, except set_page_data_script, which is live at once.

## Steps

1. Run `describe` on every DocType a page reads or a form inserts. Use the real fieldnames and the exact Select options.
2. Create the page with create_web_page. Give the blocks you will add to later a `name`, such as `name: Register`.
3. For live records, set the page's data script with set_page_data_script, then bind blocks to it (see Live records). Check the sample it returns before you bind.
4. Add forms with add_form_block and chats with add_chat_block.
5. Publish with publish_web_page when the user asks.

## Live records

The data script is Python that fills the dict `data` on every visit:

```python
data.speakers = frappe.get_all("Speaker", fields=["full_name", "company"], order_by="full_name asc")
data.count = len(data.speakers)
```

`frappe.get_all` reads past permissions, so fetch only the records and fields the page shows. Never fetch emails, phone numbers or other private fields for a public page.

In the page YAML, repeat a block over a list and bind its fields:

```yaml
- el: div
  name: Speakers
  style: {display: grid, gridTemplateColumns: repeat(3, 1fr), gap: 24px}
  repeat:
    data: speakers
    item:
      el: div
      c:
        - el: h3
          bind: {text: full_name}
        - el: p
          bind: {text: company}
```

Outside a repeat, `bind: {text: count}` reads a top-level key. `bind: {href: url}` binds an attribute.

## Forms

add_form_block adds a form that inserts one document of a DocType when a visitor submits it.

- List `fields` in the order the visitor fills them. Every required field of the DocType must be in the form, or set by the server. The tool warns when one is missing.
- A visitor submits as Guest. Give Guest create permission on the DocType, and nothing more. Use `allow_guest` only when Guest must not have that permission elsewhere.
- Values the visitor must not choose, such as a status, a price or a code, belong in server logic on the DocType, not in the form.
- Set `submit_label` to the action ("Register", "Submit talk") and `success_message` to what happens next. `success_route` opens a page instead.
- `columns: 2` puts short fields two to a row on a wide screen.
- Always set `--fb-accent` to the page's primary button color and `--fb-accent-ink` to its text color, so the submit button matches the page's main button. Match the rest through `style`: `--fb-radius`, `--fb-border` and `--fb-field-bg`. The form takes the page's font and text color by itself. On a dark section, set `--fb-field-bg` to a slightly lighter shade and `--fb-border` to a light border.

## Chats

add_chat_block puts a chat with one agent on a page, for visitors.

- The agent becomes public. Every visitor chats as Guest, so its tools read only DocTypes that give Guest read permission. Give Guest read on what the agent answers from, and never on DocTypes with private records, such as attendees or emails. The result lists the custom DocTypes Guest can read.
- Give the agent read tools only. A tool call that needs approval is declined, and a public agent cannot have update_memory or execute.
- Write a `greeting` that says what the agent can answer, and a `placeholder` with a sample question.
- The chat grows with its messages from 280px up to `--fb-chat-height` (default 480px).

## Example

"A registration form at /frappeverse/register that creates an Attendee."

After create_web_page made the page with a section named `Register`:

```json
{
  "page": "page-1a2b3c4d",
  "doctype": "Attendee",
  "fields": ["full_name", "email", "company", "ticket_type", "t_shirt_size", "dietary"],
  "submit_label": "Register",
  "success_message": "You're registered. Your ticket is on its way to your inbox.",
  "columns": 2,
  "inside": "Register",
  "style": {"--fb-accent": "#2563eb", "--fb-accent-ink": "#ffffff"}
}
```
