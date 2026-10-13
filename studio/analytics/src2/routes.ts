import type { RouteRecordRaw } from 'vue-router'

// Children of the layer's path (`/studio/analytics`), so every path here is relative.
// A person opens two artifacts here, a dashboard and a chart. The shell lists them.
export const routes: RouteRecordRaw[] = [
	{
		path: '',
		name: 'InsightsHome',
		redirect: '/studio',
	},
	{
		props: true,
		name: 'Dashboard',
		path: 'dashboards/:name',
		component: () => import('./dashboard/Dashboard.vue'),
		meta: { artifact: { doctype: 'Insights Dashboard v3', param: 'name' } },
	},
	{
		props: true,
		name: 'Chart',
		path: 'charts/:name',
		component: () => import('./charts/ChartPreview.vue'),
		meta: { artifact: { doctype: 'Insights Chart v3', param: 'name' } },
	},
	{
		props: true,
		name: 'SharedDashboard',
		path: 'shared/dashboard/:dashboard_name',
		component: () => import('./dashboard/SharedDashboard.vue'),
		meta: { guest: true, hideRail: true },
	},
	{
		path: ':pathMatch(.*)*',
		name: 'InsightsNotFound',
		component: () => import('./auth/NotFound.vue'),
	},
]
