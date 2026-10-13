import re

import frappe
from frappe import _
from frappe.utils import cint

from frappe.analytics.api.list_filters import (
    get_content_filters,
    get_last_opened,
    get_shares,
    get_source_filters,
    match_operations,
    match_records,
)
from frappe.analytics.decorators import insights_whitelist
from frappe.analytics.permissions import validate_shareable_users
from frappe.analytics.telemetry import capture_share_granted
from frappe.analytics.utils import DocShare

# Filters the list's filter control declares beyond the workbook's own columns
WORKBOOK_FILTERS = {
    "name": match_records("Insights Workbook", "name"),
    "query": match_records("Insights Query v3", "workbook"),
    "chart": match_records("Insights Chart v3", "workbook"),
    "dashboard": match_records("Insights Dashboard v3", "workbook"),
    "data_source": match_operations("data_source", "workbook"),
    "table_name": match_operations("table_name", "workbook"),
}


@insights_whitelist()
def get_workbooks(
    search_term: str | None = None,
    limit: int = 100,
    sources: list | None = None,
    filters: list | None = None,
):
    """Return workbooks from the chosen sources, last modified first.

    sources: any of "created" (owned by the user), "shared" (given to the user
    by someone else) and "others" (neither; only an admin reads any). Defaults
    to created and shared.
    """
    list_filters = get_content_filters(filters or [], WORKBOOK_FILTERS)
    list_filters += get_source_filters("Insights Workbook", sources)

    workbooks = frappe.get_list(
        "Insights Workbook",
        filters=list_filters,
        or_filters={"title": ["like", f"%{search_term}%"]} if search_term else None,
        fields=["name", "title", "owner", "creation", "modified"],
        order_by="modified desc",
        limit=limit,
    )

    workbook_names = [workbook["name"] for workbook in workbooks]
    # batch the share lookups into two grouped queries instead of ~2 per
    # workbook (avoids an N+1 over the whole list)
    org_shared, shared_users = get_shares("Insights Workbook", workbook_names)
    for workbook in workbooks:
        name = workbook["name"]
        if name in org_shared:
            workbook["shared_with_organization"] = True
            continue
        workbook["shared_with"] = [user for user in shared_users.get(name, []) if user != workbook["owner"]]

    data_sources = _workbook_data_sources(workbook_names)
    last_opened = get_last_opened("Insights Workbook", workbook_names)
    for workbook in workbooks:
        workbook["data_sources"] = data_sources.get(workbook["name"], [])
        workbook["last_opened"] = last_opened.get(workbook["name"])

    return workbooks


def _workbook_data_sources(names: list[str]) -> dict[str, list[str]]:
    """Data sources each workbook's queries read, most used first."""
    counts: dict[str, dict[str, int]] = {}
    for query in frappe.get_all(
        "Insights Query v3", filters={"workbook": ["in", names]}, fields=["workbook", "operations"]
    ):
        for source in re.findall(r'"data_source": "([^"]+)"', query.operations or ""):
            sources = counts.setdefault(query.workbook, {})
            sources[source] = sources.get(source, 0) + 1
    return {name: sorted(sources, key=sources.get, reverse=True) for name, sources in counts.items()}


@insights_whitelist()
def import_workbook(workbook: dict | str):
    from frappe.analytics.doctype.insights_workbook.insights_workbook import import_workbook

    return import_workbook(workbook)


@insights_whitelist()
def get_share_permissions(workbook_name: str):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"), frappe.PermissionError)

    DocShare = frappe.qb.DocType("DocShare")
    User = frappe.qb.DocType("User")

    user_permissions = (
        frappe.qb.from_(DocShare)
        .left_join(User)
        .on(DocShare.user == User.name)
        .select(
            DocShare.user,
            DocShare.read,
            DocShare.write,
            DocShare.share,
            User.full_name,
            User.user_image,
        )
        .where(DocShare.share_doctype == "Insights Workbook")
        .where(DocShare.share_name == workbook_name)
        .where(DocShare.everyone == 0)
        .run(as_dict=True)
    )
    owner = frappe.db.get_value("Insights Workbook", workbook_name, "owner")
    owner_info = frappe.db.get_value("User", owner, ["full_name", "user_image"], as_dict=True) or {}
    user_permissions.append(
        {
            "user": owner,
            "full_name": owner_info.get("full_name"),
            "user_image": owner_info.get("user_image"),
            "read": 1,
            "write": 1,
        }
    )

    public_docshare = frappe.db.get_value(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
            "everyone": 1,
        },
        fieldname=["read", "write"],
        as_dict=True,
    )
    organization_access = None
    if public_docshare:
        organization_access = "edit" if public_docshare["write"] else "view"

    return {
        "user_permissions": user_permissions,
        "organization_access": organization_access,
    }


@insights_whitelist()
def update_share_permissions(
    workbook_name: str, user_permissions: list, organization_access: str | None = None
):
    if not frappe.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        frappe.throw(_("You do not have permission to share this workbook"), frappe.PermissionError)

    existing_shares = frappe.get_all(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
        },
        fields=["name", "user", "everyone", "read", "write"],
    )

    allowed_users = {permission["user"] for permission in user_permissions}
    # The dialog posts back every share it showed, so validate only a new
    # person or a raised access level. Otherwise a kept share with someone who
    # has left Insights would block every later save. A removed person keeps a
    # row with no access, so giving access back counts as raising it.
    held = {share.user: access_level(share) for share in existing_shares if share.user}
    validate_shareable_users(
        {
            permission["user"]
            for permission in user_permissions
            if access_level(permission) > held.get(permission["user"], 0)
        }
    )
    for share in existing_shares:
        if share.user and share.user not in allowed_users:
            frappe.delete_doc("DocShare", share.name, ignore_permissions=True)

    shared_users = {share.user for share in existing_shares if share.user}
    shared_with_organization = any(share.everyone for share in existing_shares)

    for permission in user_permissions:
        doc = DocShare.get_or_create_doc(
            share_doctype="Insights Workbook",
            share_name=workbook_name,
            user=permission["user"],
        )
        doc.read = permission["read"]
        doc.write = permission["write"]
        doc.notify_by_email = 0
        doc.save(ignore_permissions=True)

    public_docshare = DocShare.get_or_create_doc(
        share_doctype="Insights Workbook",
        share_name=workbook_name,
        everyone=1,
    )
    if organization_access:
        public_docshare.read = 1
        public_docshare.write = organization_access == "edit"
        public_docshare.notify_by_email = 0
        public_docshare.save(ignore_permissions=True)
    elif public_docshare.name:
        public_docshare.delete(ignore_permissions=True)

    newly_shared = allowed_users - shared_users
    if newly_shared:
        capture_share_granted("workbook", "user", len(newly_shared))
    if organization_access and not shared_with_organization:
        capture_share_granted("workbook", "org", 1)


def access_level(share) -> int:
    """0 for none, 1 for view, 2 for edit. The dialog posts edit as write
    without read, and a removed person as neither."""
    if cint(share.get("write")):
        return 2
    return 1 if cint(share.get("read")) else 0


# folder Management APIs


@insights_whitelist()
def delete_folder(folder_name: str, move_items_to_root: bool = True):
    """Delete folder and move items to root"""
    folder = frappe.get_doc("Insights Folder", folder_name)
    if not frappe.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        frappe.throw(_("You do not have permission to modify this workbook"), frappe.PermissionError)

    if move_items_to_root:
        # move all queries to root
        frappe.db.set_value(
            "Insights Query v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )
        # move all charts to root
        frappe.db.set_value(
            "Insights Chart v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )

    frappe.delete_doc("Insights Folder", folder_name)


