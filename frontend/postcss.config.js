import autoprefixer from "autoprefixer"
import tailwindcss from "tailwindcss"

import layerScope from "./build/layerScope.js"

export default {
	plugins: [tailwindcss(), layerScope(), autoprefixer()],
}
