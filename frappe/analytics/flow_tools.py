"""Tools that let the AI layer (flow) build dashboards with Insights. Listed under the
`flow_tools` hook, so every flow agent can attach them.

A chart is a SQL query that returns one row per record, plus a spec that says how the
chart groups and aggregates those rows. The query stays per row so that dashboard
filters and drill-downs reach the records. The workbook is only the container in the
data model: one per dashboard, never shown."""

import json
from math import ceil
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext
from frappe.analytics.doctype.insights_chart_v3.chart_query import config_errors
from frappe.analytics.doctype.insights_data_source_v3.ibis_utils import get_columns_from_schema

DASHBOARD = "Insights Dashboard v3"
CHART = "Insights Chart v3"
QUERY = "Insights Query v3"
DATA_SOURCE = "Site DB"

GRID_WIDTH = 20
ROW_HEIGHT = 22
CHART_HEIGHT = 15
FILTER_CELL = (4, 2)
STRIP_CARDS = 5
DATE_TYPES = ("Date", "Datetime")
NUMBER_TYPES = ("Integer", "Decimal")
ROWS_RETURNED = 15

Grain = Literal["hour", "day", "week", "month", "quarter", "year"]


class Measure(BaseModel):
    label: str = Field(description="What the reader sees, 1 to 3 words, e.g. Registrations, Revenue")
    aggregation: Literal["count", "count_distinct", "sum", "avg", "min", "max"] = "count"
    column: str | None = Field(default=None, description="Column of the SQL result to aggregate; not used by count")
    format: Literal["currency", "percent"] | None = None
    target: float | None = Field(default=None, description="Number only: the value the reading aims at")
    compare: Literal["previous", "last year"] | None = Field(
        default=None,
        description="Number only: compare with the period before. Needs x with a grain or span, "
        "or a Date dashboard filter set to a `within` value",
    )


class ChartSpec(BaseModel):
    title: str = Field(description="1 to 4 words, no dates, e.g. Revenue by Ticket Type")
    chart_type: Literal["Number", "Line", "Bar", "Row", "Donut", "Funnel", "Table"]
    sql: str = Field(
        description="One MariaDB SELECT over the site's tables (`tabSales Invoice`...) returning one row "
        "per record, with joins and WHERE as needed and no GROUP BY: the chart groups"
    )
    x: str | None = Field(
        default=None,
        description="Column to group by: the x axis, the slices, a funnel's stages, a table's first "
        "column. On a Number card, the date column its grain or span reads",
    )
    grain: Grain | None = Field(default=None, description="Bucket for a date x; hour needs a Datetime column")
    measures: list[Measure] = Field(description="One per series, card reading or table value")
    split_by: str | None = Field(default=None, description="Bar or Line: one series per value of this column")
    table_columns: list[str] | None = Field(default=None, description="Table: more columns to group rows by, after x")
    sort: Literal["value desc", "value asc", "x asc", "x desc"] | None = Field(
        default=None, description="Default: a date x runs forwards, categories by value desc"
    )
    limit: int | None = Field(default=None, description="Rows to plot. Row defaults to 10, categories to 30")
    span: str | None = Field(default=None, description="Number only: the period it reads, e.g. Last 7 days")
    info: str | None = Field(default=None, description="Definition or caveat behind an info mark")
    wide: bool = Field(default=False, description="Take the dashboard's full width")


class Filter(BaseModel):
    label: str = Field(description="e.g. Date, Ticket Type, Day")
    column: str = Field(description="A column the charts' SQL returns")
    type: Literal["Date", "String", "Number"] | None = Field(default=None, description="Default: the column's type")
    operator: str | None = Field(default=None, description="Default operator, e.g. within, in, =, between")
    value: Any = Field(default=None, description="Default value, e.g. Last 30 days. Empty shows every row")
    charts: list[str] | None = Field(
        default=None, description="Chart titles to link. Default: every chart whose SQL returns the column"
    )


# --- queries


def native_operations(sql: str) -> str:
    return json.dumps([{"type": "sql", "raw_sql": sql.strip().rstrip(";"), "data_source": DATA_SOURCE}])


def query_doc(sql: str):
    doc = frappe.new_doc(QUERY)
    doc.name = doc.title = "flow-sql"
    doc.use_live_connection = 1
    doc.is_native_query = 1
    doc.operations = native_operations(sql)
    return doc


