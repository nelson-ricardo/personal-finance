<script lang="ts">
	import type { Envelope } from '#lib/schemas/category.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		envelope,
		unassignedBalance = 0,
		onmove,
		onedit
	}: {
		envelope: Envelope;
		unassignedBalance: number;
		onmove: (envelope: Envelope, mode: 'assign' | 'return') => void;
		onedit: (envelope: Envelope) => void;
	} = $props();

	const balanceNum = $derived(parseFloat(envelope.balance) || 0);
	const isNegative = $derived(balanceNum < 0);
	const isPositive = $derived(balanceNum > 0);
	const isUnassigned = $derived(envelope.name === 'Unassigned');
</script>

<div
	class="px-4 py-3 sm:px-5 sm:py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-brand-50/40 transition-colors {!envelope.is_active
		? 'opacity-60 bg-slate-50/50'
		: ''}"
>
	<!-- Envelope Identification -->
	<div class="space-y-0.5 min-w-0">
		<div class="flex items-center gap-2 flex-wrap">
			<span class="font-bold text-sm text-brand-900 font-sans leading-snug break-words">
				{envelope.name}
			</span>

			{#if envelope.system_role === 'CREDIT_CARD_PAYMENT' || envelope.name === 'Credit Card Payment'}
				<span
					class="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200"
				>
					Credit Card
				</span>
			{:else if envelope.system_role}
				<span
					class="text-[10px] font-mono px-2 py-0.5 rounded-md bg-stone-100 text-stone-700 border border-stone-200"
				>
					System
				</span>
			{/if}

			{#if !envelope.is_active}
				<span
					class="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200"
				>
					Archived
				</span>
			{/if}
		</div>

		{#if envelope.note}
			<p class="text-xs text-brand-600 truncate max-w-md">
				{envelope.note}
			</p>
		{/if}
	</div>

	<!-- Balance & Actions -->
	<div
		class="flex items-center justify-between sm:justify-end gap-3 sm:gap-4 shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-brand-100"
	>
		<!-- Rolling Balance Badge -->
		<div
			class="px-2.5 py-1 rounded-lg font-mono text-sm font-bold tabular-nums {isNegative
				? 'bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20'
				: isPositive
					? 'bg-emerald-50 text-emerald-800 border border-emerald-200/80'
					: 'bg-slate-100 text-slate-700 border border-slate-200'}"
		>
			{formatCurrency(envelope.balance)}
		</div>

		<!-- Action Buttons -->
		<div class="flex items-center gap-1.5">
			<button
				type="button"
				onclick={() =>
					onmove(
						envelope,
						balanceNum < 0
							? 'assign'
							: balanceNum > 0 && unassignedBalance <= 0
								? 'return'
								: 'assign'
					)}
				disabled={isUnassigned}
				class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all {!isUnassigned
					? 'bg-brand-900 text-white hover:bg-brand-800 active:bg-brand-950 cursor-pointer shadow-2xs'
					: 'bg-brand-100 text-brand-400 cursor-not-allowed'}"
				title={!isUnassigned
					? 'Move money between this envelope and Ready to Assign'
					: 'System envelope'}
			>
				<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
					/>
				</svg>
				<span>Move</span>
			</button>

			<button
				type="button"
				onclick={() => onedit(envelope)}
				class="p-1.5 text-brand-500 hover:text-brand-900 hover:bg-brand-100 rounded-lg transition-colors cursor-pointer"
				title="Edit {envelope.name}"
				aria-label="Edit {envelope.name}"
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
