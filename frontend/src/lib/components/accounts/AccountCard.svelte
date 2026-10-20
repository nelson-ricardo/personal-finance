<script lang="ts">
	import type { Account } from '#lib/schemas/account.ts';
	import { formatCurrency, getOrdinalSuffix } from '#lib/utils/formatters.ts';

	let {
		account,
		onedit
	}: {
		account: Account;
		onedit?: (account: Account) => void;
	} = $props();
</script>

<div
	class="bg-white rounded-2xl border border-brand-200/90 p-4 sm:p-5 shadow-2xs hover:shadow-sm transition-all duration-150 flex flex-col justify-between space-y-3.5 sm:space-y-4"
>
	<!-- Card Header (Responsive Flex) -->
	<div class="flex flex-col xs:flex-row xs:items-start justify-between gap-3">
		<div class="flex items-start gap-3 min-w-0">
			<div
				class="w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center text-base sm:text-lg shrink-0 {account.account_type ===
				'cash'
					? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
					: account.account_type === 'credit_card'
						? 'bg-slate-100 text-slate-700 border border-slate-200'
						: 'bg-stone-100 text-stone-700 border border-stone-200'}"
			>
				{#if account.account_type === 'cash'}
					💵
				{:else if account.account_type === 'credit_card'}
					💳
				{:else}
					🏦
				{/if}
			</div>

			<div class="space-y-1 min-w-0">
				<h3
					class="font-bold text-sm sm:text-base text-brand-900 font-sans leading-snug break-words"
				>
					{account.name}
				</h3>
				<div class="flex flex-wrap items-center gap-1.5">
					<!-- Type Badge -->
					<span
						class="text-[10px] sm:text-[11px] font-mono capitalize px-2 py-0.5 rounded-md {account.account_type ===
						'cash'
							? 'bg-emerald-100 text-emerald-800'
							: account.account_type === 'credit_card'
								? 'bg-slate-100 text-slate-800'
								: 'bg-stone-100 text-stone-800'}"
					>
						{account.account_type.replace('_', ' ')}
					</span>
					<!-- Active Status -->
					<span
						class="text-[10px] sm:text-[11px] font-mono px-2 py-0.5 rounded-md {account.is_active
							? 'bg-brand-100 text-brand-800'
							: 'bg-brand-100 text-brand-500'}"
					>
						{account.is_active ? 'Active' : 'Archived'}
					</span>
				</div>
			</div>
		</div>

		<!-- Balance Display in JetBrains Mono -->
		<div
			class="flex xs:flex-col items-baseline xs:items-end justify-between xs:justify-start gap-1 pt-2 xs:pt-0 border-t xs:border-t-0 border-brand-100 shrink-0"
		>
			<div class="text-[11px] font-mono text-brand-600 uppercase tracking-wider">Balance</div>
			<div class="text-lg sm:text-xl font-mono font-bold tabular-nums text-brand-900">
				{formatCurrency(account.current_balance)}
			</div>
		</div>
	</div>

	<!-- Card Details Row (Responsive Grid) -->
	<div
		class="grid grid-cols-2 gap-2.5 sm:gap-3 py-2.5 sm:py-3 border-t border-b border-brand-100 text-xs"
	>
		<div class="min-w-0">
			<span class="text-brand-600 block text-[11px] sm:text-xs truncate">Statement Bal</span>
			<span class="font-mono tabular-nums font-semibold text-brand-900 truncate block">
				{account.total_statement_balance ? formatCurrency(account.total_statement_balance) : '—'}
			</span>
		</div>

		<div class="min-w-0">
			<span class="text-brand-600 block text-[11px] sm:text-xs truncate">Interest Saving</span>
			<span class="font-mono tabular-nums font-semibold text-brand-900 truncate block">
				{account.interest_saving_balance ? formatCurrency(account.interest_saving_balance) : '—'}
			</span>
		</div>

		<div class="min-w-0">
			<span class="text-brand-600 block text-[11px] sm:text-xs truncate">Due Date</span>
			<span class="font-mono tabular-nums font-semibold text-brand-900 truncate block">
				{#if account.due_date}
					{getOrdinalSuffix(account.due_date)} of mo
				{:else}
					—
				{/if}
			</span>
		</div>

		<div class="min-w-0">
			<span class="text-brand-600 block text-[11px] sm:text-xs truncate">Monthly Payment</span>
			<span class="font-mono tabular-nums font-semibold text-brand-900 truncate block">
				{account.monthly_payment ? formatCurrency(account.monthly_payment) : '—'}
			</span>
		</div>
	</div>

	<!-- Card Footer Action -->
	<div class="flex items-center justify-between pt-0.5">
		<span class="text-[11px] font-mono text-brand-500">
			ID #{account.id}
		</span>

		{#if account.account_type !== 'cash'}
			<button
				type="button"
				onclick={() => onedit?.(account)}
				class="px-3 py-1.5 rounded-lg text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 hover:text-brand-900 border border-brand-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
			>
				Edit Account
			</button>
		{:else}
			<span class="text-xs text-brand-400 italic">Cash Managed</span>
		{/if}
	</div>
</div>
