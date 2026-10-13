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
		component: () => import('./dashboard/editor').then((editor) => editor.default.preview),
		meta: {
			artifact: {
				doctype: 'Insights Dashboard v3',
				param: 'name',
				editor: () => import('./dashboard/editor'),
			},
		},
	},
	{
		props: true,
		name: 'Chart',
		path: 'charts/:name',
		component: () => import('./charts/editor').then((editor) => editor.default.preview),
		meta: {
			artifact: {
				doctype: 'Insights Chart v3',
				param: 'name',
				editor: () => import('./charts/editor'),
			},
		},
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
