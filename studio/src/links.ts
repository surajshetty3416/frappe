import type { Router } from "vue-router"

const isPlainClick = (event: MouseEvent) =>
	!event.defaultPrevented &&
	event.button === 0 &&
	!(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)

// Links in rendered content (a chat answer, a dashboard description) are plain anchors.
// A link into any layer opens in place instead of reloading the whole app.
export function keepLayerLinksInApp(router: Router) {
	document.addEventListener("click", (event) => {
		if (!isPlainClick(event) || !(event.target instanceof Element)) return
		const anchor = event.target.closest("a[href]")
		if (!(anchor instanceof HTMLAnchorElement) || anchor.download) return
		if (anchor.target && anchor.target !== "_self") return
		const url = new URL(anchor.href, window.location.href)
		if (url.origin !== window.location.origin) return
		const route = router.resolve(url.pathname + url.search + url.hash)
		if (!route.matched[0]?.meta.layer) return
		event.preventDefault()
		router.push(route)
	})
}
