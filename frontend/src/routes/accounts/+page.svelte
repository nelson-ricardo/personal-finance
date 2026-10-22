<script lang="ts">
	import type { PageProps } from './$types';
	import type { Account } from '#lib/schemas/account.ts';
	import type { ResolvedPathname } from '$app/types';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import AccountOverviewStats from '#lib/components/accounts/AccountOverviewStats.svelte';
	import AccountCard from '#lib/components/accounts/AccountCard.svelte';
	import AccountEmptyState from '#lib/components/accounts/AccountEmptyState.svelte';
	import AddAccountModal from '#lib/components/accounts/AddAccountModal.svelte';
	import EditAccountModal from '#lib/components/accounts/EditAccountModal.svelte';
	import AccountOperationsModal, {
		type OperationTab
	} from '#lib/components/accounts/AccountOperationsModal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let { data }: PageProps = $props();

	let isAdding = $state(false);
	let editingAccount = $state<Account | null>(null);

	// Operations Modal state
	let isOperationsOpen = $state(false);
	let selectedOperationTab = $state<OperationTab>('payment');
	let selectedOperationAccount = $state<string>('');

	function openOperations(tab: OperationTab = 'payment', account?: Account) {
		selectedOperationTab = tab;
		selectedOperationAccount = account?.name || '';
		isOperationsOpen = true;
	}

	const allAccountsUrl = `${resolve('/accounts')}?all=true` as unknown as ResolvedPathname;
	const activeAccountsUrl = resolve('/accounts');

	// Derived metrics
	const accounts = $derived(data.accounts);
	const activeAccounts = $derived(accounts.filter((a) => a.is_active));
	const cashAccounts = $derived(accounts.filter((a) => a.account_type === 'cash'));
	const investmentAccounts = $derived(accounts.filter((a) => a.account_type === 'investment'));
	const debtAccounts = $derived(
		accounts.filter((a) => a.account_type !== 'cash' && a.account_type !== 'investment')
	);

	const totalCash = $derived.by(() => {
		return cashAccounts.reduce((acc, a) => acc + (parseFloat(a.current_balance) || 0), 0);
	});
	const totalInvestments = $derived.by(() => {
		return investmentAccounts.reduce((acc, a) => acc + (parseFloat(a.current_balance) || 0), 0);
	});
	const creditCardDebt = $derived.by(() => {
		return accounts
			.filter((a) => a.account_type === 'credit_card')
			.reduce((acc, a) => acc + (parseFloat(a.current_balance) || 0), 0);
	});
	const totalLiabilities = $derived.by(() => {
		return debtAccounts.reduce((acc, a) => acc + (parseFloat(a.current_balance) || 0), 0);
	});
	const totalNetWorth = $derived(totalCash + totalInvestments - totalLiabilities);
	const netLiquid = $derived(totalCash - creditCardDebt);
</script>