def sql_columns(sql: str) -> dict[str, str]:
    """The SQL result's columns and their Insights types. A query that does not run is
    refused with the database's own message."""
    try:
        schema = query_doc(sql).build().schema()
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.throw(_("The SQL does not run: {0}").format(e))
    return {column["name"]: column["type"] for column in get_columns_from_schema(schema)}


def query_sql(query: str) -> str | None:
    operations = frappe.parse_json(frappe.db.get_value(QUERY, query, "operations") or "[]")
    return next((op.get("raw_sql") for op in operations if op.get("type") == "sql"), None)


def json_rows(rows: list) -> list:
    return json.loads(frappe.as_json(rows, indent=None))


# --- a chart's config, from its spec


def column_type(spec: ChartSpec, columns: dict, column: str | None, role: str) -> str:
    if column not in columns:
        frappe.throw(
            _("{0}: {1} {2} is not a column of its SQL, which returns {3}").format(
                spec.title, role, column, ", ".join(columns)
            )
        )
    return columns[column]


def dimension(spec: ChartSpec, columns: dict, column: str | None, role: str = "x") -> dict:
    kind = column_type(spec, columns, column, role)
    dim = {"dimension_name": column, "column_name": column, "data_type": kind}
    if kind in DATE_TYPES:
        grain = spec.grain or "day"
        if grain == "hour" and kind == "Date":
            frappe.throw(_("{0}: {1} is a Date and has no hour. Select a Datetime.").format(spec.title, column))
        dim["granularity"] = grain
    return dim


def measure(spec: ChartSpec, columns: dict, m: Measure) -> dict:
    if m.aggregation == "count":
        out = {"measure_name": m.label, "column_name": "count", "data_type": "Integer", "aggregation": "count"}
    else:
        if not m.column:
            frappe.throw(_("{0}: {1} needs a column to {2}").format(spec.title, m.label, m.aggregation))
        kind = column_type(spec, columns, m.column, "measure column")
        if m.aggregation == "count_distinct":
            kind = "Integer"
        elif kind not in NUMBER_TYPES:
            frappe.throw(
                _("{0}: {1} is a {2}, which has no {3}").format(spec.title, m.column, kind, m.aggregation)
            )
        out = {"measure_name": m.label, "column_name": m.column, "data_type": kind, "aggregation": m.aggregation}
    if m.format:
        out["format"] = m.format
    return out


def number_formats(measures: list[Measure]) -> dict:
    """Counts print whole and money short, so an axis never reads 0.2 registrations."""
    formats = {}
    for m in measures:
        if m.aggregation in ("count", "count_distinct"):
            formats[m.label] = {"decimals": 0}
        elif m.format == "currency":
            formats[m.label] = {"shorten": True}
    return formats


def sort_order(spec: ChartSpec, x_is_date: bool) -> list | None:
    sort = spec.sort or (None if x_is_date else "value desc")
    if not sort:
        return None
    key, direction = sort.split()
    column = spec.x if key == "x" else spec.measures[0].label
    return [{"column": {"type": "column", "column_name": column}, "direction": direction}]


