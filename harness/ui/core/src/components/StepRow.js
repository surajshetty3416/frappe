import { h } from "vue"

// A step's row: a native button when the step opens, else a div. h() makes the element itself, where
// <component :is="'button'"> resolves to a Button component the host app registered globally.
export default function StepRow(props, { slots }) {
	return h(props.button ? "button" : "div", null, slots.default?.())
}

StepRow.props = { button: Boolean }
