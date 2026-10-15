"""The people the Frappeverse demo is shown as, each starting from the home: a volunteer who reads what
was built, a program lead who may change one dashboard, and a builder who edits everything in Studio.
They get the demo project's artifacts through shares, as a team would hand them out."""

import json
from typing import Any

import frappe
from frappe.ai.home import LAYOUT_KEY, clean, viewable
from frappe.ai.permissions import ASSISTANT_USER_ROLE
from frappe.analytics.permissions import workbook_of
from frappe.desk.like import _toggle_like
from frappe.share import add_docshare
from frappe.utils.password import update_password

PERSONAS = [
	{
		"email": "neha@example.com",
		"first_name": "Neha",
		"last_name": "Kulkarni",
		"persona": "Viewer: reads the dashboards and apps, asks the chat about them",
		"roles": [ASSISTANT_USER_ROLE, "Analytics User", "Volunteer"],
		"write": [],
		"pin": ["Insights Dashboard v3"],
	},
	{
		"email": "rahul@example.com",
		"first_name": "Rahul",
		"last_name": "Menon",
		"persona": "Program lead: reads everything, may edit the dashboards",
		"roles": [ASSISTANT_USER_ROLE, "Analytics User", "Program Committee", "Volunteer"],
		"write": ["Insights Dashboard v3"],
		"pin": ["Insights Dashboard v3", "Studio App"],
		"home": [
			{"type": "embed", "doctype": "Insights Dashboard v3"},
			{"type": "pinned"},
			{"type": "recent"},
		],
	},
	{
		"email": "arjun@example.com",
		"first_name": "Arjun",
		"last_name": "Shah",
		"persona": "Builder: edits every artifact in Studio",
		"roles": [
			ASSISTANT_USER_ROLE,
			"System Manager",
			"Website Manager",
			"App Manager",
			"Analytics Manager",
		],
		"write": None,
		"pin": ["Builder Page"],
	},
]


def setup_personas(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
	"""Each persona as a user with a new password, sharing and pinning the demo's `artifacts`; their
	logins, for whoever shows the demo."""
	logins = []
	for persona in PERSONAS:
		user = ensure_user(persona)
		for artifact in artifacts:
			doctype, name = artifact["doctype"], artifact["name"]
			if persona["write"] is not None:
				share(doctype, name, user, write=doctype in persona["write"])
			if doctype in persona["pin"] and artifact is first_of(artifacts, doctype):
				_toggle_like(doctype, name, "Yes", user=user)
		if persona.get("home"):
			set_home(user, persona["home"], artifacts)
		password = frappe.generate_hash(length=12)
		update_password(user, password)
		logins.append({"user": user, "password": password, "persona": persona["persona"]})
	frappe.db.commit()
	return logins


def share(doctype: str, name: str, user: str, write: bool) -> None:
	"""Share the artifact with `user`; a dashboard is changed through its workbook, so that is what
	a writer gets."""
	flags = {"ignore_share_permission": True}
	if write and doctype == "Insights Dashboard v3":
		workbook = workbook_of(frappe.get_doc(doctype, name))
		add_docshare("Insights Workbook", workbook, user, read=1, write=1, flags=flags)
		write = False
	add_docshare(doctype, name, user, read=1, write=int(write), flags=flags)


def set_home(user: str, sections: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> None:
	"""The persona's own home; an embedded section shows the demo's first artifact of its DocType."""
	sections = [dict(section) for section in sections]
	for section in sections:
		if section["type"] == "embed":
			section["name"] = (first_of(artifacts, section["doctype"]) or {}).get("name")
	sections = [section for section in sections if section["type"] != "embed" or section["name"]]
	frappe.defaults.set_user_default(LAYOUT_KEY, json.dumps(clean(sections)), user)


def ensure_user(persona: dict[str, Any]) -> str:
	if not frappe.db.exists("User", persona["email"]):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": persona["email"],
				"first_name": persona["first_name"],
				"last_name": persona["last_name"],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", persona["email"]).add_roles(*persona["roles"])
	return persona["email"]


def first_of(artifacts: list[dict[str, Any]], doctype: str) -> dict[str, Any] | None:
	return next((artifact for artifact in artifacts if artifact["doctype"] == doctype), None)


def demo_artifacts(project: str) -> list[dict[str, Any]]:
	"""What the demo project's chats made that the home can open."""
	types = viewable()
	return [
		{"doctype": row.reference_doctype, "name": row.reference_name}
		for row in frappe.get_doc("Studio Project", project).artifacts
		if row.reference_doctype in types and frappe.db.exists(row.reference_doctype, row.reference_name)
	]
