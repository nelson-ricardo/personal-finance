<script lang="ts">
	import type { PageProps } from './$types';
	import { APP_CONFIG } from '#lib/config.ts';
	import { resolve } from '$app/paths';
	import { formatCurrency, formatDate } from '#lib/utils/formatters.ts';
	import { superForm } from 'sveltekit-superforms';
	import Modal from '#lib/components/Modal.svelte';
	import TransferModal from '#lib/components/envelopes/TransferModal.svelte';
	import { getUserVisibleCategories } from '#lib/utils/categories.ts';

	let { data }: PageProps = $props();

	// Modal States
	let isQuickAddOpen = $state(false);
	let isTransferOpen = $state(false);

	// SuperForm for Quick Add
	// svelte-ignore state_referenced_locally
	const {
		form: quickForm,
		errors: quickErrors,
		enhance: enhanceQuick,
		submitting: adding
	} = superForm(data.quickAddForm, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				isQuickAddOpen = false;
			}
		}
	});

	// Derived Data
	const accounts = $derived(data.accounts);
	const categories = $derived(data.categories);
	const recentTransactions = $derived(data.recentTransactions);

	// Accounts breakdown
	const cashAccounts = $derived(accounts.filter((a) => a.account_type === 'cash'));
	const investmentAccounts = $derived(accounts.filter((a) => a.account_type === 'investment'));
	const creditAccounts = $derived(accounts.filter((a) => a.account_type === 'credit_card'));
	const loanAccounts = $derived(accounts.filter((a) => a.account_type === 'loan'));

	const totalCash = $derived(
		cashAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0)
	);
	const totalInvestments = $derived(
		investmentAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0)
	);
	const totalCredit = $derived(
		creditAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0)
	);
	const totalLoans = $derived(
		loanAccounts.reduce((sum, a) => sum + (parseFloat(a.current_balance) || 0), 0)
	);
	const totalLiabilities = $derived(totalCredit + totalLoans);
	const totalNetWorth = $derived(totalCash + totalInvestments - totalLiabilities);
	const netLiquidWorth = $derived(totalCash - totalCredit);

	// Envelopes breakdown
	const allEnvelopes = $derived(categories.flatMap((c) => c.envelopes));
	const activeEnvelopes = $derived(
		allEnvelopes.filter(
			(e) => e.is_active && e.name !== 'Unassigned' && e.name !== 'Account Adjustment'
		)
	);
	const unassignedEnv = $derived(allEnvelopes.find((e) => e.name === 'Unassigned'));
	const unassignedBalance = $derived(parseFloat(unassignedEnv?.balance ?? '0.00') || 0);

	const userCategories = $derived(getUserVisibleCategories(categories));

	// Envelopes needing attention (overspent or negative balance)
	const overspentEnvelopes = $derived(allEnvelopes.filter((e) => (parseFloat(e.balance) || 0) < 0));

	// Active envelopes list for modal dropdowns
	const selectableEnvelopes = $derived(
		userCategories.flatMap((c) => c.envelopes).filter((e) => e.is_active)
	);
	const selectableAccounts = $derived(
		accounts.filter(
			(a) => a.is_active && a.account_type !== 'loan' && a.account_type !== 'investment'
		)
	);
</script>

