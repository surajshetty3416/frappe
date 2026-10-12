"""An endpoint that keeps a write under GET accepts only POST.

`InsightsIntegrationTestCase` watches every test for such an endpoint. These
tests pin what the watch reports. The watch sees only what the tests run, so a
new endpoint also has to be listed here before it may accept GET.
"""

import importlib
import pkgutil

import frappe
from frappe.tests import UnitTestCase

from frappe import analytics as insights
from frappe.analytics.decorators import insights_whitelist
from frappe.analytics.tests.base import InsightsIntegrationTestCase

# An endpoint here was never checked for writes. Take it off the list once it
# accepts only POST, or once it is read and found to keep no write under GET.
ENDPOINTS_ACCEPTING_GET = [
    "frappe.analytics.api.ai.lineage.describe_query",
    "frappe.analytics.api.ai.search.search_columns",
    "frappe.analytics.api.ai.search.search_content",
    "frappe.analytics.api.alerts.get_alerts",
    "frappe.analytics.api.authoring.download_chart_rows",
    "frappe.analytics.api.authoring.download_drill_rows",
    "frappe.analytics.api.authoring.get_chart_count",
    "frappe.analytics.api.authoring.get_chart_data",
    "frappe.analytics.api.authoring.get_drill_data",
    "frappe.analytics.api.authoring.get_drill_dimensions",
    "frappe.analytics.api.authoring.get_drill_rows_range",
    "frappe.analytics.api.authoring.get_drill_rows_values",
    "frappe.analytics.api.dashboards.get_dashboards",
    "frappe.analytics.api.data_sources.create_data_source",
    "frappe.analytics.api.data_sources.get_all_data_sources",
    "frappe.analytics.api.data_sources.get_data_source_table",
    "frappe.analytics.api.data_sources.get_data_source_table_columns",
    "frappe.analytics.api.data_sources.get_data_source_table_row_count",
    "frappe.analytics.api.data_sources.get_data_source_tables",
    "frappe.analytics.api.data_sources.get_data_sources_of_tables",
    "frappe.analytics.api.data_sources.get_schema",
    "frappe.analytics.api.data_sources.get_table_links",
    "frappe.analytics.api.data_sources.test_connection",
    "frappe.analytics.api.data_sources.update_table_links",
    "frappe.analytics.api.data_store.get_data_store_tables",
    "frappe.analytics.api.get_app_version",
    "frappe.analytics.api.get_doc",
    "frappe.analytics.api.get_file_data",
    "frappe.analytics.api.get_security_update",
    "frappe.analytics.api.get_site_info",
    "frappe.analytics.api.get_user_info",
    "frappe.analytics.api.maps.find_unresolved_regions",
    "frappe.analytics.api.maps.get_available_regions",
    "frappe.analytics.api.maps.save_region_mappings",
    "frappe.analytics.api.run_doc_method",
    "frappe.analytics.api.search.search_workbook_items",
    "frappe.analytics.api.translations.get_translations",
    "frappe.analytics.api.user.accept_invitation",
    "frappe.analytics.api.user.add_insights_user",
    "frappe.analytics.api.user.create_team",
    "frappe.analytics.api.user.delete_team",
    "frappe.analytics.api.user.get_roles",
    "frappe.analytics.api.user.get_teams",
    "frappe.analytics.api.user.get_users",
    "frappe.analytics.api.user.update_team",
    "frappe.analytics.api.user.update_user",
    "frappe.analytics.api.view.download_chart_rows",
    "frappe.analytics.api.view.download_drill_rows",
    "frappe.analytics.api.view.get_card_range",
    "frappe.analytics.api.view.get_card_values",
    "frappe.analytics.api.view.get_chart",
    "frappe.analytics.api.view.get_chart_count",
    "frappe.analytics.api.view.get_chart_data",
    "frappe.analytics.api.view.get_dashboard",
    "frappe.analytics.api.view.get_drill_data",
    "frappe.analytics.api.view.get_drill_rows_range",
    "frappe.analytics.api.view.get_drill_rows_values",
    "frappe.analytics.api.view.get_filter_range",
    "frappe.analytics.api.view.get_filter_values",
    "frappe.analytics.api.workbooks.create_folder",
    "frappe.analytics.api.workbooks.delete_folder",
    "frappe.analytics.api.workbooks.get_export_modules",
    "frappe.analytics.api.workbooks.get_share_permissions",
    "frappe.analytics.api.workbooks.get_workbooks",
    "frappe.analytics.api.workbooks.import_workbook",
    "frappe.analytics.api.workbooks.is_workbook_file",
    "frappe.analytics.api.workbooks.move_item_to_folder",
    "frappe.analytics.api.workbooks.rename_folder",
    "frappe.analytics.api.workbooks.toggle_folder_expanded",
    "frappe.analytics.api.workbooks.update_share_permissions",
    "frappe.analytics.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.duplicate",
    "frappe.analytics.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.export",
    "frappe.analytics.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.published_reach",
    "frappe.analytics.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_distinct_column_values",
    "frappe.analytics.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_filter_column_range",
    "frappe.analytics.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.track_view",
    "frappe.analytics.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.update_access",
    "frappe.analytics.doctype.insights_data_source_v3.ibis.utils.get_code_completions",
    "frappe.analytics.doctype.insights_data_source_v3.ibis.utils.get_function_description",
    "frappe.analytics.doctype.insights_data_source_v3.ibis.utils.get_function_list",
    "frappe.analytics.doctype.insights_data_source_v3.ibis.utils.validate_expression",
    "frappe.analytics.doctype.insights_data_source_v3.insights_data_source_v3.InsightsDataSourcev3.test_connection",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.download_results",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.duplicate",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.execute",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.export",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.format",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_column_range",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_columns_for_selection",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_count",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_distinct_column_values",
    "frappe.analytics.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.profile_column",
    "frappe.analytics.doctype.insights_settings.insights_settings.InsightsSettings.update_settings",
    "frappe.analytics.doctype.insights_table_import_log.insights_table_import_log.InsightsTableImportLog.mark_as_failed",
    "frappe.analytics.doctype.insights_table_v3.insights_table_v3.InsightsTablev3.get_stats",
    "frappe.analytics.doctype.insights_user_invitation.insights_user_invitation.InsightsUserInvitation.accept_invitation",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.duplicate",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.export",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.get_lineage_graph",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_chart",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_query",
    "frappe.analytics.doctype.insights_workbook.insights_workbook.InsightsWorkbook.track_view",
    "frappe.analytics.setup.setup_wizard.check_demo_data_exists",
]


