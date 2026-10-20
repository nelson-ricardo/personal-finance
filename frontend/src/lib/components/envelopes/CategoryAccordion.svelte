<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		category,
		onaddenvelope,
		oneditcategory,
		children
	}: {
		category: EnvelopeCategoryWithEnvelopes;
		onaddenvelope: (categoryName: string) => void;
		oneditcategory: (category: EnvelopeCategoryWithEnvelopes) => void;
		children?: Snippet;
	} = $props();

	let isOpen = $state(true);

	const totalBalance = $derived(parseFloat(category.total_balance) || 0);
	const isNegative = $derived(totalBalance < 0);
</script>

<div
	class="bg-white rounded-2xl border border-brand-200/90 shadow-2xs overflow-hidden transition-all duration-150"
>
	<!-- Category Header Bar (Entire bar is clickable to toggle) -->
	<div
		role="button"
		tabindex="0"
		onclick={() => (isOpen = !isOpen)}
		onkeydown={(e) => {
			if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
				e.preventDefault();
				isOpen = !isOpen;
			}
		}}
		class="px-4 py-3.5 sm:px-5 sm:py-4 bg-brand-50/60 hover:bg-brand-100/60 flex items-center justify-between gap-3 border-b border-brand-100 cursor-pointer select-none transition-colors group"
		aria-expanded={isOpen}
	>
		<div class="flex items-center gap-2.5 sm:gap-3 text-left min-w-0">
			<svg
				class="w-4 h-4 text-brand-500 transition-transform duration-200 shrink-0 group-hover:text-brand-800 {isOpen
					? 'rotate-90'
					: ''}"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
			</svg>

			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans truncate">
						{category.name}
					</h2>
					<span
						class="text-[11px] font-mono text-brand-600 bg-brand-100 px-1.5 py-0.2 rounded-md shrink-0"
					>
						{category.envelopes.length}
					</span>
				</div>
			</div>
		</div>

		<div class="flex items-center gap-2 sm:gap-3 shrink-0">
			<!-- Total Category Balance -->
			<div class="text-right">
				<span
					class="font-mono font-bold text-sm sm:text-base tabular-nums {isNegative
						? 'text-[#6b1d2f]'
						: 'text-brand-900'}"
				>
					{formatCurrency(category.total_balance)}
				</span>
			</div>

			<!-- Category Quick Actions (stop propagation so clicking actions does not toggle accordion) -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="flex items-center gap-1 border-l border-brand-200 pl-2 sm:pl-3"
				onclick={(e) => e.stopPropagation()}
			>
				<button
					type="button"
					onclick={() => onaddenvelope(category.name)}
					class="p-1.5 text-brand-500 hover:text-brand-900 hover:bg-brand-200/80 rounded-lg transition-colors cursor-pointer"
					title="Add envelope to {category.name}"
					aria-label="Add envelope to {category.name}"
				>
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2.5"
							d="M12 4v16m8-8H4"
						/>
					</svg>
				</button>

				<button
					type="button"
					onclick={() => oneditcategory(category)}
					class="p-1.5 text-brand-500 hover:text-brand-900 hover:bg-brand-200/80 rounded-lg transition-colors cursor-pointer"
					title="Edit category {category.name}"
					aria-label="Edit category {category.name}"
				>
					<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
						/>
					</svg>
				</button>
			</div>
		</div>
	</div>

	<!-- Children / Envelopes Content -->
	{#if isOpen}
		<div class="divide-y divide-brand-100">
			{#if category.envelopes.length === 0}
				<div class="px-5 py-6 text-center text-xs text-brand-500">
					No envelopes in this category yet.
					<button
						type="button"
						onclick={() => onaddenvelope(category.name)}
						class="text-brand-700 underline font-semibold ml-1 cursor-pointer hover:text-brand-900"
					>
						Create one now
					</button>
				</div>
			{:else}
				{@render children?.()}
			{/if}
		</div>
	{/if}
</div>
