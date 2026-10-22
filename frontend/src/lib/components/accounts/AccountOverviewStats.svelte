<script lang="ts">
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		totalNetWorth = 0,
		netLiquid = 0,
		totalLiabilities = 0,
		totalInvestments = 0
	}: {
		totalNetWorth?: number;
		netLiquid?: number;
		totalLiabilities?: number;
		totalInvestments?: number;
	} = $props();
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
	<!-- Total Net Worth -->
	<div class="bg-white rounded-2xl border border-brand-200/80 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-semibold text-brand-500 tracking-tight">Total Net Worth</div>
		<div
			class="text-2xl sm:text-3xl font-mono font-bold tabular-nums {totalNetWorth < 0
				? 'text-[#6b1d2f]'
				: 'text-brand-950'}"
		>
			{formatCurrency(totalNetWorth)}
		</div>
	</div>

	<!-- Net Liquid Assets -->
	<div class="bg-white rounded-2xl border border-brand-200/80 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-semibold text-brand-500 tracking-tight">Net Liquid Assets</div>
		<div
			class="text-2xl sm:text-3xl font-mono font-bold tabular-nums {netLiquid < 0
				? 'text-[#6b1d2f]'
				: 'text-brand-900'}"
		>
			{formatCurrency(netLiquid)}
		</div>
	</div>

	<!-- Total Portfolio Investments -->
	<div class="bg-white rounded-2xl border border-brand-200/80 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-semibold text-brand-500 tracking-tight">Investments</div>
		<div class="text-2xl sm:text-3xl font-mono font-bold tabular-nums text-emerald-900">
			{formatCurrency(totalInvestments)}
		</div>
	</div>

	<!-- Total Outstanding Liabilities -->
	<div class="bg-white rounded-2xl border border-brand-200/80 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-semibold text-brand-500 tracking-tight">Total Outstanding Debt</div>
		<div
			class="text-2xl sm:text-3xl font-mono font-bold tabular-nums {totalLiabilities > 0
				? 'text-[#6b1d2f]'
				: 'text-brand-900'}"
		>
			{formatCurrency(totalLiabilities)}
		</div>
	</div>
</div>
