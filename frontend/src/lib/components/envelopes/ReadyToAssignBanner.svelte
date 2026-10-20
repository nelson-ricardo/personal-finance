<script lang="ts">
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		unassignedBalance = 0,
		onaddincome
	}: {
		unassignedBalance: number;
		onaddincome: () => void;
	} = $props();

	const isPositive = $derived(unassignedBalance > 0);
	const isNegative = $derived(unassignedBalance < 0);
</script>

<div
	class="relative overflow-hidden rounded-2xl border p-5 sm:p-6 transition-all duration-200 {isNegative
		? 'bg-[#6b1d2f]/5 border-[#6b1d2f]/30'
		: isPositive
			? 'bg-gradient-to-br from-emerald-50/80 via-white to-brand-50/40 border-emerald-200/80 shadow-2xs'
			: 'bg-white border-brand-200 shadow-2xs'}"
>
	<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
		<div class="space-y-1">
			<div class="flex items-center gap-2">
				<span
					class="w-2.5 h-2.5 rounded-full {isNegative
						? 'bg-[#6b1d2f] animate-pulse'
						: isPositive
							? 'bg-emerald-500'
							: 'bg-slate-400'}"
				></span>
				<span
					class="text-xs font-bold uppercase tracking-wider font-mono {isNegative
						? 'text-[#6b1d2f]'
						: isPositive
							? 'text-emerald-800'
							: 'text-brand-600'}"
				>
					{isNegative ? 'Overallocated Deficit' : 'Ready to Assign'}
				</span>
			</div>

			<div
				class="text-3xl sm:text-4xl font-mono font-extrabold tabular-nums tracking-tight {isNegative
					? 'text-[#6b1d2f]'
					: isPositive
						? 'text-emerald-950'
						: 'text-brand-900'}"
			>
				{formatCurrency(unassignedBalance)}
			</div>

			<p class="text-xs sm:text-sm text-brand-600 max-w-md">
				{#if isPositive}
					Unassigned cash waiting to be allocated into your budgeting envelopes.
				{:else if isNegative}
					You have assigned more money than available in liquid cash. Reduce allocations to balance.
				{:else}
					All available cash is assigned. Practice zero-based stewardship by assigning incoming
					income.
				{/if}
			</p>
		</div>

		<button
			type="button"
			onclick={onaddincome}
			class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 active:bg-brand-700 transition-colors shadow-xs cursor-pointer self-start sm:self-auto shrink-0"
		>
			<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2.5"
					d="M12 4v16m8-8H4"
				/>
			</svg>
			<span>Add Income</span>
		</button>
	</div>
</div>
