---
name: dashboards
description: Build or change dashboards, charts and number cards over the site's data, or read and check the numbers on one. Use for any request for a dashboard, chart, KPI, target, trend or breakdown, or a question about the figures a dashboard shows.
---

# Dashboards

A chart is a SQL query plus a spec. The query returns one row per record; the spec groups and aggregates those rows. The tools: `run_query`, `create_dashboard`, `add_chart`, `update_chart`, `update_dashboard`, `read_dashboard`, `list_dashboards`. You make dashboards and charts, never workbooks.

## Before you build

- Change the dashboard the user means. "Add a chart", "fix this chart" and "put a filter on it" go to `add_chart`, `update_chart` and `update_dashboard`, never to a new `create_dashboard`. Make a dashboard only when the user asks for one. When it is unclear which, `list_dashboards` and ask.
- Look for the site's own definition before you derive one. "Active customer" or "partner" may already be a query someone uses: `read_records("Insights Query v3", {"title": ["like", "%partner%"]}, ["name", "title", "operations"])`, then the same filter on `operations`. Search one word at a time, the user's words first. A query's `operations` hold its filters and calculations: copy them into your own SQL.
- On ERPNext the app's own report defines its measure: Gross Profit, Accounts Receivable, Stock Balance. Find it with `read_records("Report", {"ref_doctype": "Sales Invoice"}, ["name", "report_type"])` and build to match it.
- Say what one counted thing is: an invoice, a customer, an attendee. A customer with three invoices counts three times when the unit is the invoice. Name the dashboard by its unit.
- When two columns could serve a measure, such as `grand_total` and `net_total`, ask which one. Never pick alone.

## Steps

1. Find the DocTypes and fields with `find_doctypes` and `describe`. A DocType's table is `` `tab<DocType>` ``. A Link field holds the `name` of the linked record, so a join is `` JOIN `tabConference` c ON c.name = a.conference ``.
2. Write one SQL per chart and try it with `run_query`.
3. Work out the numbers you expect in SQL with `run_query` (`COUNT(*)`, `SUM(...)` with `GROUP BY`). This is the only place a GROUP BY goes.
4. Call `create_dashboard` once with every chart and filter. It returns each chart's rows. Compare them with step 3.
5. Run the checks in "Check the numbers" before you report a figure.

## The SQL

- One row per record, no GROUP BY, no LIMIT. The chart groups and limits. A grouped query breaks dashboard filters and drill-down: per row, one click on a bar lands on the records behind it.
- Select every column a chart groups by, measures or filters on, with a plain name: `a.ticket_type`, `c.title AS conference`. Alias joined columns so two tables never return the same name.
- Filter in WHERE what the chart is about: `WHERE p.status = 'Accepted'`. Leave the period to a Date dashboard filter, not WHERE.
- On a submittable DocType count submitted documents: `WHERE si.docstatus = 1`. Otherwise drafts and cancelled documents count too.
- Sum ERPNext's `base_` amounts (`base_net_total`, `base_grand_total`). They are in the company's currency; a sum over mixed currencies means nothing.
- A rate per cohort leaves out the cohorts that have not settled. A 7-day rate for people who signed up 3 days ago reads as a drop: `WHERE signed_up_on <= CURDATE() - INTERVAL 7 DAY`.
- A Datetime column groups by `hour`. For a time of day across several days (the busiest half-hour at the gate), compute it in SQL and group by it as a category: `DATE_FORMAT(checked_in_at, '%H:%i')`, or the DocType's own slot field when it has one.
- MariaDB syntax. Table and column names with spaces go in backticks.

## Picking the chart

| The question | Chart | Spec |
|---|---|---|
| How many, how much, did we hit the target | Number | `measures` with `target`; see "Number cards" |
| How did it change over time | Line | `x` a date, `grain` day/week/month; `hour` for one day |
| When in the day | Bar | `x` the hour or slot, `sort: "x asc"` |
| Which category is biggest | Bar, 2 to 15 categories | `x` the category; sorted by value |
| Top N of many | Row | `limit: 10` |
| Share of a whole, 2 to 6 parts | Donut | `x` the part |
| Stages people drop out of | Funnel | `x` the stage |
| The records themselves | Table | `x` plus `table_columns` |

- Count the distinct values of `x` with `run_query` before you pick. One value is no chart: the split lives in another column. 2 to 6 is a Donut or a Bar, up to 15 a Bar, more a Row with `limit: 10` that you call a top 10, hundreds a Table.
- Read the top value's share too. When one value holds most rows, the chart shows that one value. Drop the chart, or let a filter take the value out.
- `split_by` takes the same count: a column of 2 to 8 values. The chart keeps 8 series, and a split Bar stacks.
- Compare segments by rate, not count. Segments differ in size, so their counts compare their sizes. Return a 0 or 1 column, `CASE WHEN l.status = 'Converted' THEN 1 ELSE 0 END AS converted`, and measure it with `avg` and `format: "percent"`. One chart plots one rate.
- Nested counts of one population (Registered, then Checked In, then Rated, each inside the one before) are a Funnel, not cards. Return one row per record per stage it reached, with `UNION ALL`, and set `x` to the stage. The Funnel puts the biggest stage first.
- A health or monitoring ask wants what changed, not a leaderboard. Plot the measure over time, or give its card `compare: "previous"`.
- Categories with an order of their own, such as statuses in review order: return the order as a column, `CASE p.status WHEN 'Submitted' THEN 1 WHEN 'Under Review' THEN 2 ... END AS status_order`, and sort by it with `sort: "status_order asc"`. The chart does not show that column, so `x` keeps the plain labels. Never put the order into the labels.
- Money is `format: "currency"`; a rate is `format: "percent"` on a 0 to 1 value.
- One chart, one question. Two charts of the same cut in different shapes are one chart.

