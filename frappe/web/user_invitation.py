from frappe.model.document import Document
from frappe.utils.telemetry import capture

from frappe.web.hooks import builder_path

# builder is a layer of the frappe app, so its invitations belong to that app
INVITATION_APP = "frappe"
INVITATION_PATH = f"/{builder_path}"


def is_builder_invitation(invitation: Document) -> bool:
	return invitation.app_name == INVITATION_APP and invitation.redirect_to_path == INVITATION_PATH


def capture_user_invited(doc: Document, method: str | None = None) -> None:
	if is_builder_invitation(doc):
		capture("builder_user_invited", "builder")


def after_accept(invitation: Document, user: Document, user_inserted: bool) -> None:
	if is_builder_invitation(invitation):
		capture("builder_user_invitation_accepted", "builder")