def chart_config(spec: ChartSpec, columns: dict) -> dict:
    if not spec.measures:
        frappe.throw(_("{0} needs a measure").format(spec.title))
    labels = [m.label for m in spec.measures]
    if len(set(labels)) != len(labels):
        frappe.throw(_("{0}: give every measure its own label").format(spec.title))
    measures = [measure(spec, columns, m) for m in spec.measures]
    config = {
        "filters": {"logical_operator": "And", "filters": []},
        "number_formats": number_formats(spec.measures),
    }

    if spec.chart_type == "Number":
        options = []
        for m in spec.measures:
            option = {}
            if m.target is not None:
                option["target"] = {"value": m.target}
            if m.compare:
                option["comparison"] = {"source": m.compare}
            options.append(option)
        config.update({"number_columns": measures, "number_column_options": options, "sparkline": False})
        if spec.x:
            config["date_column"] = {**dimension(spec, columns, spec.x), "granularity": None}
            if spec.span:
                config["window"] = {"span": spec.span}
            elif spec.grain:
                config["window"] = {"grain": spec.grain}
            config["sparkline"] = "window" in config
        elif spec.span or spec.grain:
            frappe.throw(_("{0}: a Number card's grain or span needs x, its date column").format(spec.title))
        return config

    if not spec.x:
        frappe.throw(_("{0}: a {1} chart needs x").format(spec.title, spec.chart_type))
    x = dimension(spec, columns, spec.x)
    x_is_date = x["data_type"] in DATE_TYPES

    if spec.chart_type in ("Donut", "Funnel"):
        config.update({"label_column": x, "value_column": measures[0]})
        if spec.chart_type == "Donut":
            config["max_slices"] = 6
        return config

    if spec.chart_type == "Table":
        rows = [x] + [dimension(spec, columns, c, "table column") for c in spec.table_columns or []]
        config.update({"rows": rows, "columns": [], "values": measures, "limit": spec.limit or 100})
        if sort := sort_order(spec, x_is_date):
            config["order_by"] = sort
        return config

    config["x_axis"] = {"dimension": x}
    config["y_axis"] = {"series": [{"measure": m} for m in measures]}
    if spec.split_by:
        split = dimension(spec, columns, spec.split_by, "split_by")
        config["split_by"] = {"dimension": split, "max_split_values": 8}
        if spec.chart_type == "Bar":
            config["y_axis"]["stack"] = True
    if sort := sort_order(spec, x_is_date):
        config["order_by"] = sort
    config["limit"] = spec.limit or (10 if spec.chart_type == "Row" else 1000 if x_is_date else 30)
    return config


def checked_config(spec: ChartSpec, columns: dict) -> dict:
    config = chart_config(spec, columns)
    if errors := config_errors(spec.chart_type, "flow-sql", config):
        frappe.throw(_("{0}: {1}").format(spec.title, "; ".join(errors)))
    return config


# --- a chart's spec, read back from its documents


def measure_spec(m: dict, option: dict | None = None) -> dict:
    out = {"label": m.get("measure_name"), "aggregation": m.get("aggregation")}
    if m.get("aggregation") != "count":
        out["column"] = m.get("column_name")
    if m.get("format"):
        out["format"] = m["format"]
    option = option or {}
    if (option.get("target") or {}).get("value") is not None:
        out["target"] = option["target"]["value"]
    if (option.get("comparison") or {}).get("source") in ("previous", "last year"):
        out["compare"] = option["comparison"]["source"]
    return out


def spec_of(chart) -> dict:
    """The spec that builds this chart as it is now, including a person's edits to its
    type or SQL. A change is this spec, edited and sent to update_chart."""
    config = frappe.parse_json(chart.config or "{}")
    spec = {"title": chart.title, "chart_type": chart.chart_type, "sql": query_sql(chart.query)}
    if chart.info:
        spec["info"] = chart.info

    if chart.chart_type == "Number":
        options = config.get("number_column_options") or []
        columns = config.get("number_columns") or []
        spec["measures"] = [measure_spec(m, options[i] if i < len(options) else None) for i, m in enumerate(columns)]
        if date := config.get("date_column"):
            spec["x"] = date.get("column_name")
        window = config.get("window") or {}
        for key in ("grain", "span"):
            if window.get(key):
                spec[key] = window[key]
        return spec

    if chart.chart_type in ("Donut", "Funnel"):
        x, measures = config.get("label_column") or {}, [config.get("value_column") or {}]
    elif chart.chart_type == "Table":
        rows = config.get("rows") or [{}]
        x, measures = rows[0], config.get("values") or []
        if len(rows) > 1:
            spec["table_columns"] = [row.get("column_name") for row in rows[1:]]
    else:
        x = (config.get("x_axis") or {}).get("dimension") or {}
        measures = [series.get("measure") or {} for series in (config.get("y_axis") or {}).get("series") or []]
        if split := ((config.get("split_by") or {}).get("dimension") or {}).get("column_name"):
            spec["split_by"] = split
    spec["x"] = x.get("column_name")
    if x.get("granularity"):
        spec["grain"] = x["granularity"]
    spec["measures"] = [measure_spec(m) for m in measures]
    if sort := (config.get("order_by") or [None])[0]:
        key = "x" if sort["column"]["column_name"] == spec["x"] else "value"
        spec["sort"] = f"{key} {sort['direction']}"
    if config.get("limit"):
        spec["limit"] = config["limit"]
    return spec


