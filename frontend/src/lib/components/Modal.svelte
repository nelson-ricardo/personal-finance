<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = false,
		title,
		description,
		onclose,
		children
	}: {
		open: boolean;
		title?: string;
		description?: string;
		onclose?: () => void;
		children?: Snippet;
	} = $props();

	// Lock body scroll when modal is active; restore on close or unmount
	$effect(() => {
		if (!open) return;

		const originalOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';

		return () => {
			document.body.style.overflow = originalOverflow;
		};
	});
</script>

<svelte:window
	onkeydown={(e) => {
		if (open && e.key === 'Escape' && onclose) {
			onclose();
		}
	}}
/>

{#if open}
	<div
		class="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-brand-900/40 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4"
		onclick={(e) => {
			if (e.target === e.currentTarget && onclose) {
				onclose();
			}
		}}
		role="presentation"
	>
		<div
			class="bg-white rounded-2xl border border-brand-200 shadow-xl max-w-lg w-full max-h-[92vh] overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-5 animate-in fade-in zoom-in-95 duration-150"
			role="dialog"
			aria-modal="true"
			aria-labelledby={title ? 'modal-dialog-title' : undefined}
		>
			{#if title || onclose}
				<div class="flex items-center justify-between border-b border-brand-100 pb-3">
					<div>
						{#if title}
							<h2
								id="modal-dialog-title"
								class="text-lg sm:text-xl font-bold text-brand-900 font-sans"
							>
								{title}
							</h2>
						{/if}
						{#if description}
							<p class="text-xs text-brand-600">
								{description}
							</p>
						{/if}
					</div>
					{#if onclose}
						<button
							type="button"
							onclick={onclose}
							class="text-brand-400 hover:text-brand-700 p-1.5 rounded-lg transition-colors cursor-pointer"
							aria-label="Close modal"
						>
							✕
						</button>
					{/if}
				</div>
			{/if}

			{@render children?.()}
		</div>
	</div>
{/if}
