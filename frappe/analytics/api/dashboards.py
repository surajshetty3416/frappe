import frappe
from frappe.query_builder.functions import Count

from frappe.analytics.decorators import insights_whitelist
from frappe.analytics.permissions import can_write


def dashboard_view_counts(names: list[str], since: str | None = None) -> dict[str, int]:
    """Opens per dashboard, over every open or only those after `since`."""
    if not names:
        return {}
    view_log = frappe.qb.DocType("View Log")
    query = (
        frappe.qb.from_(view_log)
        .select(view_log.reference_name, Count(view_log.name).as_("views"))
        .where(
            (view_log.reference_doctype == "Insights Dashboard v3")
            # reference_name is stored as a string; cast names to match
            & view_log.reference_name.isin([str(name) for name in names])
        )
        .groupby(view_log.reference_name)
    )
    if since:
        query = query.where(view_log.creation >= since)
    rows = query.run(as_dict=True)
    return {str(row.reference_name): row.views for row in rows}


@insights_whitelist(methods=["POST"])
def update_dashboard_preview(dashboard_name: str):
    """Regenerate the preview image from the caller's rows.

    Every reader of the dashboard list sees this image, so only an editor may
    regenerate it. A save regenerates it too.
    """
    frappe.has_permission("Insights Dashboard v3", ptype="read", doc=dashboard_name, throw=True)
    dashboard = frappe.get_doc("Insights Dashboard v3", dashboard_name)
    if not can_write(dashboard):
        frappe.throw(
            frappe._("Only an editor of this dashboard can refresh its preview"), frappe.PermissionError
        )
    return dashboard.generate_dashboard_preview()
