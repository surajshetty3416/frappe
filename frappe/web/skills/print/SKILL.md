---
name: Print
description: Make or change a print format, such as a badge, a ticket, an invoice, a certificate or a label, that prints one record of a DocType on a page or as a PDF. Use for any request to print, badge, label or make a PDF of records.
---

# Print formats

A print format is a block tree on the HTML canvas, saved with save_print_format. It prints one record per page. Text and styles take Jinja against the record as `doc`. The print view and the PDF render the same output the editor shows.

## Steps

1. Run `describe` on the DocType. Use its real fieldnames and its exact Select options.
2. Save the format with save_print_format: its name, the DocType, the page size and margin, and the tree. Check `sample_text` in the result.
3. When the person asks to see it for particular records, find them with `read_records`, then call preview_output once per record.

## Page

- `page_size` is A4, A5, A6 or Letter, portrait. A6 is 105 x 148 mm, A5 148 x 210, A4 210 x 297.
- `margin_mm` is the margin on every side. A badge takes 4, a document 10 to 15.
- The root fills the page inside the margins. The width inside is the page width minus two margins: 97 mm on A6 with 4 mm margins.
- Write sizes in mm and font sizes in pt.
- To put a block at the bottom, make the root a flex column and give the block above it `flexGrow: '1'`.

## Jinja

- A field: `text: "{{ doc.full_name }}"`. An optional field: `"{{ doc.company or '' }}"`.
- Quote every value that starts with `{`. Inside it, use single quotes.
- A color by a field's value, with a default for the rest:
  `background: "{{ {'Speaker': '#ea580c', 'Student': '#16a34a', 'Sponsor Pass': '#ca8a04'}.get(doc.ticket_type, '#2563eb') }}"`
- A QR code of a field, `size` pixels square at 96 per inch (30 mm is 113): `text: "{{ qr_code(doc.ticket_code, 113) }}"`. Print the code under it as its own text block.
- Shrink a long text to fit one line: `fit_font_size(text, width_mm, max_pt)` gives the font size. The width is the text's box: the width inside the margins minus the horizontal padding around it.
  `style: {fontSize: "{{ fit_font_size(doc.full_name, 85, 26) }}", whiteSpace: nowrap, overflow: hidden}`

## Example

A6 badge with 4 mm margins:

```yaml
el: body
style: {display: flex, flexDirection: column, height: 100%, fontFamily: Inter, color: '#0f172a', border: '1px solid #e2e8f0'}
c:
  - el: div
    name: Header
    style: {background: '#0f172a', color: '#ffffff', padding: 5mm 4mm, display: flex, flexDirection: column, gap: 1mm}
    c:
      - el: div
        text: Frappeverse 2027
        style: {fontSize: 16pt, fontWeight: '700'}
      - el: div
        text: 20–21 Aug · Mumbai
        style: {fontSize: 9pt, opacity: '0.8'}
  - el: div
    name: Person
    style: {flexGrow: '1', display: flex, flexDirection: column, justifyContent: center, alignItems: center, padding: 4mm, gap: 1.5mm, textAlign: center}
    c:
      - el: div
        name: Name
        text: "{{ doc.full_name }}"
        style: {fontWeight: '700', width: 100%, whiteSpace: nowrap, overflow: hidden, fontSize: "{{ fit_font_size(doc.full_name, 85, 26) }}"}
      - el: div
        text: "{{ doc.company or '' }}"
        style: {fontSize: 11pt, color: '#334155'}
  - el: div
    name: Ribbon
    text: "{{ doc.ticket_type }}"
    style: {background: "{{ {'Speaker': '#ea580c', 'Student': '#16a34a'}.get(doc.ticket_type, '#2563eb') }}", color: '#ffffff', textAlign: center, padding: 2.5mm, fontWeight: '700', fontSize: 12pt, textTransform: uppercase}
  - el: div
    name: QR
    style: {display: flex, flexDirection: column, alignItems: center, padding: 3mm, gap: 1mm}
    c:
      - el: div
        text: "{{ qr_code(doc.ticket_code, 113) }}"
      - el: div
        text: "{{ doc.ticket_code }}"
        style: {fontSize: 8pt, fontFamily: monospace}
```
