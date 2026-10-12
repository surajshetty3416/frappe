import type { RouteRecordRaw } from 'vue-router'

// Children of the layer's path (`/studio/analytics`), so every path here is relative.
export const routes: RouteRecordRaw[] = [
	{
		path: '',
		name: 'InsightsHome',
		redirect: { name: 'DashboardList' },
	},
	{
		path: 'dashboards',
		name: 'DashboardList',
		component: () => import('./dashboard/DashboardList.vue'),
	},
	{
		props: true,
		name: 'Dashboard',
		path: 'dashboards/:name',
		component: () => import('./dashboard/Dashboard.vue'),
		// opens beside Studio's chat, so the breadcrumbs lead back instead of the sidebar
		meta: {
			hideSidebar: true,
			artifact: { doctype: 'Insights Dashboard v3', param: 'name' },
		},
	},
	{
		path: 'workbook',
		name: 'WorkbookList',
		component: () => import('./workbook/WorkbookList.vue'),
	},
	{
		props: true,
		name: 'Workbook',
		path: 'workbook/:workbook_name',
		component: () => import('./workbook/Workbook.vue'),
		meta: {
			hideSidebar: true,
			artifact: { doctype: 'Insights Workbook', param: 'workbook_name' },
		},
		children: [
			{
				props: true,
				path: 'query/:query_name',
				name: 'WorkbookQuery',
				component: () => import('./workbook/WorkbookQuery.vue'),
			},
			{
				props: true,
				path: 'chart/:chart_name',
				name: 'WorkbookChart',
				component: () => import('./workbook/WorkbookChart.vue'),
			},
			{
				props: true,
				path: 'dashboard/:dashboard_name',
				name: 'WorkbookDashboard',
				component: () => import('./workbook/WorkbookDashboard.vue'),
			},
		],
	},
	{
		path: 'data-source',
		name: 'DataSourceList',
		component: () => import('./data_source/DataSourceList.vue'),
	},
	{
		props: true,
		path: 'data-source/:name',
		name: 'DataSourceTableList',
		component: () => import('./data_source/DataSourceTableList.vue'),
	},
	{
		props: true,
		path: 'data-source/:data_source/:table_name',
		name: 'DataSourceTable',
		component: () => import('./data_source/DataSourceTable.vue'),
	},
	{
		path: 'data-store',
		name: 'DataStoreList',
		component: () => import('./data_store/DataStoreList.vue'),
	},
	{
		props: true,
		name: 'SharedChart',
		path: 'shared/chart/:chart_name',
		component: () => import('./charts/SharedChart.vue'),
		meta: { guest: true, hideRail: true, hideSidebar: true },
	},
	{
		props: true,
		name: 'SharedDashboard',
		path: 'shared/dashboard/:dashboard_name',
		component: () => import('./dashboard/SharedDashboard.vue'),
		meta: { guest: true, hideRail: true, hideSidebar: true },
	},
	{
		path: ':pathMatch(.*)*',
		name: 'InsightsNotFound',
		component: () => import('./auth/NotFound.vue'),
		meta: { hideSidebar: true },
	},
]
