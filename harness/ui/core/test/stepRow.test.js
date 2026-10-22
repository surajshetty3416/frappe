import assert from "node:assert/strict"
import test from "node:test"

import { createSSRApp, h } from "vue"
import { renderToString } from "vue/server-renderer"

import StepRow from "../src/components/StepRow.js"

function render(button) {
	const app = createSSRApp({ render: () => h(StepRow, { button, class: "row" }, () => "Reading Workspace") })
	app.component("Button", { render: () => h("span", "the host's Button") })
	return renderToString(app)
}

test("a step's row is a native button even where the host registers a Button component", async () => {
	assert.equal(await render(true), '<button class="row">Reading Workspace</button>')
	assert.equal(await render(false), '<div class="row">Reading Workspace</div>')
})
