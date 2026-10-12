# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt

from frappe.analytics.hooks import insights_path
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site


def get_boot() -> dict:
    return {
        "insights_path": f"/{insights_path}",
        "is_fc_site": is_fc_site(),
    }
