import { chatsLevel } from "@web/components/ai/commands/chats";
import { modelLevel } from "@web/components/ai/commands/models";
import { providersLevel } from "@web/components/ai/commands/providers";
import type { BobContext } from "@web/components/ai/commands/shared";
import { slashCommands, type SlashCommand } from "@web/components/ai/slashCommands";

/** Bob's built-in "/" commands. Returns the unregister for when the chat panel unmounts. */
export function registerBobCommands(ctx: BobContext): () => void {
	const commands: SlashCommand[] = [
		{
			name: "model",
			description: "Switch model",
			icon: "lucide-cpu",
			submenu: true,
			run: (arg) => modelLevel(ctx, arg),
		},
		{
			name: "providers",
			submenu: true,
			aliases: ["credits", "connect", "setup"],
			description: "Connect providers, see credits",
			icon: "lucide-server",
			run: () => providersLevel(ctx),
		},
		{
			name: "chats",
			submenu: true,
			aliases: ["history", "resume"],
			description: "Chats on this page",
			icon: "lucide-history",
			run: () => chatsLevel(ctx),
		},
		{
			name: "new",
			aliases: ["clear"],
			description: "New chat",
			icon: "lucide-plus",
			run: () => ctx.chat.newSession(),
		},
	];
	const unregisters = commands.map((command) => slashCommands.register(command));
	return () => unregisters.forEach((unregister) => unregister());
}
