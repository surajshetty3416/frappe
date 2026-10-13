---
name: Apps
description: Build or change a Studio app and its pages, frappe-ui screens over the site's DocTypes, such as a review queue, a record with actions, or a phone screen to search and act. Use for any request for an app, a screen or a page in an app.
---

# Building Studio apps

A Studio App is served at `/<app route>`. Each Studio Page is one screen at a path inside it. A page is a tree of frappe-ui components bound to resources (data fetched from DocTypes) and variables (page state). Pages you save are published at once, and a person can change them in the app editor. Read a page back with get_studio_page before you change it, because a person may have edited it.

## Steps

1. Run `describe` on every DocType the app reads. Use the real fieldnames and the exact Select options.
2. Create the app with create_studio_app, unless it exists (list_studio_apps).
3. Save each page with save_studio_page. Save the home page first: the first page saved is the app's home. If you are not sure of a component's props or slots, call get_studio_components with its name.
4. When the result says `"saved": false`, fix every error it lists and save again. Read the warnings too.
5. Reply with each page's URL.

## The tree

- Lay out with `container` blocks. A container is a flex column. Set `style.flexDirection: "row"` for a row. Space children with `gap`, never with margins on each child.
- Text is `TextBlock` with `props.text`, `props.tag` and `props.fontSize`. Do not put children in a TextBlock.
- Use frappe-ui components before you build one from containers: Button, Badge, Avatar, Select, TextInput, Textarea, Rating, Tabs, TabButtons, Dialog, NumberCard, the charts, and the List family.
- `style`, `tablet` and `mobile` take camelCase CSS. `tablet` applies below 768px and `mobile` below 576px, each on top of the one before.
- A prop value `"{{ expr }}"` is a binding. A value that starts and ends with a binding must be one expression: `"{{ a + ' · ' + b }}"`, not `"{{ a }} · {{ b }}"`. Text with a binding inside it is fine: `"{{ n }} proposals"`.
- A binding ends at the first `}}`. Put spaces between closing braces: `"{{ { a: { b: 1 } } }}"`.
- `{"$var": "track"}` binds an input's `modelValue` two-way to the variable `track`. Do not set `debounce` on such an input.

## Data

- A list: `{"resource_type": "Document List", "document_type": ..., "fields": [...], "filters": {...}, "sort_field": ..., "sort_order": "DESC", "limit": 200}`. Read it as `{{ name.data }}`. Fetch every field the page shows. The default limit is 20.
- One record from the route: `{"resource_type": "Document", "document_type": ..., "filters": {"name": "{{ route.params.name }}"}}` on a page whose route is `/proposal/:name`. Read it as `{{ name.doc.field }}`.
- A filter that follows a variable: `"track": "{{ track || null }}"`. A null filter is dropped, so an empty variable shows all records.
- OR filters, counts, and anything a Document List cannot express: an API Resource on a whitelisted method, such as `{"resource_type": "API Resource", "url": "frappe.client.get_list", "params": {"doctype": ..., "fields": [...], "or_filters": "{{ ... }}", "limit_page_length": 5}}`. Its params are sent as POST. To count by a field, fetch the field with a large limit and add a `transform`: `"function transform(data) { return data.reduce((counts, row) => ({ ...counts, [row.status]: (counts[row.status] || 0) + 1 }), {}) }"`, then read `{{ counts.data.Accepted || 0 }}`.

## Rows

- A table is the List family: `List` (props `columns`, one CSS grid track per column, and `rowHeight`) holding a `ListHeader` of `ListHeaderCell`s and a `ListRows`. `ListRows` has `items: "{{ name.data }}"`, `rowKey: "name"`, and one `ListRow` in `slots.default`, with one `ListCell` per column. Inside the row, `item` is the record.
- To open a record from a row, set the ListRow's `route` to a path in the app: `"/proposal/{{ item.name }}"`.
- Cards or any other repeated layout: `Repeater` with `data: "{{ name.data }}"` and `dataKey: "name"`, and one child as the template. Inside it, `dataItem` is the record. A Repeater lays its items out in a wrapping row, so set `style.flexDirection: "column"` for a stack.

