import type BuilderCanvas from "@web/components/BuilderCanvas.vue";
import { defineStore } from "pinia";

const useCanvasStore = defineStore("canvasStore", {
	state: () => ({
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
	}),
});

export default useCanvasStore;
