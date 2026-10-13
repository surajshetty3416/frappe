import type Block from "@web/block";

export function findBlockInTree(blockId: string, blocks: Block[]): Block | null {
	for (const block of blocks) {
		if (block.blockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findBlockInTree(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
}
