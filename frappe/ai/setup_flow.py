# Copyright (c) 2026, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""The admin's first run, three short steps with the assistant beside them: the organization, its
Spaces and its people. Each step comes filled in with a guess and can be skipped; the assistant's
setup tools (frappe.ai.workspace) do the same things from a conversation."""

from __future__ import annotations

import json
from typing import Any

import pytz

import frappe
from frappe import _
from frappe.ai.permissions import ASSISTANT_USER_ROLE
from frappe.ai.spaces import create_space, templates, visible_spaces

FREE_MAIL = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me", "example.com"}


@frappe.whitelist()
def get_setup(time_zone: str | None = None) -> dict[str, Any]:
	"""What the steps start from: guesses for the organization, the Spaces the installed apps offer,
	and the Workspaces they already have."""
	frappe.only_for("System Manager")
	from frappe.ai.workspace import organization

	settings = frappe.get_single("System Settings")
	time_zone = settings.time_zone or time_zone
	country = settings.country or country_of(time_zone)
	saved = organization() or {}
	domain = frappe.session.user.rpartition("@")[2]
	return {
		"organization": {
			"name": saved.get("name")
			or (domain.split(".")[0].title() if domain and domain not in FREE_MAIL else ""),
			"about": saved.get("about") or "",
			"country": country,
			"currency": settings.currency
			or (country and frappe.db.get_value("Country", country, "default_currency")),
			"time_zone": time_zone,
			"language": settings.language or "en",
		},
		"templates": [
			{key: template.get(key) for key in ("name", "title", "icon", "description", "app")}
			for template in templates()
		],
		"workspaces": [
			space for space in visible_spaces() if not frappe.db.exists("Space Member", {"space": space.name})
		],
		"roles": frappe.get_all(
			"Role",
			filters={"disabled": 0, "desk_access": 1, "name": ("not in", ("Administrator", "Guest", "All"))},
			pluck="name",
			order_by="name",
		),
	}


@frappe.whitelist(methods=["POST"])
def save_organization(
	organization: str, about: str, country: str, currency: str, time_zone: str, language: str = "en"
) -> None:
	"""The organization's name and what it does, and its country, currency, time zone and language."""
	frappe.only_for("System Manager")
	settings = frappe.get_single("System Settings")
	settings.update({"country": country, "currency": currency, "time_zone": time_zone, "language": language})
	settings.save()
	for key in ("country", "currency", "time_zone"):
		frappe.db.set_default(key, settings.get(key))
	frappe.db.set_value("Currency", currency, "enabled", 1)
	from frappe.ai.workspace import ORGANIZATION_KEY

	frappe.defaults.set_global_default(ORGANIZATION_KEY, json.dumps({"name": organization, "about": about}))


@frappe.whitelist(methods=["POST"])
def save_spaces(templates_chosen: list[str] | str, workspaces: list[str] | str) -> list[str]:
	"""Set up the Spaces from the chosen templates, and join the chosen Workspaces apps brought."""
	frappe.only_for("System Manager")
	from frappe.ai.spaces import join_space

	offered = {template["name"]: template for template in templates()}
	made = [create_space(offered[name]) for name in frappe.parse_json(templates_chosen) if name in offered]
	for space in frappe.parse_json(workspaces):
		join_space(space)
		made.append(space)
	return made


@frappe.whitelist(methods=["POST"])
def invite(people: list[dict[str, Any]] | str) -> list[dict[str, Any]]:
	"""Invite each person, {email, first_name?, spaces}, into their Spaces with the roles those Spaces
	need. Their Home is ready when they first sign in."""
	frappe.only_for("System Manager")
	invited = []
	for person in frappe.parse_json(people):
		email = person["email"].strip().lower()
		spaces = person.get("spaces") or []
		roles = {row.role for space in spaces for row in frappe.get_doc("Workspace", space).roles}
		invited.append(invite_person(email, person.get("first_name"), [*roles, *(person.get("roles") or [])]))
		for space in spaces:
			if not frappe.db.exists("Space Member", {"space": space, "user": email}):
				frappe.get_doc({"doctype": "Space Member", "space": space, "user": email}).insert()
	return invited


def invite_person(email: str, first_name: str | None, roles: list[str]) -> dict[str, Any]:
	roles = [role for role in dict.fromkeys(roles) if role not in ("Administrator", "Guest", "All")]
	missing = [role for role in roles if not frappe.db.exists("Role", role)]
	if missing:
		frappe.throw(_("No role named {0}.").format(", ".join(missing)))
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name or email.split("@")[0].replace(".", " ").title(),
				"send_welcome_email": 1,
			}
		).insert()
	# everyone may ask the assistant, and tailor their Home with it
	frappe.get_doc("User", email).add_roles(ASSISTANT_USER_ROLE, *roles)
	return {"email": email, "roles": roles}


def country_of(time_zone: str | None) -> str | None:
	if not time_zone:
		return None
	code = next((code for code, zones in pytz.country_timezones.items() if time_zone in zones), None)
	return frappe.db.get_value("Country", {"code": code.lower()}) if code else None


def default_templates() -> list[dict[str, Any]]:
	"""The Spaces any organization can start with."""
	return [
		{
			"name": "company",
			"title": "Company",
			"icon": "organization",
			"app": "frappe",
			"description": _("What everyone needs to know: announcements, and what is happening this week."),
			"widgets": [
				{
					"type": "queue",
					"title": _("Announcements"),
					"size": "l",
					"doctype": "Note",
					"filters": {"public": 1},
					"fields": ["modified"],
					"order_by": "modified desc",
					"home": 1,
				},
				{
					"type": "quick_entry",
					"title": _("Post an announcement"),
					"size": "s",
					"doctype": "Note",
					"fields": ["title", "content"],
					"defaults": {"public": 1},
				},
			],
		},
		{
			"name": "team",
			"title": "Team",
			"icon": "users",
			"app": "frappe",
			"description": _(
				"A place for a team to work together; the assistant fills it in from what the team does."
			),
			"widgets": [
				{
					"type": "note",
					"title": _("About this team"),
					"size": "xl",
					"text": _("Describe what this team does, and ask the assistant to set its Space up."),
				}
			],
		},
	]