def get_endpoints_accepting_get():
    for module in pkgutil.walk_packages(insights.__path__, "frappe.analytics."):
        name = module.name
        if not name.startswith("frappe.analytics.tests.") and ".test_" not in name and not name.endswith("__main__"):
            importlib.import_module(name)

    return sorted(
        {
            f"{fn.__module__}.{fn.__qualname__}"
            for fn, methods in frappe.allowed_http_methods_for_whitelisted_func.items()
            if fn.__module__.startswith("frappe.analytics.")
            and not fn.__module__.startswith("frappe.analytics.tests.")
            and "GET" in methods
        }
    )


class EndpointsAcceptingGetAreListed(UnitTestCase):
    maxDiff = None

    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_accepts_get_only_when_listed(self):
        self.assertEqual(
            get_endpoints_accepting_get(),
            ENDPOINTS_ACCEPTING_GET,
            "Pass methods=['POST'] to a new endpoint's whitelist decorator.",
        )


class GetWritesAreReported(InsightsIntegrationTestCase):
    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_commits_under_get_is_reported(self):
        @insights_whitelist()
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        with self.assertRaisesRegex(AssertionError, "save_title commits but accepts GET"):
            self.assert_no_get_writes()

    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_accepts_only_post_may_commit(self):
        @insights_whitelist(methods=["POST"])
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        self.assert_no_get_writes()