## Number cards

- Readings the reader compares side by side are one Number chart with several measures. Each measure is its own card, so give each its own `label`.
- With no `x`, a card reads the total over every row. With `x` a date column and a `span` (`"Last 1 month"`, `"Month to date"`), it reads that period. With a `grain`, it reads the newest period in the data. A `span` or `grain` adds a sparkline.
- Read a closed period, or compare like with like. A `grain` card reads the running period, so two days of a week print as a fall against a whole week. Use a span that ends at a closed period, `"Last 1 week"`, or a to-date span, `"Week to date"`, whose `compare: "previous"` reads the same stretch of the week before.
- Give every card in one row the same period. Cards side by side that read different periods look comparable and are not.
- `compare: "previous"` needs a `grain`, a `span`, or a Date filter set to a `within` value. `compare: "last year"` needs a `span` or that filter; beside a `grain` it shows nothing.
- `target` on the measure shows the value, the target and a bar.
- A card shows its measure `label`, not the chart title, and does not show the chart's `info`.

## Titles and labels

- A title is 1 to 4 words: what the chart reads or cuts by. "Registrations", "Revenue by Ticket Type", "Check-ins by Hour".
- No dates, periods or counts in a title or label. The filter owns the period, and a count you measured today is wrong tomorrow: "Top Customers", not "Top 34 Customers". Say the period and the count in your reply.
- Use the site's words, from the DocType or field the data comes from: "Customer Group", not "segment". Leave out the unit when the dashboard counts one thing: on a dashboard of attendees, "Ticket Type", not "Attendees by Ticket Type".
- Name a measure in 1 to 3 words, with a real name: "D7 Retention", not "Came Back After Day 7".
- Put a definition or caveat in `info`: what a measure counts, what the data leaves out. It shows behind a mark beside the title.

## The layout

`create_dashboard` lays out the dashboard from the charts' types, in this order:

1. Filters, in one row at the top.
2. The health strip: every Number reading, up to five a row, filling the width.
3. Trends: charts with a date x, two a row.
4. Breakdowns: charts by category, two a row.
5. Lists: tables, full width.

Within a band the charts keep the order you give. A chart alone in its row takes the full width; `wide: true` asks for it. Lead with the reading that answers the question. Keep a dashboard to about eight charts: every chart must earn its place.

## Filters

- A filter names a `column`. It is linked to every chart whose SQL returns that column, so select the column in every chart it must reach. A chart left unlinked ignores the filter, which reads as a bug: say so.
- A Date filter goes on the date the dashboard is about (`registered_on`, `checked_in_at`). Leave its value empty unless the user asks for a period: a default period hides history.
- A Date filter's `value` and a card's `span` use one grammar: `Last 3 months`, `Current quarter`, `Month to date`, `Next 2 weeks`, over day, week, month, quarter, year or fiscal year. `Last 4 weeks` is four whole weeks and leaves out the running one; `Last 4 weeks (include current)` keeps it.
- A String filter goes on a category (`ticket_type`, `track`) with `operator: "in"`. The reader picks from the values of the linked column, so link a column whose values are the ones to pick from.
- An entity the reader switches between, such as a company or a conference, is a filter. Never one copy of the charts per entity.
- Leave a chart off a filter when its period is fixed by design: a Number card with its own `span`, a cohort chart. Name the charts to link in `charts`.
- A Number card with no `span`, linked to a Date filter on its `x` set to `within`, reads the filter's period, and `compare` steps back from it. A `between` range only narrows its rows: one number, no comparison.

## Check the numbers

A chart that runs is not a chart that is right. Compare the rows each tool returns with SQL of your own, then check:

1. The number means what its title says. An average over a group is the classic trap: compute it a second way and compare.
2. The signal covers the whole range. Group it by month. A series that starts partway through is the date someone began to record it, not growth. One that stops is retired, not fallen.
3. The last period is complete. The newest day, week or month is usually partial and plots as a fall. Read `MAX(<date>)` before you call a drop real.
4. A join did not multiply rows. After each join, `COUNT(*)` equals `COUNT(DISTINCT <key>)` of the record you count. One duplicate row on the right repeats every row it matches.
5. A null bucket after a LEFT JOIN is rows the join did not match. Find out why before you label it.
6. Before you say a status or event does not exist, list every value of its column. It is often there under another name.
7. On ERPNext, run the report the measure comes from with `run_report`, over the same period, and compare the totals. A difference is a definition to explain or fix.

When a check fails, fix the chart. Do not describe the fault and leave it.

## Changing a dashboard

`read_dashboard` returns each chart's spec and current rows. To change a chart, edit its spec and send all of it to `update_chart`. To add one, `add_chart`. `update_dashboard` renames, replaces the filters, removes charts, or lays the dashboard out again with `order`. Never pass `order` unless the user asked for a new layout: it undoes their moves.

A call that fails saves nothing. Fix its input and call it again.

## Your reply

Report the headline numbers and the row counts behind them. Then name what you leaned on, one line each:

- A definition you reused, and the query or report it came from.
- A definition you derived, with the columns you built it from. Ask the user to confirm it: nobody has checked it yet.
- A cut that drops rows: a WHERE, the date the data starts.
- A chart a filter does not reach, and why.
- A chart built ahead of its data: keep it, and say it reads empty until the data arrives.

Caveats go in the reply, never in a title.

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

Every chart selects `registered_on`, so the Date filter reaches all three. Compare the Number card's rows with the SQL total and the Bar's rows with the GROUP BY above.
