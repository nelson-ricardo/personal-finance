<script lang="ts">
	import type { Account } from '#lib/schemas/account.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		totalBalance,
		totalLiabilities,
		accounts
	}: {
		totalBalance: number;
		totalLiabilities: number;
		accounts: Account[];
	} = $props();

	const cashCount = $derived(accounts.filter((a) => a.account_type === 'cash').length);
	const creditCount = $derived(accounts.filter((a) => a.account_type === 'credit_card').length);
	const loanCount = $derived(accounts.filter((a) => a.account_type === 'loan').length);
</script>

<div class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
	<!-- Net Estimated Position -->
	<div class="bg-white rounded-xl border border-brand-200 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-medium text-brand-600">Net Account Position</div>
		<div class="text-xl sm:text-2xl font-mono font-bold tabular-nums text-brand-900">
			{formatCurrency(totalBalance)}
		</div>
		<div class="text-[11px] text-brand-500 font-sans">
			Cash balances minus outstanding liabilities
		</div>
	</div>

	<!-- Total Liabilities -->
	<div class="bg-white rounded-xl border border-brand-200 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-medium text-brand-600">Total Outstanding Debt</div>
		<div class="text-xl sm:text-2xl font-mono font-bold tabular-nums text-brand-900">
			{formatCurrency(totalLiabilities)}
		</div>
		<div class="text-[11px] text-brand-500 font-sans">Combined credit cards & loan balances</div>
	</div>

	<!-- Active Accounts Count -->
	<div class="bg-white rounded-xl border border-brand-200 p-4 sm:p-5 shadow-2xs space-y-1">
		<div class="text-xs font-medium text-brand-600">Connected Accounts</div>
		<div class="text-xl sm:text-2xl font-mono font-bold tabular-nums text-brand-900">
			{accounts.length}
		</div>
		<div class="text-[11px] text-brand-500 font-sans">
			{cashCount} Cash, {creditCount} Credit, {loanCount} Loan
		</div>
	</div>
</div>
