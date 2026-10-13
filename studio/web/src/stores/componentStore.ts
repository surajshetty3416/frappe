import type Block from "@web/block";
import { useLatestRequest } from "@web/composables/useLatestRequest";
import { getVersionedDoc } from "@web/data/snapshot";
import { BuilderComponent } from "@web/types/doctypes";
import getBlockTemplate from "@web/utils/blockTemplate";
import { getBlockInstance } from "@web/utils/helpers";
import { createDocumentResource, createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { markRaw } from "vue";

export type ComponentDataStore = Record<string, Record<string, Record<string, any>>>;

const { run: runLatestRequest } = useLatestRequest();

const useComponentStore = defineStore("componentStore", {
	state: () => ({
		componentMap: <Map<string, Block>>new Map(),
		componentDocMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponent: new Set(),
		// frozen component versions, keyed by the version snapshot name (the pin)
		componentVersionMap: <Map<string, BuilderComponent>>new Map(),
		fetchingComponentVersion: new Set(),
		componentData: <ComponentDataStore>{},
	}),
	actions: {
		getComponentBlock(componentName: string) {
			return (
				(this.componentMap.get(componentName) as Block) ||
				getBlockInstance(getBlockTemplate("empty-component"))
			);
		},
		async loadComponent(componentName: string) {
			if (!this.componentMap.has(componentName) && !this.fetchingComponent.has(componentName)) {
				this.fetchingComponent.add(componentName);
				return this.fetchComponent(componentName)
					.then((componentDoc) => {
						this.setComponentMap(componentDoc);
					})
					.catch(() => {
						const missingComponentDoc = {
							name: componentName,
							block: JSON.stringify(getBlockTemplate("missing-component")),
							creation: "",
							modified: "",
							owner: "Administrator",
							modified_by: "Administrator",
						};
						this.setComponentMap(missingComponentDoc);
					})
					.finally(() => {
						this.fetchingComponent.delete(componentName);
					});
			}
		},
		setComponentMap(componentDoc: BuilderComponent) {
			this.componentDocMap.set(componentDoc.name, componentDoc);
			this.componentMap.set(componentDoc.name, markRaw(getBlockInstance(componentDoc.block)));
		},
		async fetchComponent(componentName: string) {
			const webComponentDoc = await createDocumentResource({
				doctype: "Builder Component",
				name: componentName,
				auto: true,
			});
			await webComponentDoc.get.promise;
			return webComponentDoc.doc as BuilderComponent;
		},
		getComponentVersionBlock(versionName: string) {
			const doc = this.componentVersionMap.get(versionName);
			return doc ? (markRaw(getBlockInstance(doc.block)) as Block) : null;
		},
		getComponentVersionDoc(versionName: string) {
			return this.componentVersionMap.get(versionName) ?? null;
		},
		async loadComponentVersion(versionName: string, componentId: string) {
			if (this.componentVersionMap.has(versionName) || this.fetchingComponentVersion.has(versionName)) {
				return;
			}
			this.fetchingComponentVersion.add(versionName);
			try {
				// fetch the component doc as it was at this version (versioned fields overlaid)
				const doc = await getVersionedDoc(versionName);
				if (doc?.block) {
					const versionedDoc = { ...doc } as BuilderComponent;
					this.componentVersionMap.set(versionName, versionedDoc);
				} else {
					// pruned/missing version — show the live component instead
					await this.loadComponent(componentId);
				}
			} finally {
				this.fetchingComponentVersion.delete(versionName);
			}
		},
		getComponent(componentName: string) {
			return this.componentDocMap.get(componentName) as BuilderComponent;
		},
		getComponentName(componentId: string, componentVersion?: string) {
			let componentObj = this.componentDocMap.get(componentId);
			if (!componentObj && componentVersion) {
				componentObj = this.componentVersionMap.get(componentVersion);
			}
			if (!componentObj) {
				return componentId;
			}
			return componentObj.component_name;
		},
		getComponentInstanceData(componentId: string, blockId: string) {
			const instanceKey = blockId;
			return this.componentData[componentId]?.[instanceKey] ?? {};
		},
		async setComponentData(
			componentId: string,
			props: Record<string, any> = {},
			blockId: string,
			componentVersion?: string,
		) {
			const instanceKey = blockId;
			const requestKey = `${componentId}::${instanceKey}`;
			// use the data script from the pinned version when available, else live component
			const versionedDoc = componentVersion
				? this.getComponentVersionDoc(componentVersion)
				: this.getComponent(componentId);
			const script = versionedDoc?.component_data_script ?? undefined;
			const result = await runLatestRequest(requestKey, () =>
				createResource({
					url: "frappe.web.api.get_component_data",
					method: "POST",
					auto: false,
				})
					.submit({
						component_name: componentId,
						props: JSON.stringify(props),
						script,
					})
					.then((data: { [key: string]: any }) => data ?? {})
					.catch((e: { message: string }) => {
						console.error("Failed to fetch component data:", e.message);
						return {};
					}),
			);
			if (result.stale) {
				return;
			}

			if (!this.componentData[componentId]) {
				this.componentData[componentId] = {};
			}
			this.componentData[componentId][instanceKey] = result.value;
		},
		async deleteComponentData(componentId: string, blockId: string) {
			const instanceKey = blockId;
			if (!this.componentData[componentId]) return;
			this.componentData[componentId][instanceKey] = {};
		},
	},
});

export default useComponentStore;
