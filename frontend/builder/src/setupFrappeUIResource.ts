// Placed in separate file to setup frappe resource fetcher before loading the app.
import { frappeRequest, setConfig } from "frappe-ui";
import { editorDemo } from "@builder/utils/editorDemo";
import { createEditorDemoBackend } from "@builder/utils/editorDemoBackend";

setConfig("resourceFetcher", editorDemo ? createEditorDemoBackend(editorDemo) : frappeRequest);
