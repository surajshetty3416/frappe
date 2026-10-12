"""Tools that let the AI layer (flow) build reports with Insights. Listed under the
`flow_tools` hook, so every flow agent can attach them."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

import frappe
from frappe import _
from frappe.ai import artifacts, tool
from frappe.ai.lib.tool import ToolContext

DATA_TYPES = {
    "Date": "Date",
    "Datetime": "Datetime",
    "Int": "Integer",
    "Check": "Integer",
    "Float": "Decimal",
    "Currency": "Decimal",
    "Percent": "Decimal",
}
STANDARD_DATA_TYPES = {"creation": "Datetime", "modified": "Datetime", "docstatus": "Integer", "idx": "Integer"}
GRID_WIDTH = 20


class ChartSpec(BaseModel):
    title: str = Field(description="Chart title, stating the measure and grain, e.g. Open Tasks per Owner")
    doctype: str = Field(description="The DocType the chart reads, e.g. ToDo")
    chart_type: Literal["Number", "Bar", "Line", "Row", "Donut"]
    group_by: str | None = Field(
        default=None, description="Field to group by (the x axis or slices). Not used by Number."
    )
    granularity: Literal["day", "week", "month", "quarter", "year"] | None = Field(
        default=None, description="Bucket for a date group_by, e.g. month"
    )
    aggregation: Literal["count", "sum", "avg", "min", "max"] = "count"
    measure_field: str | None = Field(default=None, description="Numeric field to aggregate; not used by count")


def data_type(doctype: str, fieldname: str) -> str:
    if fieldname in STANDARD_DATA_TYPES:
        return STANDARD_DATA_TYPES[fieldname]
    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field:
        frappe.throw(_("{0} has no field {1}").format(doctype, fieldname))
    return DATA_TYPES.get(field.fieldtype, "String")


def measure(spec: ChartSpec) -> dict:
    if spec.aggregation == "count":
        return {"measure_name": "Count", "column_name": "count", "data_type": "Integer", "aggregation": "count"}
    if not spec.measure_field:
        frappe.throw(_("{0} needs a measure_field to {1}").format(spec.title, spec.aggregation))
    return {
        "measure_name": f"{spec.aggregation.title()} of {spec.measure_field}",
        "column_name": spec.measure_field,
        "data_type": data_type(spec.doctype, spec.measure_field),
        "aggregation": spec.aggregation,
    }


def dimension(spec: ChartSpec) -> dict:
    if not spec.group_by:
        frappe.throw(_("A {0} chart needs a group_by field").format(spec.chart_type))
    kind = data_type(spec.doctype, spec.group_by)
    dim = {"dimension_name": spec.group_by, "column_name": spec.group_by, "data_type": kind}
    if kind in ("Date", "Datetime"):
        dim["granularity"] = spec.granularity or "month"
    return dim


def chart_config(spec: ChartSpec) -> dict:
    if spec.chart_type == "Number":
        return {"number_columns": [measure(spec)]}
    if spec.chart_type == "Donut":
        return {"label_column": dimension(spec), "value_column": measure(spec), "max_slices": 8}
    config = {
        "x_axis": {"dimension": dimension(spec)},
        "y_axis": {"series": [{"measure": measure(spec)}]},
        "filters": {"logical_operator": "And", "filters": []},
    }
    if spec.chart_type == "Row":
        config["order_by"] = [{"column": {"type": "column", "column_name": measure(spec)["measure_name"]}, "direction": "desc"}]
        config["limit"] = 10
    return config


def layout(charts: list[ChartSpec]) -> list[dict]:
    """Number cards in a row on top, the other charts two to a row below them."""
    items, numbers, others = [], 0, 0
    for index, spec in enumerate(charts):
        if spec.chart_type == "Number":
            box = {"x": numbers * 4 % GRID_WIDTH, "y": 0, "w": 4, "h": 5}
            numbers += 1
        else:
            box = {"x": others % 2 * 10, "y": 5 + others // 2 * 16, "w": 10, "h": 16}
            others += 1
        items.append({"type": "chart", "chart": f"c-{index}", "layout": {"i": f"item-{index}", **box}})
    return items


def workbook_file(title: str, charts: list[ChartSpec]) -> dict:
    queries, chart_docs = {}, {}
    for index, spec in enumerate(charts):
        if not frappe.has_permission(spec.doctype, "read"):
            frappe.throw(_("You cannot read {0}").format(spec.doctype), frappe.PermissionError)
        queries[f"q-{index}"] = {
            "name": f"q-{index}",
            "title": spec.doctype,
            "workbook": "wb",
            "use_live_connection": 1,
            "is_builder_query": 1,
            "operations": [
                {
                    "type": "source",
                    "table": {"type": "table", "data_source": "Site DB", "table_name": f"tab{spec.doctype}"},
                }
            ],
        }
        chart_docs[f"c-{index}"] = {
            "name": f"c-{index}",
            "title": spec.title,
            "workbook": "wb",
            "query": f"q-{index}",
            "chart_type": spec.chart_type,
            "config": chart_config(spec),
        }
    return {
        "doctype": "Insights Workbook",
        "name": "wb",
        "title": title,
        "queries": queries,
        "charts": chart_docs,
        "dashboards": {"d-0": {"name": "d-0", "title": title, "workbook": "wb", "items": layout(charts)}},
    }


@tool
def list_dashboards(*, ctx: ToolContext) -> list[dict]:
    """List the Insights dashboards the user can open, newest first, with their links."""
    dashboards = frappe.get_list(
        "Insights Dashboard v3", fields=["name", "title", "workbook"], order_by="modified desc", limit=30
    )
    return [{**d, "url": artifacts.route("Insights Dashboard v3", d.name)} for d in dashboards]


@tool(
    requires_confirmation=True,
    confirm_prompt=lambda args: _("Create the dashboard {0}").format(args.get("title")),
)
def create_dashboard(
    title: Annotated[str, "Dashboard title"],
    charts: Annotated[list[ChartSpec], "One entry per chart, in reading order"],
    *,
    ctx: ToolContext,
) -> dict:
    """Build an Insights dashboard over the site's own data: one query and one chart per entry,
    laid out on a new dashboard in a new workbook, whose editor opens beside the chat. Check
    field names with describe first."""
    from frappe.analytics.doctype.insights_workbook.insights_workbook import import_workbook

    result = import_workbook(workbook_file(title, charts))
    dashboard = artifacts.link(ctx.session_id, "Insights Dashboard v3", result["names"]["d-0"])
    # linked last, so the workbook is the chat's newest artifact: its editor shows the dashboard
    workbook = artifacts.link(ctx.session_id, "Insights Workbook", result["workbook"])
    return {"dashboard": dashboard["route"], "workbook": workbook["route"], "artifact": workbook}