## Events

`events` maps an event name (`click`, `change`, `update:modelValue`, `keydown.enter`) to a list of actions that run in order. The tool turns the list into a script the editor shows.

- `{"save": "proposal", "values": {"status": "Accepted"}}` saves a Document resource. Through a Document List, add `"name": "{{ item.name }}"`.
- `{"insert": "checkins", "values": {...}}` inserts through a Document List resource.
- `{"call": "frappe.client.insert", "args": {"doc": {"doctype": ..., ...}}}` calls any whitelisted method. Add `"result": "variable"` to keep its answer.
- `{"set": "query", "value": ""}`, `{"reload": "proposals"}`, `{"route": "Queue"}` (a page title, with optional `params`), `{"toast": "Saved"}`, `{"script": "js"}`.
- Values are JSON. A `"{{ expr }}"` value reads like a binding, with `item`, `dataItem` and `eventArgs` (the event's arguments) in scope. `await` works inside an expression.
- Helpers that several values need, such as the current time, go in the page `script` as top-level functions.

## Look

Pages must look finished with nothing added by hand.

- Page frame: one container with `maxWidth: "1120px"`, `width: "100%"`, `margin: "0 auto"`, `padding: "32px 24px"`, `gap: "20px"`, and `mobile: {"padding": "16px"}`.
- Page title: TextBlock, `tag: "h1"`, `fontSize: "text-3xl"`, `style: {"fontWeight": "600", "color": "var(--ink-gray-9)"}`. A one-line subtitle under it: `text-p-sm` in `var(--ink-gray-6)`. A record title: `text-4xl`.
- Text colors: `var(--ink-gray-9)` for headings and key values, `--ink-gray-8` for body, `--ink-gray-7` for secondary, `--ink-gray-6` for labels. Use `text-p-*` sizes for sentences and plain `text-*` sizes for labels.
- Card: `padding: "20px"`, `gap: "16px"`, `borderRadius: "0.75rem"`, `borderWidth: "1px"`, `borderStyle: "solid"`, `borderColor: "var(--outline-gray-2)"`. Never hex colors; use `--surface-*`, `--ink-*` and `--outline-*` tokens.
- Status as a Badge with a theme per value: `"{{ { Accepted: 'green', Rejected: 'red', Shortlisted: 'blue' }[x] || 'gray' }}"`.
- One solid Button per screen, for the main action. The others are subtle. A destructive one is subtle with `theme: "red"`.
- Desktop side panels: a row with a flexible main column (`flex: "1"`, `minWidth: "0"`) and a fixed side column (`width: "340px"`), and `tablet: {"flexDirection": "column"}` on the row, `tablet: {"width": "100%"}` on the side column.
- Phone screens: one column with `maxWidth: "480px"`, `padding: "16px"`, `gap: "16px"`. Inputs and buttons `size: "lg"`, buttons full width with `height: "48px"`, names in `text-2xl`.

## Example: a list with filters

```json
{
  "title": "Queue", "route": "/queue",
  "resources": {"proposals": {"resource_type": "Document List", "document_type": "Talk Proposal",
    "fields": ["name", "title", "speaker_name", "track", "format", "level", "screener_score"],
    "filters": {"status": ["in", ["Submitted", "Under Review"]], "track": "{{ track || null }}", "format": "{{ format || null }}"},
    "sort_field": "screener_score", "sort_order": "DESC", "limit": 200}},
  "variables": {"track": "", "format": ""},
  "blocks": [{"name": "container", "style": {"width": "100%", "maxWidth": "1120px", "margin": "0 auto", "padding": "32px 24px", "gap": "20px"}, "mobile": {"padding": "16px"}, "children": [
    {"name": "container", "style": {"gap": "4px"}, "children": [
      {"name": "TextBlock", "props": {"text": "Review queue", "tag": "h1", "fontSize": "text-3xl"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}},
      {"name": "TextBlock", "props": {"text": "{{ proposals.data.length }} proposals waiting, highest screener score first", "fontSize": "text-p-sm"}, "style": {"color": "var(--ink-gray-6)"}}]},
    {"name": "container", "style": {"flexDirection": "row", "gap": "8px", "flexWrap": "wrap"}, "children": [
      {"name": "Select", "props": {"modelValue": {"$var": "track"}, "options": [{"label": "All tracks", "value": ""}, {"label": "Build", "value": "Build"}, {"label": "Run", "value": "Run"}, {"label": "Grow", "value": "Grow"}]}, "style": {"width": "160px"}},
      {"name": "Select", "props": {"modelValue": {"$var": "format"}, "options": [{"label": "All formats", "value": ""}, {"label": "Talk", "value": "Talk 25 min"}, {"label": "Lightning", "value": "Lightning 10 min"}, {"label": "Workshop", "value": "Workshop 90 min"}]}, "style": {"width": "160px"}}]},
    {"name": "List", "props": {"columns": ["minmax(0, 3fr)", "minmax(0, 2fr)", "6rem", "9rem", "8rem", "5rem"], "rowHeight": 52}, "children": [
      {"name": "ListHeader", "children": [
        {"name": "ListHeaderCell", "children": [{"name": "TextBlock", "props": {"text": "Title"}}]},
        {"name": "ListHeaderCell", "children": [{"name": "TextBlock", "props": {"text": "Speaker"}}]},
        {"name": "ListHeaderCell", "children": [{"name": "TextBlock", "props": {"text": "Track"}}]},
        {"name": "ListHeaderCell", "children": [{"name": "TextBlock", "props": {"text": "Format"}}]},
        {"name": "ListHeaderCell", "children": [{"name": "TextBlock", "props": {"text": "Level"}}]},
        {"name": "ListHeaderCell", "style": {"justifyContent": "flex-end"}, "children": [{"name": "TextBlock", "props": {"text": "Score"}}]}]},
      {"name": "ListRows", "props": {"items": "{{ proposals.data }}", "rowKey": "name"}, "slots": {"default": [
        {"name": "ListRow", "props": {"value": "{{ value }}", "route": "/proposal/{{ item.name }}"}, "children": [
          {"name": "ListCell", "children": [{"name": "TextBlock", "props": {"text": "{{ item.title }}"}, "style": {"color": "var(--ink-gray-9)", "fontWeight": "500", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}}]},
          {"name": "ListCell", "children": [{"name": "TextBlock", "props": {"text": "{{ item.speaker_name }}"}, "style": {"color": "var(--ink-gray-7)"}}]},
          {"name": "ListCell", "children": [{"name": "Badge", "props": {"label": "{{ item.track }}", "theme": "{{ { Build: 'blue', Run: 'green', Grow: 'amber' }[item.track] || 'gray' }}"}}]},
          {"name": "ListCell", "children": [{"name": "TextBlock", "props": {"text": "{{ item.format }}"}, "style": {"color": "var(--ink-gray-7)"}}]},
          {"name": "ListCell", "children": [{"name": "TextBlock", "props": {"text": "{{ item.level }}"}, "style": {"color": "var(--ink-gray-7)"}}]},
          {"name": "ListCell", "style": {"justifyContent": "flex-end"}, "children": [{"name": "TextBlock", "props": {"text": "{{ item.screener_score }}"}, "style": {"color": "var(--ink-gray-9)", "fontWeight": "600"}}]}]}]}}]}]}]
}
```

## Example: a record with actions

```json
{
  "title": "Proposal", "route": "/proposal/:name",
  "resources": {"proposal": {"resource_type": "Document", "document_type": "Talk Proposal", "filters": {"name": "{{ route.params.name }}"}}},
  "blocks": [{"name": "container", "style": {"width": "100%", "maxWidth": "1120px", "margin": "0 auto", "padding": "32px 24px", "gap": "24px"}, "mobile": {"padding": "16px"}, "children": [
    {"name": "Button", "props": {"label": "Queue", "variant": "ghost", "iconLeft": "lucide-arrow-left", "route": "/queue"}, "style": {"alignSelf": "flex-start"}},
    {"name": "container", "style": {"flexDirection": "row", "gap": "32px", "alignItems": "flex-start"}, "tablet": {"flexDirection": "column"}, "children": [
      {"name": "container", "style": {"flex": "1", "minWidth": "0", "gap": "16px"}, "children": [
        {"name": "Badge", "props": {"label": "{{ proposal.doc.status }}", "theme": "{{ { Accepted: 'green', Rejected: 'red', Shortlisted: 'blue' }[proposal.doc.status] || 'gray' }}"}, "style": {"alignSelf": "flex-start"}},
        {"name": "TextBlock", "props": {"text": "{{ proposal.doc.title }}", "tag": "h1", "fontSize": "text-4xl"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}},
        {"name": "TextBlock", "props": {"text": "{{ proposal.doc.abstract }}", "tag": "p", "fontSize": "text-p-lg"}, "style": {"color": "var(--ink-gray-8)"}},
        {"name": "container", "style": {"flexDirection": "row", "gap": "12px", "alignItems": "center", "paddingTop": "16px", "borderWidth": "1px 0px 0px 0px", "borderStyle": "solid", "borderColor": "var(--outline-gray-1)"}, "children": [
          {"name": "Avatar", "props": {"label": "{{ proposal.doc.speaker_name }}", "size": "2xl"}},
          {"name": "container", "style": {"gap": "2px"}, "children": [
            {"name": "TextBlock", "props": {"text": "{{ proposal.doc.speaker_name }}", "fontSize": "text-lg"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}},
            {"name": "TextBlock", "props": {"text": "{{ proposal.doc.speaker_company }}", "fontSize": "text-sm"}, "style": {"color": "var(--ink-gray-6)"}}]}]},
        {"name": "TextBlock", "props": {"text": "{{ proposal.doc.speaker_bio }}", "fontSize": "text-p-base"}, "style": {"color": "var(--ink-gray-7)"}}]},
      {"name": "container", "style": {"width": "340px", "flexShrink": "0", "gap": "16px", "padding": "20px", "borderRadius": "0.75rem", "borderWidth": "1px", "borderStyle": "solid", "borderColor": "var(--outline-gray-2)"}, "tablet": {"width": "100%"}, "children": [
        {"name": "container", "style": {"flexDirection": "row", "justifyContent": "space-between", "alignItems": "baseline"}, "children": [
          {"name": "TextBlock", "props": {"text": "Screener score", "fontSize": "text-sm"}, "style": {"color": "var(--ink-gray-6)"}},
          {"name": "TextBlock", "props": {"text": "{{ proposal.doc.screener_score }}", "fontSize": "text-3xl"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}}]},
        {"name": "TextBlock", "props": {"text": "{{ proposal.doc.screener_tags }}", "fontSize": "text-sm"}, "style": {"color": "var(--ink-gray-6)"}},
        {"name": "TextBlock", "props": {"text": "{{ proposal.doc.screener_summary }}", "fontSize": "text-p-sm"}, "style": {"color": "var(--ink-gray-8)"}},
        {"name": "Divider"},
        {"name": "Rating", "props": {"label": "Your rating", "modelValue": "{{ proposal.doc.review_score || 0 }}"}, "events": {"update:modelValue": [{"save": "proposal", "values": {"review_score": "{{ eventArgs[0] }}"}}]}},
        {"name": "Textarea", "props": {"label": "Notes", "placeholder": "What should the committee know?", "rows": 4, "modelValue": "{{ proposal.doc.reviewer_notes }}"}, "events": {"change": [{"save": "proposal", "values": {"reviewer_notes": "{{ eventArgs[0].target.value }}"}}]}},
        {"name": "container", "style": {"flexDirection": "row", "gap": "8px"}, "children": [
          {"name": "Button", "props": {"label": "Shortlist", "variant": "subtle"}, "style": {"flex": "1"}, "events": {"click": [{"save": "proposal", "values": {"status": "Shortlisted"}}, {"route": "Queue"}]}},
          {"name": "Button", "props": {"label": "Reject", "variant": "subtle", "theme": "red"}, "style": {"flex": "1"}, "events": {"click": [{"save": "proposal", "values": {"status": "Rejected"}}, {"route": "Queue"}]}},
          {"name": "Button", "props": {"label": "Accept", "variant": "solid"}, "style": {"flex": "1"}, "events": {"click": [{"save": "proposal", "values": {"status": "Accepted"}}, {"route": "Queue"}]}}]}]}]}]}]
}
```

## Example: search and act on a phone

```json
{
  "title": "Scan", "route": "/scan",
  "resources": {"matches": {"resource_type": "API Resource", "url": "frappe.client.get_list", "params": {
    "doctype": "Attendee", "fields": ["name", "full_name", "company", "ticket_type", "checked_in"],
    "or_filters": "{{ { ticket_code: query, email: query, full_name: ['like', `%${query}%`] } }}", "limit_page_length": 5}}},
  "variables": {"query": ""},
  "script": "function eventDay() {\n  return new Date() < new Date('2027-08-21') ? 'Day 1' : 'Day 2'\n}\nfunction pad(n) {\n  return String(n).padStart(2, '0')\n}\nfunction stamp() {\n  const d = new Date()\n  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`\n}\nfunction halfHour() {\n  const d = new Date()\n  return `${pad(d.getHours())}:${d.getMinutes() < 30 ? '00' : '30'}`\n}",
  "blocks": [{"name": "container", "style": {"width": "100%", "maxWidth": "480px", "margin": "0 auto", "padding": "16px", "gap": "16px"}, "children": [
    {"name": "TextBlock", "props": {"text": "Check in", "tag": "h1", "fontSize": "text-3xl"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}},
    {"name": "TextInput", "props": {"modelValue": {"$var": "query"}, "placeholder": "Ticket code, email or name", "size": "lg"}, "slots": {"prefix": [{"name": "Icon", "props": {"icon": "lucide-search"}}]}},
    {"name": "Repeater", "visible": "{{ query }}", "props": {"data": "{{ matches.data }}", "dataKey": "name", "emptyStateMessage": "No attendee found"}, "style": {"flexDirection": "column", "gap": "12px"}, "children": [
      {"name": "container", "style": {"width": "100%", "gap": "12px", "padding": "16px", "borderRadius": "0.75rem", "borderWidth": "1px", "borderStyle": "solid", "borderColor": "var(--outline-gray-2)"}, "children": [
        {"name": "TextBlock", "props": {"text": "{{ dataItem.full_name }}", "fontSize": "text-2xl"}, "style": {"fontWeight": "600", "color": "var(--ink-gray-9)"}},
        {"name": "TextBlock", "props": {"text": "{{ dataItem.company + ' · ' + dataItem.ticket_type }}", "fontSize": "text-base"}, "style": {"color": "var(--ink-gray-7)"}},
        {"name": "Badge", "props": {"label": "{{ dataItem.checked_in ? 'Already in' : 'Not in yet' }}", "theme": "{{ dataItem.checked_in ? 'green' : 'gray' }}", "size": "lg"}, "style": {"alignSelf": "flex-start"}},
        {"name": "Button", "props": {"label": "Check in", "variant": "solid", "size": "lg"}, "style": {"width": "100%", "height": "48px"}, "events": {"click": [
          {"call": "frappe.client.insert", "args": {"doc": {"doctype": "Check In", "attendee": "{{ dataItem.name }}", "day": "{{ eventDay() }}", "checked_in_at": "{{ stamp() }}", "slot": "{{ halfHour() }}",
            "kind": "{{ (await call('frappe.client.get_count', { doctype: 'Check In', filters: { attendee: dataItem.name, day: eventDay(), kind: 'Arrival' } })) ? 'Re-entry' : 'Arrival' }}"}}},
          {"call": "frappe.client.set_value", "args": {"doctype": "Attendee", "name": "{{ dataItem.name }}", "fieldname": "checked_in", "value": 1}},
          {"toast": "{{ dataItem.full_name + ' is in' }}"},
          {"set": "query", "value": ""}]}}]}]}]}]
}
```
