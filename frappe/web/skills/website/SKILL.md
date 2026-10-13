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

Build strings with f-strings. The sandbox refuses `str.format`.

`frappe.get_all` reads past permissions, so fetch only the records and fields the page shows. Never fetch emails, phone numbers or other private fields for a public page.

In the page YAML, repeat a block over a list and bind its fields, as in Cards below. Outside a repeat, `bind: {text: count}` reads a top-level key. `bind: {href: url}` binds an attribute.

## Layout

`style` is the desktop. `t_style` applies below 1024px, and `m_style` below 576px, over `t_style`.

- Header and footer: write one Nav and one Footer and put the same blocks on every page. Link only to pages that exist and to anchors on the home page, such as `/event#speakers` with `attrs: {id: speakers}` on that section. Leave out a link to a page you have not made. A page cannot script or toggle a menu, so the nav never collapses. Make the Nav a wrapping row of the wordmark, the links in one block and the Register link, in `order` wordmark, links, Register on desktop. On phone the links block takes `m_style: {order: 3, flexBasis: 100%}`, so Register stays beside the wordmark and the links wrap below. Never hide a link.
- Sections: the same padding on every section, such as `96px 48px` with `m_style: {padding: 64px 20px}`.
- Identity without images: a hero with a gradient or pattern in the site's colors, such as `backgroundImage: radial-gradient(circle at 80% 0%, rgba(37,99,235,0.45), transparent 60%)`. One wordmark, spelled the same in nav, hero and footer. Link color only on links. All numbers in a row in one color.
- Card text never clips: no fixed `height`, no `overflow: hidden` or `whiteSpace: nowrap` on a card or its text. A card grows with its text.

### Cards

Speakers, sponsors, tracks and numbers go in a grid on the block that holds the cards, which for live records is the repeat block: four a row on desktop, two on tablet, one on phone.

```yaml
- el: div
  name: Speakers
  style: {display: grid, gridTemplateColumns: repeat(4, minmax(0, 1fr)), gap: 24px}
  t_style: {gridTemplateColumns: repeat(2, minmax(0, 1fr))}
  m_style: {gridTemplateColumns: 1fr}
  repeat:
    data: speakers
    item:
      el: div
      style: {display: flex, flexDirection: column, gap: 4px, padding: 24px, borderRadius: 12px, background: '#141925'}
      c:
        - el: h3
          style: {margin: '0', fontSize: 18px}
          bind: {text: full_name}
        - el: p
          style: {margin: '0', opacity: '0.7'}
          bind: {text: company}
```

Sponsors sit in a wrapping row per tier, each tile sized to its content, a higher tier larger. Without a logo, the sponsor's name is its wordmark. Make it in the data script, `s.mark = f'<img src="{s.logo}" alt="{s.company_name}" style="height:40px">' if s.logo else s.company_name`, and bind it:

```yaml
- el: div
  name: Gold Sponsors
  style: {display: flex, flexWrap: wrap, gap: 16px}
  repeat:
    data: gold
    item:
      el: div
      style: {padding: 20px 32px, borderRadius: 12px, border: '1px solid rgba(255,255,255,0.15)', fontSize: 24px, fontWeight: '800'}
      bind: {text: mark}
```

### Schedule

Room headers and sessions share one grid, so each header heads its column. The repeat block takes `display: contents`, which makes its cards cells of that grid. The data script gives each session a `cell` with its column and rows as CSS variables. The rows are the session's start and end among the day's sorted times, so a 10-minute talk gets a whole row. A break spans every room with `--col: 1 / -1`. On phone the grid turns to one column and the cards stack in time order, each showing its room.

```python
rooms = ["Main Hall", "Room A", "Room B"]
rows = frappe.get_all("Session", fields=["session_title", "room", "start_time", "end_time"], filters={"day": "Day 1"}, order_by="start_time asc")
times = sorted({r.start_time for r in rows} | {r.end_time for r in rows})
hhmm = lambda t: frappe.utils.format_datetime(t, "HH:mm")
for r in rows:
    r.time = f"{hhmm(r.start_time)}–{hhmm(r.end_time)}"
    r.cell = f"--col: {rooms.index(r.room) + 1}; --row: {times.index(r.start_time) + 2} / {times.index(r.end_time) + 2}"
data.sessions = rows
```

```yaml
- el: div
  name: Schedule
  style: {display: grid, gridTemplateColumns: repeat(3, minmax(0, 1fr)), gap: 8px}
  m_style: {gridTemplateColumns: 1fr}
  c:
    - {el: div, text: Main Hall, style: {fontWeight: '700'}, m_style: {display: none}}
    - {el: div, text: Room A, style: {fontWeight: '700'}, m_style: {display: none}}
    - {el: div, text: Room B, style: {fontWeight: '700'}, m_style: {display: none}}
    - el: div
      style: {display: contents}
      repeat:
        data: sessions
        item:
          el: div
          style: {gridColumn: var(--col), gridRow: var(--row), display: flex, flexDirection: column, gap: 4px, padding: 12px, borderRadius: 10px, background: '#141925'}
          m_style: {gridColumn: auto, gridRow: auto}
          bind: {style: cell}
          c:
            - {el: span, bind: {text: time}, style: {fontSize: 12px}}
            - {el: strong, bind: {text: session_title}}
            - {el: span, bind: {text: room}, style: {display: none}, m_style: {display: inline}}
```

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
