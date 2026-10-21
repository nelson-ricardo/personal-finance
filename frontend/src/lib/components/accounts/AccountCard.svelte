<script lang="ts">
	import type { Account } from '#lib/schemas/account.ts';
	import type { Envelope } from '#lib/schemas/category.ts';
	import { formatCurrency, getOrdinalSuffix } from '#lib/utils/formatters.ts';

	let {
		account,
		envelopes = [],
		onedit,
		onoperation
	}: {
		account: Account;
		envelopes?: Envelope[];
		onedit?: (account: Account) => void;
		onoperation?: (
			tab: 'payment' | 'adjustment' | 'interest_charge' | 'interest_earned',
			account: Account
		) => void;
	} = $props();

	const linkedEnvelope = $derived.by(() => {
		if (account.account_type === 'cash') return null;

		// 1. Match by account.envelope_id
		if (account.envelope_id) {
			const found = envelopes.find((e) => e.id === account.envelope_id);
			if (found) return found;
		}

		const acctNameLower = account.name.toLowerCase();

		// 2. If Credit Card
		if (account.account_type === 'credit_card') {
			const found = envelopes.find(
				(e) =>
					e.system_role?.toUpperCase() === 'CREDIT_CARD_PAYMENT' ||
					e.name.toLowerCase() === 'credit card payment' ||
					e.name.toLowerCase() === `credit card payment - ${acctNameLower}` ||
					e.name.toLowerCase().includes(acctNameLower)
			);
			if (found) return found;
		}

		// 3. If Loan
		const found = envelopes.find(
			(e) => e.name.toLowerCase() === acctNameLower || e.name.toLowerCase().includes(acctNameLower)
		);
		if (found) return found;

		return null;
	});

	const displayEnvelopeName = $derived(account.envelope_name ?? linkedEnvelope?.name ?? null);
	const displayEnvelopeBalance = $derived(
		account.envelope_balance ?? linkedEnvelope?.balance ?? null
	);
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

	<!-- Available in Envelope Banner for Debt Accounts -->
	{#if account.account_type === 'credit_card' || account.account_type === 'loan'}
		<div
			class="flex items-center justify-between px-3 py-2 rounded-xl bg-emerald-50/80 border border-emerald-200/80 text-xs"
		>
			<span class="text-emerald-900 font-medium flex items-center gap-1.5">
				<span>✉️</span>
				<span>Available in Envelope</span>
				{#if displayEnvelopeName}
					<span class="text-[10px] text-emerald-700 font-sans">({displayEnvelopeName})</span>
				{/if}
			</span>
			<span class="font-mono tabular-nums font-bold text-emerald-900 text-sm">
				{displayEnvelopeBalance != null ? formatCurrency(displayEnvelopeBalance) : '—'}
			</span>
		</div>
	{/if}

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

	<!-- Card Footer Action Buttons -->
	<div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-brand-100/70">
		<span class="text-[11px] font-mono text-brand-500">
			ID #{account.id}
		</span>

		<div class="flex flex-wrap items-center gap-1.5">
			{#if !account.is_active}
				<form method="POST" action="?/activateAccount" class="inline">
					<input type="hidden" name="name" value={account.name} />
					<button
						type="submit"
						class="px-2.5 py-1 rounded-lg text-xs font-semibold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 transition-colors cursor-pointer flex items-center gap-1 shadow-2xs"
						title="Reactivate this archived account"
					>
						<span>🔄</span>
						<span>Reactivate</span>
					</button>
				</form>

				<button
					type="button"
					onclick={() => onedit?.(account)}
					class="px-2 py-1 rounded-lg text-xs font-semibold text-brand-600 hover:text-brand-900 hover:bg-brand-100/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
					title="Edit account settings"
				>
					Edit
				</button>
			{:else if account.account_type === 'credit_card' || account.account_type === 'loan'}
				<button
					type="button"
					onclick={() => onoperation?.('payment', account)}
					class="px-2.5 py-1 rounded-lg text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer flex items-center gap-1"
					title="Record payment toward debt"
				>
					<span>💳</span>
					<span>Pay</span>
				</button>

				<button
					type="button"
					onclick={() => onoperation?.('adjustment', account)}
					class="px-2 py-1 rounded-lg text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
					title="Reconcile account balance"
				>
					<span>⚖️ Adjust</span>
				</button>

				<button
					type="button"
					onclick={() => onoperation?.('interest_charge', account)}
					class="px-2 py-1 rounded-lg text-xs font-semibold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 cursor-pointer"
					title="Log interest or finance fee"
				>
					<span>📈 Interest</span>
				</button>

				<button
					type="button"
					onclick={() => onedit?.(account)}
					class="px-2 py-1 rounded-lg text-xs font-semibold text-brand-600 hover:text-brand-900 hover:bg-brand-100/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
					title="Edit account settings"
				>
					Edit
				</button>
			{:else}
				<button
					type="button"
					onclick={() => onoperation?.('adjustment', account)}
					class="px-2.5 py-1 rounded-lg text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer flex items-center gap-1"
					title="Reconcile cash balance"
				>
					<span>⚖️</span>
					<span>Adjust Balance</span>
				</button>

				<button
					type="button"
					onclick={() => onoperation?.('interest_earned', account)}
					class="px-2.5 py-1 rounded-lg text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer flex items-center gap-1"
					title="Log interest earned (APY)"
				>
					<span>💰</span>
					<span>+ Interest</span>
				</button>
			{/if}
		</div>
	</div>
</div>