<svelte:head>
	<title>Accounts — Homeledger</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8">
	<!-- Flash Feedback Banners -->
	{#if page.form?.accountActionError}
		<div
			class="p-3.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/30 text-xs font-medium flex items-center justify-between shadow-2xs"
		>
			<div class="flex items-center gap-2">
				<span>⚠️</span>
				<span>{page.form.accountActionError}</span>
			</div>
		</div>
	{/if}
	{#if page.form?.message}
		<div
			class="p-3.5 rounded-xl bg-emerald-50 text-emerald-900 border border-emerald-200 text-xs font-medium flex items-center justify-between shadow-2xs"
		>
			<div class="flex items-center gap-2">
				<span>✅</span>
				<span>{page.form.message}</span>
			</div>
		</div>
	{/if}

	<!-- Page Header with Summary & Actions -->
	<div
		class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 pb-4 border-b border-brand-200"
	>
		<div class="flex items-center gap-2.5 flex-wrap">
			<h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-brand-900 font-sans">
				Accounts
			</h1>
			<span
				class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800 border border-brand-200"
			>
				{activeAccounts.length} Active
			</span>
			{#if data.showAll}
				<span
					class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300"
				>
					Including Archived
				</span>
			{/if}
		</div>

		<div class="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
			<!-- Operations Action Button (Single button handling all account transactions) -->
			<button
				type="button"
				onclick={() => openOperations('payment')}
				class="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl border border-brand-300 bg-white text-brand-900 text-xs sm:text-sm font-semibold hover:bg-brand-50 hover:border-brand-400 shadow-2xs transition-all duration-150 cursor-pointer"
			>
				<span class="text-base leading-none">⚡</span>
				<span>Account Actions</span>
			</button>

			{#if !data.showAll}
				<a
					href={allAccountsUrl}
					class="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs sm:text-sm font-semibold hover:bg-brand-50 hover:text-brand-950 shadow-2xs transition-all duration-150 cursor-pointer"
				>
					<svg class="w-4 h-4 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 6h16M4 12h16M4 18h7"
						/>
					</svg>
					<span>Show All Accounts</span>
				</a>
			{:else}
				<a
					href={activeAccountsUrl}
					class="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl border border-brand-300 bg-brand-100 text-brand-900 text-xs sm:text-sm font-semibold hover:bg-brand-200 shadow-2xs transition-all duration-150 cursor-pointer"
				>
					<svg class="w-4 h-4 text-brand-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
						/>
					</svg>
					<span>Show Active Only</span>
				</a>
			{/if}

			<button
				type="button"
				onclick={() => (isAdding = true)}
				class="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 active:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 shadow-sm transition-all duration-150 cursor-pointer"
			>
				<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2.5"
						d="M12 4v16m8-8H4"
					/>
				</svg>
				<span>Add Account</span>
			</button>
		</div>
	</div>

	<!-- Financial Overview Stats Cards -->
	<AccountOverviewStats {totalNetWorth} {netLiquid} {totalInvestments} {totalLiabilities} />

	<!-- Cash & Liquid Deposits Section (Apple-style horizontal cards) -->
	{#if cashAccounts.length > 0}
		<section class="space-y-3">
			<div class="flex items-center justify-between">
				<h2 class="text-xs font-bold uppercase tracking-wider text-brand-700 font-sans">
					Liquid Cash
				</h2>
				<span class="text-xs font-mono text-brand-500">
					{cashAccounts.length} account{cashAccounts.length === 1 ? '' : 's'}
				</span>
			</div>

			<div class="space-y-2.5">
				{#each cashAccounts as account (account.id)}
					<div
						class="bg-white rounded-2xl border border-brand-200/90 p-4 sm:p-5 shadow-2xs hover:shadow-xs transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
					>
						<!-- Left: Emblem, Identity & Balance -->
						<div class="flex items-center gap-3.5 min-w-0">
							<div
								class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-100 flex items-center justify-center text-lg shrink-0"
							>
								💵
							</div>
							<div class="min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<h3 class="font-bold text-base text-brand-900 font-sans leading-snug truncate">
										{account.name}
									</h3>
									{#if !account.is_active}
										<span
											class="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200"
										>
											Archived
										</span>
									{/if}
								</div>
								<div
									class="text-2xl sm:text-3xl font-mono font-bold tabular-nums text-brand-950 mt-0.5"
								>
									{formatCurrency(account.current_balance)}
								</div>
							</div>
						</div>

						<!-- Right: Actions (Adjust Balance, + Interest, Edit) -->
						<div class="flex flex-wrap items-center gap-2 self-start sm:self-center shrink-0">
							{#if !account.is_active}
								<form method="POST" action="?/activateAccount" class="inline">
									<input type="hidden" name="name" value={account.name} />
									<button
										type="submit"
										class="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 transition-colors cursor-pointer flex items-center gap-1 shadow-2xs"
										title="Reactivate this archived account"
									>
										<span>🔄 Reactivate</span>
									</button>
								</form>
							{:else}
								<button
									type="button"
									onclick={() => openOperations('adjustment', account)}
									class="px-3 py-1.5 rounded-xl text-xs font-semibold text-brand-800 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer flex items-center gap-1.5 shadow-2xs"
									title="Reconcile cash balance"
								>
									<span>⚖️</span>
									<span>Adjust Balance</span>
								</button>

								<button
									type="button"
									onclick={() => openOperations('interest_earned', account)}
									class="px-3 py-1.5 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer flex items-center gap-1.5 shadow-2xs"
									title="Log interest earned (APY)"
								>
									<span>💰</span>
									<span>+ Interest</span>
								</button>
							{/if}

							<button
								type="button"
								onclick={() => (editingAccount = account)}
								class="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-brand-600 hover:text-brand-900 hover:bg-brand-100/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
								title="Edit account settings"
							>
								Edit
							</button>
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Investments & Portfolio Section (Apple-style asset tracking cards) -->
	{#if investmentAccounts.length > 0}
		<section class="space-y-3">
			<div class="flex items-center justify-between">
				<h2 class="text-xs font-bold uppercase tracking-wider text-brand-700 font-sans">
					Investments & Portfolio
				</h2>
				<span class="text-xs font-mono text-brand-500">
					{investmentAccounts.length} account{investmentAccounts.length === 1 ? '' : 's'}
				</span>
			</div>

			<div class="space-y-2.5">
				{#each investmentAccounts as account (account.id)}
					<div
						class="bg-white rounded-2xl border border-brand-200/90 p-4 sm:p-5 shadow-2xs hover:shadow-xs transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
					>
						<!-- Left: Emblem, Identity & Balance -->
						<div class="flex items-center gap-3.5 min-w-0">
							<div
								class="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 border border-teal-100 flex items-center justify-center text-lg shrink-0"
							>
								📈
							</div>
							<div class="min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<h3 class="font-bold text-base text-brand-900 font-sans leading-snug truncate">
										{account.name}
									</h3>
									{#if !account.is_active}
										<span
											class="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 border border-amber-200"
										>
											Archived
										</span>
									{/if}
								</div>
								<div
									class="text-2xl sm:text-3xl font-mono font-bold tabular-nums text-emerald-900 mt-0.5"
								>
									{formatCurrency(account.current_balance)}
								</div>
							</div>
						</div>

						<!-- Right: Actions (Adjust Balance, Edit) -->
						<div class="flex flex-wrap items-center gap-2 self-start sm:self-center shrink-0">
							{#if !account.is_active}
								<form method="POST" action="?/activateAccount" class="inline">
									<input type="hidden" name="name" value={account.name} />
									<button
										type="submit"
										class="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 transition-colors cursor-pointer flex items-center gap-1 shadow-2xs"
										title="Reactivate this archived account"
									>
										<span>🔄 Reactivate</span>
									</button>
								</form>
							{:else}
								<button
									type="button"
									onclick={() => openOperations('adjustment', account)}
									class="px-3 py-1.5 rounded-xl text-xs font-semibold text-brand-800 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer flex items-center gap-1.5 shadow-2xs"
									title="Reconcile market value"
								>
									<span>⚖️</span>
									<span>Adjust Balance</span>
								</button>

								<button
									type="button"
									onclick={() => openOperations('payment', account)}
									class="px-3 py-1.5 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer flex items-center gap-1.5 shadow-2xs"
									title="Transfer cash to investment"
								>
									<span>💸</span>
									<span>Transfer In</span>
								</button>
							{/if}

							<button
								type="button"
								onclick={() => (editingAccount = account)}
								class="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-brand-600 hover:text-brand-900 hover:bg-brand-100/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 cursor-pointer"
								title="Edit account settings"
							>
								Edit
							</button>
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Credit Cards & Loans (Structured Liabilities & Debt) -->
	<section class="space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans">
				{data.showAll ? 'Credit Cards & Loans (All)' : 'Credit Cards & Loans'}
			</h2>
			<span class="text-xs font-mono text-brand-600">
				{debtAccounts.length} record{debtAccounts.length === 1 ? '' : 's'}
			</span>
		</div>

		{#if debtAccounts.length === 0}
			{#if cashAccounts.length === 0 && investmentAccounts.length === 0}
				<AccountEmptyState onadd={() => (isAdding = true)} />
			{:else}
				<div
					class="bg-white rounded-2xl border border-dashed border-brand-200 p-6 text-center space-y-2"
				>
					<p class="text-xs text-brand-500">No credit cards or loans tracked yet.</p>
					<button
						type="button"
						onclick={() => (isAdding = true)}
						class="text-xs font-semibold text-brand-700 hover:text-brand-950 underline"
					>
						+ Add Credit Card or Loan
					</button>
				</div>
			{/if}
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 sm:gap-4">
				{#each debtAccounts as account (account.id)}
					<AccountCard
						{account}
						envelopes={data.envelopes}
						onedit={(acc: Account) => (editingAccount = acc)}
						onoperation={(tab, acc) => openOperations(tab, acc)}
					/>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Add Account Modal with Scroll-Lock -->
	<AddAccountModal
		open={isAdding}
		formData={data.createForm}
		categories={data.categories}
		onclose={() => (isAdding = false)}
	/>

	<!-- Edit Account Modal with Scroll-Lock -->
	<EditAccountModal
		open={editingAccount !== null}
		formData={data.updateForm}
		account={editingAccount}
		onclose={() => (editingAccount = null)}
	/>

	<!-- Account Operations Modal (Debt Payment, Balance Adjustment, Interest Charge, Interest Earned) -->
	<AccountOperationsModal
		open={isOperationsOpen}
		initialTab={selectedOperationTab}
		initialAccountName={selectedOperationAccount}
		accounts={data.accounts}
		categories={data.categories}
		envelopes={data.envelopes}
		paymentFormData={data.paymentForm}
		adjustmentFormData={data.adjustmentForm}
		interestChargeFormData={data.interestChargeForm}
		interestEarnedFormData={data.interestEarnedForm}
		onclose={() => (isOperationsOpen = false)}
	/>
</div>