# --- the dashboard grid


def number_cell_rows(config: dict, index: int) -> int:
    """A reading's height in grid rows, measured as the client's `numberCardRows` does."""
    options = config.get("number_column_options") or []
    option = options[index] if index < len(options) else {}
    sparkline = bool(config.get("sparkline") and config.get("date_column"))
    line = 13 * 1.35
    height = 16 + 18 + line + 6 + 20 * 1.35
    if option.get("comparison") or sparkline:
        height += 6 + line
    if sparkline:
        height += 40
    if option.get("target"):
        height += 6 + line
    return ceil(height / ROW_HEIGHT)


def band(chart: dict) -> int:
    """Where a chart goes: the strip of number cards, then trends, then breakdowns, then
    tables."""
    if chart["chart_type"] == "Number":
        return 0
    if chart["chart_type"] == "Table":
        return 3
    x = (chart["config"].get("x_axis") or {}).get("dimension") or {}
    return 1 if x.get("data_type") in DATE_TYPES else 2


def spread(count: int) -> list[int]:
    """Widths for `count` cells that fill one grid row between them."""
    base, extra = divmod(GRID_WIDTH, count)
    return [base + (1 if i < extra else 0) for i in range(count)]


def reading_of(m: dict) -> str:
    return m.get("id") or m["measure_name"]


