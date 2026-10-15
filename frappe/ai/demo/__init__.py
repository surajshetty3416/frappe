"""The Frappeverse demo: seven recorded chats that build a conference on Studio, one per layer."""

import json
import time
from pathlib import Path
from typing import Any

import frappe
from frappe.ai.replay import get_replay, import_recording, list_recordings, play_step, start_replay

RECORDINGS = Path(__file__).parent / "frappeverse"
SPEED = 50
PROJECT = "Frappeverse 2027"
PROJECT_CONTEXT = """Frappeverse 2027 is Frappe's yearly conference, on 20 and 21 August 2027 at Nehru Centre, Worli, Mumbai.
Its DocTypes live in the Frappeverse module. Amounts are in INR and times in Asia/Kolkata."""


def setup_site() -> None:
	"""What the setup wizard would have set: India, INR and Asia/Kolkata, a person for
	Administrator, and outgoing mail to a local SMTP receiver on port 1025."""
	currency = frappe.get_doc("Currency", "INR")
	currency.update({"enabled": 1, "symbol": currency.symbol or "₹"})
	currency.save()
	settings = frappe.get_single("System Settings")
	settings.update(
		{"country": "India", "currency": "INR", "time_zone": "Asia/Kolkata", "language": settings.language or "en"}
	)
	settings.save()
	for key in ("country", "currency", "time_zone"):
		frappe.db.set_default(key, settings.get(key))
	frappe.db.set_value(
		"User",
		"Administrator",
		{"first_name": "Aditi", "last_name": "Rao", "full_name": "Aditi Rao", "email": "aditi@frappeverse.in"},
	)
	if not frappe.db.exists("Email Account", "Frappeverse"):
		frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": "Frappeverse",
				"email_id": "hello@frappeverse.test",
				"service": "",
				"smtp_server": "127.0.0.1",
				"smtp_port": 1025,
				"use_tls": 0,
				"use_ssl_for_outgoing": 0,
				"no_smtp_authentication": 1,
				"enable_outgoing": 1,
				"default_outgoing": 1,
				"enable_incoming": 0,
			}
		).insert()
	frappe.db.commit()


def import_recordings() -> None:
	"""The demo's recordings, in layer order, each once."""
	for path in sorted(RECORDINGS.glob("*.json")):
		data = json.loads(path.read_text())
		if not frappe.db.exists("Flow Recording", {"title": data["title"]}):
			import_recording(data)
	frappe.db.commit()


def project() -> str:
	"""The demo's project, which its recorded chats replay into."""
	name = frappe.db.get_value("Studio Project", {"title": PROJECT})
	if not name:
		name = frappe.get_doc(
			{
				"doctype": "Studio Project",
				"title": PROJECT,
				"description": "Everything for the conference: data, apps, website, dashboards, badges, emails and agents.",
				"context": PROJECT_CONTEXT,
			}
		).insert().name
		frappe.db.commit()
	return name


def unplayed() -> list[dict[str, Any]]:
	"""Recordings no chat has replayed: a second replay makes the same artifacts again and fails."""
	played = set(frappe.get_all("Flow Replay", pluck="recording"))
	return [r for r in list_recordings() if r.name not in played]


def play(recording: str, project: str | None = None) -> dict[str, Any]:
	"""Replay a recording into a new chat in `project`, step by step, until it ends."""
	session = start_replay(recording, project)["session"]
	while True:
		state = play_step(session, SPEED)
		while state["status"] == "Playing":
			time.sleep(0.3)
			frappe.db.commit()  # a new snapshot, which sees what the flow server's callbacks wrote
			state = get_replay(session)
		if state["status"] != "Ready":
			return state
