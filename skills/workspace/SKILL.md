---
name: workspace
description: Set a person up on first sign-in, and build or change their workspace (/home), the one view where they do their daily work through widgets. Use when the message's studio_context has `setup`, or the person asks to add, change, move or remove something on their workspace or home, or asks how to see or act on their work in one place.
---

# Workspace

A person's workspace is one view at /home where they do most of their work. It holds widgets, never links: a queue of records with buttons that act on them, their inbox of assignments and approvals, a live chart or number, a short form that creates a record, an app used in place, a note. The tools: `read_workspace`, `arrange_workspace`, and for first-run setup `get_setup_state`, `configure_site`, `invite_people`.

## First-run setup

A message whose studio_context has `setup` comes from the setup screen. The person's workspace is drawn beside the chat and fills in as you arrange it. Lead the conversation; keep each turn short, one question at a time.

1. Call `get_setup_state`. Greet the person by first name.
2. When `site` is true, the person is the admin and the site is new to them:
   - Ask what the organization is and does, and where it works. From the answer, propose the name, country, currency, time zone and language, and call `configure_site`; the person approves it on the card.
   - Ask who else works here and on what. Match each person's work to a role from `roles`, and call `invite_people`. Skip it when they want to invite people later.
3. Ask what the person works on day to day: what they handle, what they decide, what they watch. Use `organization` for context.
4. Find their work in the data: `find_doctypes`, then `describe` the DocTypes their roles can read. Look for the status, stage or flag fields that say a record waits on someone, and the analytics charts that already exist (`list_dashboards`, `read_dashboard`).
5. Build the workspace with `arrange_workspace`, then say in two or three lines what each widget is for and ask what to change. Change it until they are happy. They finish with the button beside the chat.

## Building a workspace

- Start from what waits on the person. Most urgent first: their inbox when approvals or assignments reach them, then a queue of the records they work through, then the numbers they watch.
- A queue is the heart of a workspace. Filter it to the records in the state that needs the person, show at most four fields that let them decide, and give it the buttons for the decision: `set` to move a status or stage forward, `workflow` when the DocType has a workflow (`describe` shows it), `create` to make the record that follows from the row, such as a check-in for an attendee. Use `when` so a button shows only on rows it fits. Add `search` when the person looks records up, such as at a desk.
- A quick entry is for a record the person makes often from nothing: a few fields, the rest in `defaults`.
- A chart widget shows an existing analytics chart by its name. When the number the person watches has no chart, build one with the dashboards skill first.
- An embed shows an app the person already uses, when no queue can do its job.
- Sizes: s is a third of the row, l two thirds, xl the whole row. Give a queue or the inbox l, a chart s, and fill each row: an l beside an s, or three s. A number chart shows as a tile in a strip above the rest, whatever its size.
- Six to eight widgets at most. Each one earns its place by work the person does in it.
- Keep the `id` of every widget that stays; send the whole list each time.
- Never put a widget that only links somewhere.

## Changing a workspace

`read_workspace` first. Make the change the person asked for and leave the rest as it is. When they describe a change in their work ("I review sponsors now, not proposals"), propose the widgets to swap before you change them.