def layout(charts: list[dict], filters: list[dict]) -> list[dict]:
    """Filters in the top row, a strip of number cards, then two charts to a row:
    trends, then breakdowns, then tables at full width. A chart alone in its row takes
    the whole row, so no tile sits beside empty space."""
    items, y = [], 0
    for index, item in enumerate(filters):
        w, h = FILTER_CELL
        per_row = GRID_WIDTH // w
        item["layout"] = {"i": f"filter-{index}", "x": index % per_row * w, "y": index // per_row * h, "w": w, "h": h}
        items.append(item)
    if filters:
        y = ceil(len(filters) / (GRID_WIDTH // FILTER_CELL[0])) * FILTER_CELL[1]

    cells = [
        (chart, index, reading_of(m))
        for chart in charts
        if band(chart) == 0
        for index, m in enumerate(chart["config"]["number_columns"])
    ]
    for start in range(0, len(cells), STRIP_CARDS):
        row = cells[start : start + STRIP_CARDS]
        h = max(number_cell_rows(chart["config"], index) for chart, index, _r in row)
        x = 0
        for (chart, _i, reading), w in zip(row, spread(len(row)), strict=True):
            cell = {"i": f"{chart['name']}-{reading}", "x": x, "y": y, "w": w, "h": h}
            items.append({"type": "chart", "chart": chart["name"], "reading": reading, "layout": cell})
            x += w
        y += h

    row: list[dict] = []

    def close_row():
        nonlocal y
        for i, chart in enumerate(row):
            w = GRID_WIDTH // len(row)
            cell = {"i": chart["name"], "x": i * w, "y": y, "w": w, "h": CHART_HEIGHT}
            items.append({"type": "chart", "chart": chart["name"], "layout": cell})
        if row:
            y += CHART_HEIGHT
        row.clear()

    previous_band = None
    for chart in sorted((chart for chart in charts if band(chart)), key=band):
        if band(chart) != previous_band:
            close_row()
            previous_band = band(chart)
        if chart["wide"] or band(chart) == 3:
            close_row()
            row.append(chart)
            close_row()
            continue
        row.append(chart)
        if len(row) == 2:
            close_row()
    close_row()
    return items


def filter_type(column_type: str) -> str:
    if column_type in DATE_TYPES:
        return "Date"
    return "Number" if column_type in NUMBER_TYPES else "String"


def filter_items(specs: list[Filter], charts: list[dict]) -> list[dict]:
    """Dashboard filters, each linked to the charts whose query returns its column."""
    items = []
    for spec in specs:
        named = set(spec.charts or [])
        if unknown := named - {c["title"] for c in charts} - {c["name"] for c in charts}:
            frappe.throw(_("Filter {0} names no chart called {1}").format(spec.label, ", ".join(unknown)))
        links, kind = {}, spec.type
        for chart in charts:
            if named and not named & {chart["title"], chart["name"]}:
                continue
            if spec.column not in chart["columns"]:
                if named:
                    frappe.throw(
                        _("Filter {0}: the SQL of {1} returns no {2}").format(spec.label, chart["title"], spec.column)
                    )
                continue
            links[chart["name"]] = f"`{chart['query']}`.`{spec.column}`"
            kind = kind or filter_type(chart["columns"][spec.column])
        if not links:
            frappe.throw(_("Filter {0}: no chart's SQL returns {1}").format(spec.label, spec.column))
        item = {"type": "filter", "filter_name": spec.label, "filter_type": kind, "links": links}
        if spec.operator:
            item["default_operator"] = spec.operator
        if spec.value not in (None, "", []):
            item["default_value"] = spec.value
        items.append(item)
    return items


def filter_column(item: dict) -> str | None:
    """The column a filter item reads, from the first of its links."""
    link = next(iter((item.get("links") or {}).values()), None)
    return link.split("`.`")[-1].strip("`") if link else None


def items_bottom(items: list[dict]) -> int:
    return max((item["layout"]["y"] + item["layout"]["h"] for item in items if item.get("layout")), default=0)


# --- documents


def save_chart(workbook: str, spec: ChartSpec, chart=None) -> dict:
    """Write a chart and its own query from a spec. `chart` is the chart to change."""
    columns = sql_columns(spec.sql)
    config = checked_config(spec, columns)
    if chart:
        query = frappe.get_doc(QUERY, chart.query)
        query.update(
            {"title": spec.title, "operations": native_operations(spec.sql), "is_native_query": 1, "is_builder_query": 0}
        )
        query.save()
    else:
        query = frappe.get_doc(
            {
                "doctype": QUERY,
                "workbook": workbook,
                "title": spec.title,
                "use_live_connection": 1,
                "is_native_query": 1,
                "operations": native_operations(spec.sql),
            }
        ).insert()
        chart = frappe.new_doc(CHART)
        chart.workbook = workbook
        chart.query = query.name
    chart.update({"title": spec.title, "chart_type": spec.chart_type, "info": spec.info, "config": json.dumps(config)})
    chart.save()
    return {
        "name": chart.name,
        "title": spec.title,
        "chart_type": spec.chart_type,
        "query": query.name,
        # read back: saving names each reading, and a dashboard cell points at that name
        "config": frappe.parse_json(frappe.db.get_value(CHART, chart.name, "config")),
        "columns": columns,
        "wide": spec.wide,
    }


def chart_inputs(dashboard) -> list[dict]:
    """The dashboard's charts in the shape `layout` and `filter_items` read."""
    out = []
    for chart in dashboard_charts(dashboard):
        sql = query_sql(chart.query)
        out.append(
            {
                "name": chart.name,
                "title": chart.title,
                "chart_type": chart.chart_type,
                "query": chart.query,
                "config": frappe.parse_json(chart.config or "{}"),
                "columns": sql_columns(sql) if sql else {},
                "wide": False,
            }
        )
    return out


def dashboard_charts(dashboard) -> list:
    items = frappe.parse_json(dashboard.items or "[]")
    names = dict.fromkeys(item["chart"] for item in items if item.get("type") == "chart")
    return [frappe.get_doc(CHART, name) for name in names]


def chart_result(chart: str, dashboard: str | None = None) -> dict:
    """The chart's rows as the dashboard shows them, so the numbers can be checked."""
    from frappe.analytics.api import view

    result = view.get_chart_data(chart=chart, dashboard=dashboard)
    if result.get("errors"):
        return {"errors": result["errors"]}
    rows = result.get("rows") or []
    return {"rows": json_rows(rows[:ROWS_RETURNED]), "row_count": len(rows)}


def describe_dashboard(dashboard) -> dict:
    items = frappe.parse_json(dashboard.items or "[]")
    filters = [
        {
            "label": item["filter_name"],
            "column": filter_column(item),
            "type": item.get("filter_type"),
            "operator": item.get("default_operator"),
            "value": item.get("default_value"),
            "charts": list(item.get("links") or {}),
        }
        for item in items
        if item.get("type") == "filter"
    ]
    charts = [
        {"name": chart.name, "spec": spec_of(chart), **chart_result(chart.name, dashboard.name)}
        for chart in dashboard_charts(dashboard)
    ]
    route = artifacts.route(DASHBOARD, dashboard.name)
    return {"dashboard": dashboard.name, "title": dashboard.title, "route": route, "filters": filters, "charts": charts}


def writable_dashboard(name: str):
    doc = frappe.get_doc(DASHBOARD, name)
    doc.check_permission("write")
    return doc


def linked(ctx: ToolContext, dashboard: str) -> dict | None:
    return artifacts.link(ctx.session_id, DASHBOARD, dashboard) if ctx.session_id else None


# --- tools


@tool
def list_dashboards(*, ctx: ToolContext) -> list[dict]:
    """List the dashboards the user can open, newest first, with their links."""
    dashboards = frappe.get_list(DASHBOARD, fields=["name", "title"], order_by="modified desc", limit=30)
    return [{**d, "route": artifacts.route(DASHBOARD, d.name)} for d in dashboards]


@tool
def read_dashboard(dashboard: Annotated[str, "Dashboard name"], *, ctx: ToolContext) -> dict:
    """A dashboard's filters and charts: each chart's spec, as update_chart takes it, and
    the rows it shows now. Read it before a change, and to answer questions about the
    numbers."""
    doc = frappe.get_doc(DASHBOARD, dashboard)
    doc.check_permission("read")
    return describe_dashboard(doc)


@tool
def run_query(
    sql: Annotated[str, "One MariaDB SELECT over the site's tables"],
    limit: Annotated[int, "Rows to return, at most 200"] = 20,
    *,
    ctx: ToolContext,
) -> dict:
    """Run a SQL SELECT on the site's database under the user's permissions. Returns the
    columns with their types and the first rows. Try a chart's SQL here before charting
    it, and check a number by aggregating in SQL."""
    result = query_doc(sql).execute(page_size=min(max(limit, 1), 200))
    return {"columns": result["columns"], "rows": json_rows(result["rows"])}


@tool(
    requires_confirmation=True,
    confirm_prompt=lambda args: _("Create the dashboard {0}").format(args.get("title")),
)
def create_dashboard(
    title: Annotated[str, "Dashboard title"],
    charts: Annotated[list[ChartSpec], "Every chart and number card, in reading order"],
    filters: Annotated[list[Filter] | None, "Dashboard filters"] = None,
    *,
    ctx: ToolContext,
) -> dict:
    """Build a dashboard over the site's own data; it opens beside the chat. Each chart is
    its own SQL query plus a spec. Number cards form a strip on top, then trends, then
    breakdowns, then tables. Each filter is linked to every chart whose SQL returns its
    column. Returns each chart's rows: check the numbers before you report them."""
    for spec in charts:
        checked_config(spec, sql_columns(spec.sql))
    workbook = frappe.get_doc({"doctype": "Insights Workbook", "title": title}).insert()
    saved = [save_chart(workbook.name, spec) for spec in charts]
    items = layout(saved, filter_items(filters or [], saved))
    dashboard = frappe.get_doc(
        {
            "doctype": DASHBOARD,
            "workbook": workbook.name,
            "title": title,
            "items": json.dumps(items),
            "vertical_compact_layout": 1,
        }
    ).insert()
    return {**describe_dashboard(dashboard), "artifact": linked(ctx, dashboard.name)}


@tool
def add_chart(
    dashboard: Annotated[str, "Dashboard name"],
    chart: Annotated[ChartSpec, "The chart or number card to add"],
    *,
    ctx: ToolContext,
) -> dict:
    """Add a chart or number card at the bottom of a dashboard, linked to every dashboard
    filter whose column its SQL returns."""
    doc = writable_dashboard(dashboard)
    saved = save_chart(doc.workbook, chart)
    items = frappe.parse_json(doc.items or "[]")
    bottom = items_bottom(items)
    for item in layout([saved], []):
        item["layout"]["y"] += bottom
        items.append(item)
    for item in items:
        column = filter_column(item) if item.get("type") == "filter" else None
        if column in saved["columns"]:
            item["links"][saved["name"]] = f"`{saved['query']}`.`{column}`"
    doc.items = json.dumps(items)
    doc.save()
    return {"chart": saved["name"], **chart_result(saved["name"], doc.name), "artifact": linked(ctx, doc.name)}


@tool
def update_chart(
    chart: Annotated[str, "Chart name"],
    spec: Annotated[ChartSpec, "The whole new spec: the one read_dashboard returns, edited"],
    *,
    ctx: ToolContext,
) -> dict:
    """Change a chart's SQL, type, axes, measures, targets or title. It keeps its place on
    every dashboard, and its filter links."""
    doc = frappe.get_doc(CHART, chart)
    doc.check_permission("write")
    saved = save_chart(doc.workbook, spec, doc)
    dashboards = frappe.get_all(
        "Insights Dashboard Chart v3", filters={"chart": chart, "parenttype": DASHBOARD}, pluck="parent"
    )
    for name in dashboards:
        place_readings(frappe.get_doc(DASHBOARD, name), saved)
    dashboard = dashboards[0] if dashboards else None
    return {"chart": chart, **chart_result(chart, dashboard), "artifact": linked(ctx, dashboard) if dashboard else None}


def place_readings(dashboard, saved: dict) -> None:
    """A number card has a cell per reading, so a reading renamed, added or removed
    gets its cells laid out again where the card's first cell was."""
    items = frappe.parse_json(dashboard.items or "[]")
    cells = [item for item in items if item.get("chart") == saved["name"]]
    if saved["chart_type"] == "Number":
        wanted = [reading_of(m) for m in saved["config"]["number_columns"]]
    else:
        wanted = [None]
    if [cell.get("reading") for cell in cells] == wanted:
        return
    top = cells[0]["layout"]["y"] if cells else items_bottom(items)
    fresh = [item for item in layout([saved], []) if item.get("chart")]
    for item in fresh:
        item["layout"]["y"] += top
    dashboard.items = json.dumps(fresh + [item for item in items if item.get("chart") != saved["name"]])
    dashboard.save()


@tool
def update_dashboard(
    dashboard: Annotated[str, "Dashboard name"],
    title: Annotated[str | None, "New title"] = None,
    filters: Annotated[list[Filter] | None, "Replaces every dashboard filter"] = None,
    remove_charts: Annotated[list[str] | None, "Names of the charts to take off the dashboard"] = None,
    order: Annotated[list[str] | None, "Chart names in reading order. Lays the whole dashboard out again"] = None,
    *,
    ctx: ToolContext,
) -> dict:
    """Rename a dashboard, set its filters, take charts off it, or lay it out again. A
    person's moves and resizes stay unless `order` is given."""
    doc = writable_dashboard(dashboard)
    if title:
        doc.title = title
    items = frappe.parse_json(doc.items or "[]")
    if remove_charts:
        items = [item for item in items if item.get("chart") not in remove_charts]
        for item in items:
            if item.get("type") == "filter":
                item["links"] = {k: v for k, v in (item.get("links") or {}).items() if k not in remove_charts}
        doc.items = json.dumps(items)
    charts = chart_inputs(doc) if filters is not None or order else []

    if filters is not None:
        old = {item["filter_name"]: item.get("layout") for item in items if item.get("type") == "filter"}
        fresh = filter_items(filters, charts)
        items = [item for item in items if item.get("type") != "filter"]
        new = [item for item in fresh if not old.get(item["filter_name"])]
        if new and not order:
            # new filters take a row of their own at the top, as the app adds them
            for item in items:
                item["layout"]["y"] += FILTER_CELL[1]
            for index, item in enumerate(new):
                w, h = FILTER_CELL
                item["layout"] = {"i": frappe.generate_hash(length=8), "x": index * w % GRID_WIDTH, "y": 0, "w": w, "h": h}
        for item in fresh:
            item["layout"] = old.get(item["filter_name"]) or item.get("layout")
        items = fresh + items

    if order:
        by_name = {chart["name"]: chart for chart in charts}
        if unknown := set(order) - set(by_name):
            frappe.throw(_("{0} is not on this dashboard").format(", ".join(unknown)))
        ordered = [by_name[name] for name in order] + [c for c in charts if c["name"] not in order]
        texts = [item for item in items if item.get("type") == "text"]
        items = layout(ordered, [item for item in items if item.get("type") == "filter"])
        bottom = items_bottom(items)
        for item in texts:
            item["layout"]["y"] = bottom
        items += texts

    doc.items = json.dumps(items)
    doc.save()
    return {**describe_dashboard(doc), "artifact": linked(ctx, doc.name)}
