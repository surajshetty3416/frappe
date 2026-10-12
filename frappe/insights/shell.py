# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt

from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site

from frappe.insights.hooks import insights_path


def get_boot() -> dict:
    return {
        "insights_path": f"/{insights_path}",
        "is_fc_site": is_fc_site(),
    }