<svelte:head>
	<title>{APP_CONFIG.name} — Overview</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8">
	<!-- Apple Wallet Hero Card: Net Liquid & Stewardship Bar -->
	<div
		class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-700 text-white p-6 sm:p-8 shadow-sm border border-brand-400/20"
	>
		<!-- Specular Light Effect -->
		<div
			class="absolute -right-16 -top-16 w-72 h-72 rounded-full bg-white/10 pointer-events-none blur-3xl"
		></div>
		<div
			class="absolute -left-12 -bottom-12 w-64 h-64 rounded-full bg-brand-400/10 pointer-events-none blur-2xl"
		></div>

		<div class="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
			<!-- Primary Metrics -->
			<div class="space-y-2">
				<div class="flex items-center gap-2.5 flex-wrap">
					<span class="text-xs uppercase tracking-wider font-semibold text-brand-200">
						Total Net Worth
					</span>
					<span
						class="text-xs font-mono font-medium text-brand-100 bg-white/15 px-2.5 py-0.5 rounded-full border border-white/20"
					>
						Liquid: {formatCurrency(netLiquidWorth)}
					</span>
				</div>
				<div
					class="text-4xl sm:text-5xl font-mono font-bold tracking-tight tabular-nums text-white"
				>
					{formatCurrency(totalNetWorth)}
				</div>

				<!-- Ready to Assign Status Pill -->
				<div class="pt-1 flex items-center gap-2 flex-wrap">
					<div
						class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-md transition-colors {unassignedBalance <
						0
							? 'bg-[#6b1d2f]/80 text-white border border-[#6b1d2f]'
							: unassignedBalance > 0
								? 'bg-emerald-500/20 text-emerald-100 border border-emerald-400/30'
								: 'bg-white/10 text-brand-100 border border-white/15'}"
					>
						<span
							class="w-2 h-2 rounded-full {unassignedBalance < 0
								? 'bg-rose-400 animate-pulse'
								: unassignedBalance > 0
									? 'bg-emerald-400'
									: 'bg-brand-300'}"
						></span>
						<span>Ready to Assign:</span>
						<span class="font-mono font-bold tabular-nums">
							{formatCurrency(unassignedBalance)}
						</span>
					</div>

					{#if overspentEnvelopes.length > 0}
						<div
							class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-[#6b1d2f]/80 text-white border border-[#6b1d2f]"
						>
							<span class="w-2 h-2 rounded-full bg-rose-300 animate-pulse"></span>
							<span>{overspentEnvelopes.length} Overspent</span>
						</div>
					{/if}
				</div>
			</div>

			<!-- Apple Glass Quick Action Buttons -->
			<div class="flex flex-wrap items-center gap-2.5 pt-2 md:pt-0">
				<button
					type="button"
					onclick={() => (isQuickAddOpen = true)}
					class="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white text-brand-900 font-semibold text-xs sm:text-sm hover:bg-brand-50 transition-all shadow-xs cursor-pointer active:scale-98"
				>
					<svg class="w-4 h-4 text-brand-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2.5"
							d="M12 4v16m8-8H4"
						/>
					</svg>
					<span>New Expense</span>
				</button>

				<button
					type="button"
					onclick={() => (isTransferOpen = true)}
					class="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white/15 hover:bg-white/25 text-white font-semibold text-xs sm:text-sm backdrop-blur-md transition-all border border-white/20 shadow-2xs cursor-pointer active:scale-98"
				>
					<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
						/>
					</svg>
					<span>Transfer Funds</span>
				</button>
			</div>
		</div>
	</div>

	<!-- 2-Column Responsive Adaptive Grid: Accounts & Envelopes -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Accounts Grouped Inset Card -->
		<section
			class="bg-white rounded-3xl border border-brand-200/70 p-5 sm:p-6 shadow-2xs flex flex-col justify-between"
		>
			<div>
				<div class="flex items-center justify-between pb-3 border-b border-brand-100">
					<div class="flex items-center gap-2">
						<h2 class="text-base font-bold tracking-tight text-brand-950 font-sans">Accounts</h2>
						<span
							class="px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-100 text-brand-700"
						>
							{accounts.length}
						</span>
					</div>
					<a
						href={resolve('/accounts')}
						class="text-xs font-semibold text-brand-600 hover:text-brand-900 inline-flex items-center gap-1 transition-colors"
					>
						<span>View All</span>
						<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</a>
				</div>

				<!-- Grouped Inset List of Account Categories -->
				<div class="divide-y divide-brand-100/80">
					<!-- Cash & Checking -->
					<div class="py-3.5 flex items-center justify-between">
						<div class="flex items-center gap-3">
							<div
								class="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-800 flex items-center justify-center font-bold text-sm shrink-0 border border-emerald-200/60"
							>
								💵
							</div>
							<div>
								<div class="text-sm font-semibold text-brand-950">Cash & Checking</div>
								<div class="text-xs text-brand-400">{cashAccounts.length} accounts</div>
							</div>
						</div>
						<div class="text-sm font-mono font-bold tabular-nums text-brand-900">
							{formatCurrency(totalCash)}
						</div>
					</div>

					<!-- Investments & Portfolio -->
					{#if investmentAccounts.length > 0}
						<div class="py-3.5 flex items-center justify-between">
							<div class="flex items-center gap-3">
								<div
									class="w-9 h-9 rounded-xl bg-teal-50 text-teal-800 flex items-center justify-center font-bold text-sm shrink-0 border border-teal-200/60"
								>
									📈
								</div>
								<div>
									<div class="text-sm font-semibold text-brand-950">Investments</div>
									<div class="text-xs text-brand-400">
										{investmentAccounts.length} account{investmentAccounts.length === 1 ? '' : 's'}
									</div>
								</div>
							</div>
							<div class="text-sm font-mono font-bold tabular-nums text-emerald-800">
								{formatCurrency(totalInvestments)}
							</div>
						</div>
					{/if}

					<!-- Credit Cards -->
					<div class="py-3.5 flex items-center justify-between">
						<div class="flex items-center gap-3">
							<div
								class="w-9 h-9 rounded-xl bg-brand-100 text-brand-800 flex items-center justify-center font-bold text-sm shrink-0 border border-brand-200"
							>
								💳
							</div>
							<div>
								<div class="text-sm font-semibold text-brand-950">Credit Cards</div>
								<div class="text-xs text-brand-400">{creditAccounts.length} accounts</div>
							</div>
						</div>
						<div
							class="text-sm font-mono font-bold tabular-nums {totalCredit > 0
								? 'text-[#6b1d2f]'
								: 'text-brand-900'}"
						>
							{formatCurrency(totalCredit)}
						</div>
					</div>

					<!-- Loans & Debt if any -->
					{#if loanAccounts.length > 0}
						<div class="py-3.5 flex items-center justify-between">
							<div class="flex items-center gap-3">
								<div
									class="w-9 h-9 rounded-xl bg-brand-100 text-brand-800 flex items-center justify-center font-bold text-sm shrink-0 border border-brand-200"
								>
									🏦
								</div>
								<div>
									<div class="text-sm font-semibold text-brand-950">Loans</div>
									<div class="text-xs text-brand-400">{loanAccounts.length} accounts</div>
								</div>
							</div>
							<div class="text-sm font-mono font-bold tabular-nums text-[#6b1d2f]">
								{formatCurrency(totalLoans)}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Individual Accounts Inset Pills -->
			{#if accounts.length > 0}
				<div class="pt-4 border-t border-brand-100 flex flex-wrap gap-2">
					{#each accounts.slice(0, 4) as account (account.id)}
						<a
							href={resolve('/accounts')}
							class="inline-flex items-center justify-between gap-3 px-3 py-1.5 rounded-xl bg-brand-50 hover:bg-brand-100/80 text-brand-800 text-xs font-medium border border-brand-200/60 transition-colors"
						>
							<span class="truncate max-w-[120px]">{account.name}</span>
							<span
								class="font-mono font-bold tabular-nums {account.account_type === 'credit_card' &&
								parseFloat(account.current_balance) > 0
									? 'text-[#6b1d2f]'
									: 'text-brand-950'}"
							>
								{formatCurrency(parseFloat(account.current_balance) || 0)}
							</span>
						</a>
					{/each}
				</div>
			{/if}
		</section>

		<!-- Envelope Health & Budget Progress Card -->
		<section
			class="bg-white rounded-3xl border border-brand-200/70 p-5 sm:p-6 shadow-2xs flex flex-col justify-between"
		>
			<div>
				<div class="flex items-center justify-between pb-3 border-b border-brand-100">
					<div class="flex items-center gap-2">
						<h2 class="text-base font-bold tracking-tight text-brand-950 font-sans">Envelopes</h2>
						<span
							class="px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-brand-100 text-brand-700"
						>
							{activeEnvelopes.length} Active
						</span>
					</div>
					<a
						href={resolve('/envelopes')}
						class="text-xs font-semibold text-brand-600 hover:text-brand-900 inline-flex items-center gap-1 transition-colors"
					>
						<span>View All</span>
						<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</a>
				</div>

				<!-- Categories Breakdown -->
				{#if userCategories.length === 0}
					<div class="py-8 text-center space-y-3">
						<div
							class="w-10 h-10 rounded-full bg-brand-100 text-brand-600 mx-auto flex items-center justify-center text-lg"
						>
							✉️
						</div>
						<p class="text-sm font-semibold text-brand-800">No categories created</p>
						<a
							href={resolve('/envelopes')}
							class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:underline"
						>
							<span>Set up your envelopes</span>
							<span>→</span>
						</a>
					</div>
				{:else}
					<div class="divide-y divide-brand-100/80">
						{#each userCategories.slice(0, 4) as category (category.name)}
							{@const catBalance = category.envelopes.reduce(
								(sum, e) => sum + (parseFloat(e.balance) || 0),
								0
							)}
							{@const totalAllocated = userCategories.reduce(
								(sum, c) =>
									sum +
									c.envelopes.reduce(
										(esum, e) => esum + Math.max(0, parseFloat(e.balance) || 0),
										0
									),
								0
							)}
							{@const percent =
								totalAllocated > 0
									? Math.min(100, Math.round((Math.max(0, catBalance) / totalAllocated) * 100))
									: 0}
							{@const hasNegative = category.envelopes.some(
								(e) => (parseFloat(e.balance) || 0) < 0
							)}

							<div class="py-3 space-y-1.5">
								<div class="flex items-center justify-between text-xs sm:text-sm">
									<div class="flex items-center gap-1.5">
										<span class="font-semibold text-brand-950 truncate max-w-[160px]">
											{category.name}
										</span>
										{#if hasNegative}
											<span class="w-1.5 h-1.5 rounded-full bg-[#6b1d2f]" title="Envelope overspent"
											></span>
										{/if}
									</div>
									<div class="font-mono font-bold tabular-nums text-brand-900">
										{formatCurrency(catBalance)}
									</div>
								</div>

								<!-- Progress Bar -->
								<div class="w-full bg-brand-100 rounded-full h-1.5 overflow-hidden">
									<div
										class="h-1.5 rounded-full transition-all {hasNegative
											? 'bg-[#6b1d2f]'
											: 'bg-brand-500'}"
										style="width: {Math.max(0, percent)}%"
									></div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Envelopes Summary Footer -->
			<div class="pt-4 border-t border-brand-100 flex items-center justify-between text-xs">
				<span class="text-brand-500 font-medium">Allocated Budget</span>
				<span class="font-mono font-bold tabular-nums text-brand-900">
					{formatCurrency(
						userCategories.reduce(
							(sum, c) =>
								sum + c.envelopes.reduce((esum, e) => esum + (parseFloat(e.balance) || 0), 0),
							0
						)
					)}
				</span>
			</div>
		</section>
	</div>

	<!-- Recent Transactions Ledger Grouped Inset Card -->
	<section class="bg-white rounded-3xl border border-brand-200/70 p-5 sm:p-6 shadow-2xs">
		<div class="flex items-center justify-between pb-3 border-b border-brand-100">
			<div class="flex items-center gap-2">
				<h2 class="text-base font-bold tracking-tight text-brand-950 font-sans">Recent Activity</h2>
			</div>
			<a
				href={resolve('/transactions')}
				class="text-xs font-semibold text-brand-600 hover:text-brand-900 inline-flex items-center gap-1 transition-colors"
			>
				<span>View All</span>
				<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</a>
		</div>

		{#if recentTransactions.length === 0}
			<div class="py-10 text-center space-y-3">
				<div
					class="w-10 h-10 rounded-full bg-brand-100 text-brand-600 mx-auto flex items-center justify-center text-lg"
				>
					🧾
				</div>
				<p class="text-sm font-semibold text-brand-800">No transactions recorded yet</p>
				<button
					type="button"
					onclick={() => (isQuickAddOpen = true)}
					class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-brand-500 text-white text-xs font-semibold hover:bg-brand-600 transition-colors shadow-2xs cursor-pointer"
				>
					<span>Record First Expense</span>
				</button>
			</div>
		{:else}
			<div class="divide-y divide-brand-100/80">
				{#each recentTransactions as tx (tx.id)}
					{@const totalNum = typeof tx.total === 'number' ? tx.total : parseFloat(tx.total) || 0}

					<div
						class="py-3 sm:py-3.5 flex items-center justify-between gap-3 hover:bg-brand-50/50 -mx-2 px-2 rounded-xl transition-colors"
					>
						<!-- Left: Merchant & Badges -->
						<div class="min-w-0 flex items-center gap-3">
							<div
								class="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 border {tx.transaction_type ===
								'INCOME'
									? 'bg-emerald-50 text-emerald-800 border-emerald-200/60'
									: 'bg-brand-100/80 text-brand-800 border-brand-200'}"
							>
								{#if tx.transaction_type === 'INCOME'}
									↓
								{:else if tx.transaction_type === 'TRANSFER'}
									⇄
								{:else}
									↑
								{/if}
							</div>

							<div class="min-w-0">
								<div class="text-sm font-semibold text-brand-950 truncate">
									{tx.merchant}
								</div>
								<div class="flex items-center gap-1.5 flex-wrap text-xs text-brand-400 mt-0.5">
									<span>{formatDate(tx.logged_date)}</span>
									<span>•</span>
									<span class="truncate">{tx.payment_method_name}</span>
									{#if tx.splits && tx.splits.length > 0}
										<span>•</span>
										<span
											class="px-1.5 py-0.2 rounded bg-brand-100 text-brand-700 font-medium text-[10px]"
										>
											{tx.splits[0].envelope_name}
										</span>
									{/if}
								</div>
							</div>
						</div>

						<!-- Right: Total Amount in JetBrains Mono -->
						<div
							class="text-sm font-mono font-bold tabular-nums shrink-0 {tx.transaction_type ===
							'INCOME'
								? 'text-emerald-700'
								: 'text-brand-900'}"
						>
							{formatCurrency(totalNum)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>

<!-- Quick Add Expense Modal -->
<Modal open={isQuickAddOpen} title="Record Expense" onclose={() => (isQuickAddOpen = false)}>
	<form method="POST" action="?/quickAdd" use:enhanceQuick class="space-y-4">
		<!-- Amount -->
		<div>
			<label
				for="home-quick-amount"
				class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
			>
				Amount
			</label>
			<div class="relative">
				<span class="absolute left-3 top-2.5 text-brand-400 font-mono text-sm">$</span>
				<input
					id="home-quick-amount"
					name="amount"
					type="text"
					inputmode="decimal"
					placeholder="0.00"
					bind:value={$quickForm.amount}
					class="w-full pl-8 pr-3 py-2 rounded-xl border border-brand-200 bg-white font-mono text-base font-bold text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					required
				/>
			</div>
			{#if $quickErrors.amount}
				<p class="text-xs text-[#6b1d2f] mt-1">{$quickErrors.amount}</p>
			{/if}
		</div>

		<!-- Merchant -->
		<div>
			<label
				for="home-quick-merchant"
				class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
			>
				Merchant / Payee
			</label>
			<input
				id="home-quick-merchant"
				name="merchant"
				type="text"
				placeholder="e.g. Grocery Store"
				bind:value={$quickForm.merchant}
				class="w-full px-3 py-2 rounded-xl border border-brand-200 bg-white text-sm text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
				required
			/>
			{#if $quickErrors.merchant}
				<p class="text-xs text-[#6b1d2f] mt-1">{$quickErrors.merchant}</p>
			{/if}
		</div>

		<!-- Account & Envelope Grid -->
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
			<div>
				<label
					for="home-quick-acct"
					class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
				>
					Account
				</label>
				<select
					id="home-quick-acct"
					name="payment_method_name"
					bind:value={$quickForm.payment_method_name}
					class="w-full px-3 py-2 rounded-xl border border-brand-200 bg-white text-sm text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					required
				>
					<option value="" disabled>Select account</option>
					{#each selectableAccounts as account (account.id)}
						<option value={account.name}>{account.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<label
					for="home-quick-env"
					class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
				>
					Envelope
				</label>
				<select
					id="home-quick-env"
					name="envelope_name"
					bind:value={$quickForm.envelope_name}
					class="w-full px-3 py-2 rounded-xl border border-brand-200 bg-white text-sm text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					required
				>
					<option value="" disabled>Select envelope</option>
					{#each selectableEnvelopes as env (env.id)}
						<option value={env.name}>{env.name}</option>
					{/each}
				</select>
			</div>
		</div>

		<!-- Date & Optional Note -->
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
			<div>
				<label
					for="home-quick-date"
					class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
				>
					Date
				</label>
				<input
					id="home-quick-date"
					name="logged_date"
					type="date"
					bind:value={$quickForm.logged_date}
					class="w-full px-3 py-2 rounded-xl border border-brand-200 bg-white text-sm text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					required
				/>
			</div>

			<div>
				<label
					for="home-quick-note"
					class="block text-xs font-bold uppercase tracking-wider text-brand-700 mb-1"
				>
					Note (Optional)
				</label>
				<input
					id="home-quick-note"
					name="note"
					type="text"
					placeholder="Details"
					bind:value={$quickForm.note}
					class="w-full px-3 py-2 rounded-xl border border-brand-200 bg-white text-sm text-brand-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
				/>
			</div>
		</div>

		<!-- Submit -->
		<div class="pt-2 flex justify-end gap-2">
			<button
				type="button"
				onclick={() => (isQuickAddOpen = false)}
				class="px-4 py-2 rounded-xl border border-brand-200 text-xs font-semibold text-brand-700 hover:bg-brand-50 cursor-pointer"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={$adding}
				class="px-4 py-2 rounded-xl bg-brand-500 text-white text-xs font-semibold hover:bg-brand-600 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
			>
				{$adding ? 'Saving...' : 'Add Expense'}
			</button>
		</div>
	</form>
</Modal>

<!-- Transfer Modal -->
<TransferModal
	open={isTransferOpen}
	formData={data.transferForm}
	envelopes={allEnvelopes}
	onclose={() => (isTransferOpen = false)}
/>
