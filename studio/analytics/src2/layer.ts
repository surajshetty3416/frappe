import { defineLayer } from '@shell/layer'
import { APP_PATH } from './app_path'
import { routes } from './routes'

// The shell compiles its classes from this file, not from the editors, and draws the
// icons the editors name: lucide-hash lucide-chart-column lucide-chart-bar lucide-chart-line
// lucide-chart-pie lucide-filter lucide-table lucide-map lucide-list-filter lucide-type
// lucide-palette lucide-arrow-up-down
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
