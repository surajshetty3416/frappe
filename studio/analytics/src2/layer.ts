import { defineLayer } from '@shell/layer'
import { APP_PATH } from './app_path'
import { routes } from './routes'

export default defineLayer({
	name: 'analytics',
	title: 'Dashboards',
	icon: 'lucide-chart-column',
	path: APP_PATH,
	component: () => import('./App.vue'),
	routes,
	setup: async (app) => (await import('./main')).default(app),
	beforeEnter: async () => {
		const { default: session } = await import('./session')
		await session.initialize()
	},
})
