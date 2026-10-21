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
	const totalBalance = $derived.by(() => {
		return accounts.reduce((acc, a) => {
			const val = parseFloat(a.current_balance) || 0;
			return acc + (a.account_type === 'cash' ? val : -val);
		}, 0);
	});
	const totalLiabilities = $derived.by(() => {
		return accounts
			.filter((a) => a.account_type !== 'cash')
			.reduce((acc, a) => acc + (parseFloat(a.current_balance) || 0), 0);
	});
</script>

<svelte:head>
	<title>Accounts & Balances — Personal Finance</title>
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
		<div class="space-y-1">
			<div class="flex items-center gap-2">
				<h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-brand-900 font-sans">
					Accounts & Balances
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
			<p class="text-brand-700 text-xs sm:text-sm leading-relaxed">
				Track and manage deposit accounts, credit cards, statement schedules, and payment
				obligations.
			</p>
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
	<AccountOverviewStats {totalBalance} {totalLiabilities} {accounts} />

	<!-- Accounts Section -->
	<section class="space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans">
				{data.showAll ? 'All Accounts (Active & Archived)' : 'Active Accounts'}
			</h2>
			<span class="text-xs font-mono text-brand-600">
				{accounts.length} record{accounts.length === 1 ? '' : 's'}
			</span>
		</div>

		{#if accounts.length === 0}
			<AccountEmptyState onadd={() => (isAdding = true)} />
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 sm:gap-4">
				{#each accounts as account (account.id)}
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
