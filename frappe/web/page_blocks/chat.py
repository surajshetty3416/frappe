"""The chat block: a site visitor's conversation with one public agent. Every conversation runs
as Guest, whoever is signed in, so the agent's tools read only what Guest may read. A visitor
cannot approve a tool call, so each call that asks is declined."""

import hashlib
import hmac
import re
from contextlib import contextmanager

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint
from frappe.utils.password import get_encryption_key

from frappe.web.page_blocks import esc, published_block

MESSAGE_LIMIT = 1000
TURN_LIMIT = 30
MEMORY = re.compile(r"\n<memory>\n[\s\S]*?\n</memory>$")
SEND_ICON = (
	'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" '
	'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>'
)


class ChatBlock:
	key = "chat"

	def __init__(self, config: dict):
		self.config = config
		agent = config.get("agent")
		self.agent = (
			frappe.db.get_value("Flow Agent", agent, ["name", "title", "enabled", "public"], as_dict=True)
			if agent
			else None
		)
		if not self.agent:
			frappe.throw(_("The chat's agent {0} does not exist.").format(agent))

	@classmethod
	def clean(cls, config: dict) -> dict:
		config = {
			"agent": config.get("agent"),
			"title": config.get("title") or "",
			"greeting": config.get("greeting") or "",
			"placeholder": config.get("placeholder") or "",
		}
		block = cls(config)
		if not block.agent.public:
			frappe.throw(
				_("Flow Agent {0} is not public. Make it public before a page offers it.").format(
					block.agent.name
				)
			)
		return config

	def render(self, block_id: str) -> str:
		title = self.config.get("title") or self.agent.title
		greeting = self.config.get("greeting")
		placeholder = self.config.get("placeholder") or _("Ask a question")
		first = f'<div class="fb-chat-msg fb-chat-agent"><p>{esc(greeting)}</p></div>' if greeting else ""
		return (
			f'<div class="fb-chat" data-fb-chat data-page="{{{{ page_name }}}}" data-block="{esc(block_id)}">'
			f'<div class="fb-chat-header"><span class="fb-chat-title">{esc(title)}</span></div>'
			f'<div class="fb-chat-log" aria-live="polite">{first}'
			'<div class="fb-chat-typing" hidden><span></span><span></span><span></span></div></div>'
			'<form class="fb-chat-composer">'
			f'<textarea class="fb-chat-input" rows="1" maxlength="{MESSAGE_LIMIT}" placeholder="{esc(placeholder)}" '
			f'aria-label="{esc(placeholder)}"></textarea>'
			f'<button class="fb-chat-send" type="submit" disabled aria-label="{esc(_("Send"))}">{SEND_ICON}</button>'
			"</form></div>"
		)


@contextmanager
def as_guest():
	"""Run as Guest inside the request, then restore the caller's session untouched."""
	local = frappe.local
	saved = local.session, local.form_dict
	local.session = frappe._dict(saved[0])
	frappe.set_user("Guest")
	try:
		yield
	finally:
		local.session, local.form_dict = saved
		local.user_perms = None
		local.role_permissions = {}
		local.cache = {}


def session_token(session: str) -> str:
	return hmac.new(
		get_encryption_key().encode(), f"chat-block:{session}".encode(), hashlib.sha256
	).hexdigest()


def visitor_session(session: str, token: str, agent: str):
	"""The visitor's own Flow Session, proven by the token the block was given for it."""
	if not (session and token and hmac.compare_digest(session_token(session), str(token))):
		raise frappe.PermissionError(_("This conversation has ended. Reload the page to start a new one."))
	doc = frappe.get_doc("Flow Session", session)
	if doc.agent != agent or doc.owner != "Guest":
		raise frappe.PermissionError(_("This conversation has ended. Reload the page to start a new one."))
	return doc


def message_text(message: str) -> str:
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Write a message first."))
	if len(message) > MESSAGE_LIMIT:
		frappe.throw(_("Keep a message under {0} characters.").format(MESSAGE_LIMIT))
	return message


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=10 * 60)
def send(page: str, block: str, message: str, session: str | None = None, token: str | None = None) -> dict:
	"""Start a turn in the visitor's conversation, or start the conversation."""
	from frappe.ai.lib.session import new_session

	row, config = published_block(page, block, ChatBlock.key)
	message = message_text(message)
	with as_guest():
		if session:
			doc = visitor_session(session, token, config["agent"])
			if frappe.db.count("Flow Run", {"session": doc.name}) >= TURN_LIMIT:
				frappe.throw(_("This conversation is at its limit. Reload the page to start a new one."))
		else:
			doc = new_session(config["agent"], title=_("Visitor on {0}").format(row.name))
		doc.chat(message)
	return {"session": doc.name, "token": session_token(doc.name)}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=900, seconds=10 * 60)
def poll(page: str, block: str, session: str, token: str, since: int | str = 0) -> dict:
	"""The conversation's messages after `since`, and whether the agent is still answering."""
	from frappe.ai.lib.session import flow_server

	_row, config = published_block(page, block, ChatBlock.key)
	with as_guest():
		doc = visitor_session(session, token, config["agent"])
		with flow_server() as client:
			state = client.get_session(doc.name)["state"]
			rows = client.entries(doc.name, since=cint(since), path="all")["entries"]
		if state == "paused":
			decline_approvals(doc)
	return {
		"messages": [message for row in rows if (message := visitor_message(row))],
		"seq": rows[-1]["seq"] if rows else cint(since),
		"running": state != "idle",
	}


def decline_approvals(doc) -> None:
	rows = doc.entries(path="active")["entries"]
	pending = next((row for row in reversed(rows) if row["type"] == "approval_required"), None)
	if pending:
		doc.resume({call["id"]: "Deny" for call in pending["calls"]})


def visitor_message(row: dict) -> dict | None:
	if row.get("subagent_id"):
		return None
	if row["type"] == "user_message":
		return {"role": "visitor", "text": MEMORY.sub("", text_of(row["content"]))}
	if row["type"] == "assistant_message" and (text := text_of(row["content"]).strip()):
		return {"role": "agent", "text": text}
	if row["type"] == "run_error":
		return {"role": "error", "text": _("Something went wrong. Try again.")}
	return None


def text_of(content) -> str:
	if isinstance(content, str):
		return content
	return "".join(block.get("text", "") for block in content if block.get("type") == "text")
