"""An endpoint that keeps a write under GET accepts only POST.

`InsightsIntegrationTestCase` watches every test for such an endpoint. These
tests pin what the watch reports. The watch sees only what the tests run, so a
new endpoint also has to be listed here before it may accept GET.
"""

import importlib
import pkgutil

import frappe
from frappe.tests import UnitTestCase

from frappe import insights
from frappe.insights.decorators import insights_whitelist
from frappe.insights.tests.base import InsightsIntegrationTestCase

# An endpoint here was never checked for writes. Take it off the list once it
# accepts only POST, or once it is read and found to keep no write under GET.
ENDPOINTS_ACCEPTING_GET = [
    "frappe.insights.api.ai.lineage.describe_query",
    "frappe.insights.api.ai.search.search_columns",
    "frappe.insights.api.ai.search.search_content",
    "frappe.insights.api.alerts.get_alerts",
    "frappe.insights.api.authoring.download_chart_rows",
    "frappe.insights.api.authoring.download_drill_rows",
    "frappe.insights.api.authoring.get_chart_count",
    "frappe.insights.api.authoring.get_chart_data",
    "frappe.insights.api.authoring.get_drill_data",
    "frappe.insights.api.authoring.get_drill_dimensions",
    "frappe.insights.api.authoring.get_drill_rows_range",
    "frappe.insights.api.authoring.get_drill_rows_values",
    "frappe.insights.api.dashboards.get_dashboards",
    "frappe.insights.api.data_sources.create_data_source",
    "frappe.insights.api.data_sources.get_all_data_sources",
    "frappe.insights.api.data_sources.get_data_source_table",
    "frappe.insights.api.data_sources.get_data_source_table_columns",
    "frappe.insights.api.data_sources.get_data_source_table_row_count",
    "frappe.insights.api.data_sources.get_data_source_tables",
    "frappe.insights.api.data_sources.get_data_sources_of_tables",
    "frappe.insights.api.data_sources.get_schema",
    "frappe.insights.api.data_sources.get_table_links",
    "frappe.insights.api.data_sources.test_connection",
    "frappe.insights.api.data_sources.update_table_links",
    "frappe.insights.api.data_store.get_data_store_tables",
    "frappe.insights.api.get_app_version",
    "frappe.insights.api.get_doc",
    "frappe.insights.api.get_file_data",
    "frappe.insights.api.get_security_update",
    "frappe.insights.api.get_site_info",
    "frappe.insights.api.get_user_info",
    "frappe.insights.api.maps.find_unresolved_regions",
    "frappe.insights.api.maps.get_available_regions",
    "frappe.insights.api.maps.save_region_mappings",
    "frappe.insights.api.run_doc_method",
    "frappe.insights.api.search.search_workbook_items",
    "frappe.insights.api.translations.get_translations",
    "frappe.insights.api.user.accept_invitation",
    "frappe.insights.api.user.add_insights_user",
    "frappe.insights.api.user.create_team",
    "frappe.insights.api.user.delete_team",
    "frappe.insights.api.user.get_roles",
    "frappe.insights.api.user.get_teams",
    "frappe.insights.api.user.get_users",
    "frappe.insights.api.user.update_team",
    "frappe.insights.api.user.update_user",
    "frappe.insights.api.view.download_chart_rows",
    "frappe.insights.api.view.download_drill_rows",
    "frappe.insights.api.view.get_card_range",
    "frappe.insights.api.view.get_card_values",
    "frappe.insights.api.view.get_chart",
    "frappe.insights.api.view.get_chart_count",
    "frappe.insights.api.view.get_chart_data",
    "frappe.insights.api.view.get_dashboard",
    "frappe.insights.api.view.get_drill_data",
    "frappe.insights.api.view.get_drill_rows_range",
    "frappe.insights.api.view.get_drill_rows_values",
    "frappe.insights.api.view.get_filter_range",
    "frappe.insights.api.view.get_filter_values",
    "frappe.insights.api.workbooks.create_folder",
    "frappe.insights.api.workbooks.delete_folder",
    "frappe.insights.api.workbooks.get_export_modules",
    "frappe.insights.api.workbooks.get_share_permissions",
    "frappe.insights.api.workbooks.get_workbooks",
    "frappe.insights.api.workbooks.import_workbook",
    "frappe.insights.api.workbooks.is_workbook_file",
    "frappe.insights.api.workbooks.move_item_to_folder",
    "frappe.insights.api.workbooks.rename_folder",
    "frappe.insights.api.workbooks.toggle_folder_expanded",
    "frappe.insights.api.workbooks.update_share_permissions",
    "frappe.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.duplicate",
    "frappe.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.export",
    "frappe.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.published_reach",
    "frappe.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_distinct_column_values",
    "frappe.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_filter_column_range",
    "frappe.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.track_view",
    "frappe.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.update_access",
    "frappe.insights.doctype.insights_data_source_v3.ibis.utils.get_code_completions",
    "frappe.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description",
    "frappe.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list",
    "frappe.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression",
    "frappe.insights.doctype.insights_data_source_v3.insights_data_source_v3.InsightsDataSourcev3.test_connection",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.download_results",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.duplicate",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.execute",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.export",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.format",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_column_range",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_columns_for_selection",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_count",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_distinct_column_values",
    "frappe.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.profile_column",
    "frappe.insights.doctype.insights_settings.insights_settings.InsightsSettings.update_settings",
    "frappe.insights.doctype.insights_table_import_log.insights_table_import_log.InsightsTableImportLog.mark_as_failed",
    "frappe.insights.doctype.insights_table_v3.insights_table_v3.InsightsTablev3.get_stats",
    "frappe.insights.doctype.insights_user_invitation.insights_user_invitation.InsightsUserInvitation.accept_invitation",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.duplicate",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.export",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.get_lineage_graph",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_chart",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_query",
    "frappe.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.track_view",
    "frappe.insights.setup.setup_wizard.check_demo_data_exists",
]


def get_endpoints_accepting_get():
    for module in pkgutil.walk_packages(insights.__path__, "frappe.insights."):
        name = module.name
        if not name.startswith("frappe.insights.tests.") and ".test_" not in name and not name.endswith("__main__"):
            importlib.import_module(name)

    return sorted(
        {
            f"{fn.__module__}.{fn.__qualname__}"
            for fn, methods in frappe.allowed_http_methods_for_whitelisted_func.items()
            if fn.__module__.startswith("frappe.insights.")
            and not fn.__module__.startswith("frappe.insights.tests.")
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
