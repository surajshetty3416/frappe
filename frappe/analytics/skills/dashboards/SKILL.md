---
name: Dashboards
description: Build or change dashboards, charts and number cards over the site's data, or read the numbers on one. Use for any request for a dashboard, chart, KPI, target, trend or breakdown.
---

# Dashboards

A chart is a SQL query plus a spec. The query returns one row per record; the spec groups and aggregates those rows. The tools: `run_query`, `create_dashboard`, `add_chart`, `update_chart`, `update_dashboard`, `read_dashboard`, `list_dashboards`.

## Steps

1. Find the DocTypes and fields with `find_doctypes` and `describe`. A DocType's table is `` `tab<DocType>` ``. A Link field holds the `name` of the linked record, so a join is `` JOIN `tabConference` c ON c.name = a.conference ``.
2. Write one SQL per chart and try it with `run_query`.
3. Work out the numbers you expect in SQL with `run_query` (`COUNT(*)`, `SUM(...)` with `GROUP BY`). This is the only place a GROUP BY goes.
4. Call `create_dashboard` once with every chart and filter. It returns each chart's rows. Compare them with step 3 before you report.
5. Tell the user what the dashboard shows in two or three sentences, with the numbers. Say which charts a filter does not reach, and why.

## The SQL

- One row per record, no GROUP BY, no LIMIT. The chart groups and limits. A grouped query breaks dashboard filters and drill-down.
- Select every column a chart groups by, measures or filters on, with a plain name: `a.ticket_type`, `c.title AS conference`. Alias joined columns so two tables never return the same name.
- Filter in WHERE what the chart is about: `WHERE a.docstatus < 2`, `WHERE p.status = 'Accepted'`. Leave the period to a Date dashboard filter, not WHERE.
- A Datetime column groups by `hour`. For a time of day across several days (the busiest half-hour at the gate), compute it in SQL and group by it as a category: `DATE_FORMAT(checked_in_at, '%H:%i')`, or the DocType's own slot field when it has one.
- MariaDB syntax. Table and column names with spaces go in backticks.

## Picking the chart

| The question | Chart | Spec |
|---|---|---|
| How many, how much, did we hit the target | Number | `measures` with `target`; no `x` |
| How did it change over time | Line | `x` a date, `grain` day/week/month; `hour` for one day |
| When in the day | Bar | `x` the hour or slot, `sort: "x asc"` |
| Which category is biggest | Bar, 2 to 15 categories | `x` the category; sorted by value |
| Top N of many | Row | `limit: 10` |
| Share of a whole, 2 to 6 parts | Donut | `x` the part |
| Stages people drop out of | Funnel, or Row sorted by value | `x` the stage |
| The records themselves | Table | `x` plus `table_columns` |

- Count the distinct values of a column before you pick: one value is no chart, more than 15 is a Row with a limit.
- Readings the reader compares side by side are one Number chart with several measures. Each measure is its own card.
- A target is `target` on the measure: the card shows the value, the target and a bar. `compare: "previous"` adds the change against the period before; it needs `x` with a `grain` or `span`, or a Date filter set to a `within` value.
- Money is `format: "currency"`; a rate is `format: "percent"` on a 0 to 1 value.
- One chart, one question. Two charts of the same cut in different shapes are one chart.

## Titles

1 to 4 words: what the chart reads or cuts by. "Registrations", "Revenue by Ticket Type", "Check-ins by Hour". No dates or periods in a title; the filter owns the period. A Number card shows its measure `label`, not the chart title, so the label is the name.

## The layout

`create_dashboard` lays out the dashboard from the charts' types, in this order:

1. Filters, in one row at the top.
2. The health strip: every Number reading, up to five a row, filling the width.
3. Trends: charts with a date x, two a row.
4. Breakdowns: charts by category, two a row.
5. Lists: tables, full width.

Within a band the charts keep the order you give. A chart alone in its row takes the full width; `wide: true` asks for it. Lead with the reading that answers the question. Keep a dashboard to about eight charts.

## Filters

A filter names a `column`. It is linked to every chart whose SQL returns that column, so select the column in every chart it must reach. A Date filter goes on the date the dashboard is about (`registered_on`, `checked_in_at`). A String filter on a category (`ticket_type`, `track`). Leave the default value empty unless the user asks for a period. A chart left unlinked ignores the filter: say so.

## Changing a dashboard

`read_dashboard` returns each chart's spec and current rows. To change a chart, edit its spec and send all of it to `update_chart`. To add one, `add_chart`. `update_dashboard` renames, replaces the filters, removes charts, or lays the dashboard out again with `order`. Never pass `order` unless the user asked for a new layout: it undoes their moves.

## Example

"Registrations against a target of 1,000, ticket revenue, registrations per week, and revenue by ticket type, with a date filter."

Check the numbers first:

```sql
SELECT ticket_type, COUNT(*) AS n, SUM(amount_paid) AS revenue FROM `tabAttendee` GROUP BY ticket_type
```

Then one `create_dashboard` call:

```json
{
  "title": "Registrations",
  "charts": [
    {
      "title": "Registrations",
      "chart_type": "Number",
      "sql": "SELECT a.name, a.registered_on, a.ticket_type, a.amount_paid FROM `tabAttendee` a",
      "measures": [
        {"label": "Registrations", "aggregation": "count", "target": 1000},
        {"label": "Ticket Revenue", "aggregation": "sum", "column": "amount_paid", "format": "currency"}
      ]
    },
    {
      "title": "Registrations per Week",
      "chart_type": "Line",
      "sql": "SELECT a.name, a.registered_on, a.ticket_type FROM `tabAttendee` a",
      "x": "registered_on",
      "grain": "week",
      "measures": [{"label": "Registrations", "aggregation": "count"}]
    },
    {
      "title": "Revenue by Ticket Type",
      "chart_type": "Bar",
      "sql": "SELECT a.name, a.registered_on, a.ticket_type, a.amount_paid FROM `tabAttendee` a",
      "x": "ticket_type",
      "measures": [{"label": "Revenue", "aggregation": "sum", "column": "amount_paid", "format": "currency"}]
    }
  ],
  "filters": [{"label": "Date", "column": "registered_on"}]
}
```

Every chart selects `registered_on`, so the Date filter reaches all three. Compare the Number card's rows with the SQL total and the Bar's rows with the GROUP BY above, then report: "1,012 registrations against the 1,000 target; Regular tickets bring in most of the ₹38L."
