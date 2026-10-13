import ai from "@ai/layer"
import analytics from "@analytics/layer"
import ui from "@ui/layer"
import web from "@web/layer"

import agents from "../agents/src/layer"
import data from "../data/src/layer"
import email from "../email/src/layer"
import print from "../print/src/layer"
import settings from "../settings/src/layer"

export const layers = [data, ui, web, analytics, print, email, agents, ai, settings]
