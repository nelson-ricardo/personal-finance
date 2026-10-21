<script lang="ts">
	import type { PageProps } from './$types';
	import type { TransactionItem } from '#lib/schemas/transaction.ts';
	import TransactionQuickAdd from '#lib/components/transactions/TransactionQuickAdd.svelte';
	import TransactionFilterDrawer from '#lib/components/transactions/TransactionFilterDrawer.svelte';
	import TransactionTable from '#lib/components/transactions/TransactionTable.svelte';
	import TransactionCardList from '#lib/components/transactions/TransactionCardList.svelte';
	import TransactionModal from '#lib/components/transactions/TransactionModal.svelte';
	import TransactionDrawer from '#lib/components/transactions/TransactionDrawer.svelte';
	import TransactionDeleteModal from '#lib/components/transactions/TransactionDeleteModal.svelte';
	import TransactionBulkBar from '#lib/components/transactions/TransactionBulkBar.svelte';

	let { data }: PageProps = $props();

	// Modal & Drawer State
	let isFilterOpen = $state(false);
	let isModalOpen = $state(false);
	let modalDraft = $state<{
		merchant: string;
		amount: string;
		logged_date: string;
		payment_method_name: string;
		envelope_name: string;
		note: string;
	} | null>(null);

	let isDrawerOpen = $state(false);
	let activeTransaction = $state<TransactionItem | null>(null);

	let isDeleteModalOpen = $state(false);
	let transactionToDelete = $state<TransactionItem | null>(null);

	// Selection & Bulk state
	let selectedIds = $state<number[]>([]);
	let isMobileSelectMode = $state(false);

	// Client-side quick search query
	// svelte-ignore state_referenced_locally
	let searchInput = $state(data.filters.searchQuery || '');

	// Sorting & Pagination
	let sortBy = $state<'date' | 'merchant' | 'account' | 'amount'>('date');
	let sortOrder = $state<'asc' | 'desc'>('desc');
	let pageSize = $state<number>(25);
	let currentPage = $state<number>(1);

	// Filtered & Sorted Transactions
	const filteredTransactions = $derived(
		data.transactions.filter((tx) => {
			if (!searchInput.trim()) return true;
			const q = searchInput.toLowerCase().trim();
			const matchMerchant = tx.merchant.toLowerCase().includes(q);
			const matchNote = tx.note?.toLowerCase().includes(q) ?? false;
			const matchAccount = tx.payment_method_name.toLowerCase().includes(q);
			return matchMerchant || matchNote || matchAccount;
		})
	);

	const sortedTransactions = $derived(
		[...filteredTransactions].sort((a, b) => {
			let cmp = 0;
			if (sortBy === 'date') {
				cmp = a.logged_date.localeCompare(b.logged_date);
			} else if (sortBy === 'merchant') {
				cmp = a.merchant.localeCompare(b.merchant);
			} else if (sortBy === 'account') {
				cmp = a.payment_method_name.localeCompare(b.payment_method_name);
			} else if (sortBy === 'amount') {
				const numA = typeof a.total === 'number' ? a.total : parseFloat(a.total) || 0;
				const numB = typeof b.total === 'number' ? b.total : parseFloat(b.total) || 0;
				cmp = numA - numB;
			}
			return sortOrder === 'asc' ? cmp : -cmp;
		})
	);

	// Paginated slice
	const totalItems = $derived(sortedTransactions.length);
	const totalPages = $derived(Math.max(1, Math.ceil(totalItems / pageSize)));
	const paginatedTransactions = $derived(
		sortedTransactions.slice((currentPage - 1) * pageSize, currentPage * pageSize)
	);

	// Count active applied filters
	const activeFilterCount = $derived(
		(data.filters.account ? 1 : 0) +
			(data.filters.envelope ? 1 : 0) +
			(data.filters.transaction_type ? 1 : 0) +
			(data.filters.include_reversed ? 1 : 0) +
			(data.filters.allTime ? 1 : 0)
	);

	// Keep activeTransaction synced with updated data when records are modified or reconciled
	$effect(() => {
		const current = activeTransaction;
		if (current && data.transactions) {
			const fresh = data.transactions.find((t) => t.id === current.id);
			if (
				fresh &&
				(fresh.is_reconciled !== current.is_reconciled ||
					fresh.merchant !== current.merchant ||
					fresh.note !== current.note ||
					fresh.logged_date !== current.logged_date)
			) {
				activeTransaction = fresh;
			}
		}
	});

	function openTransactionDetail(tx: TransactionItem) {
		activeTransaction = tx;
		isDrawerOpen = true;
	}

	function confirmDelete(tx: TransactionItem) {
		isDrawerOpen = false;
		transactionToDelete = tx;
		isDeleteModalOpen = true;
	}

	function handleQuickAddSplit(draft: {
		merchant: string;
		amount: string;
		logged_date: string;
		payment_method_name: string;
		envelope_name: string;
		note: string;
	}) {
		modalDraft = draft;
		isModalOpen = true;
	}

	function openNewModal() {
		modalDraft = null;
		isModalOpen = true;
	}
</script>

<svelte:head>
	<title>Transactions — Personal Budgeting</title>
</svelte:head>

<div class="space-y-5 pb-16">
	<!-- Page Header & Action Bar -->
	<div
		class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-4 border-b border-brand-200"
	>
		<div class="space-y-1">
			<div class="flex items-center gap-2.5 flex-wrap">
				<h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-brand-900 font-sans">
					Transactions
				</h1>
				<span
					class="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-brand-100 text-brand-800 border border-brand-200"
				>
					{totalItems} Listed
				</span>
				{#if data.filters.allTime}
					<span
						class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700"
					>
						All Time
					</span>
				{:else if data.filters.date_from && data.filters.date_to}
					<span
						class="text-xs font-mono text-brand-600 px-2 py-0.5 rounded-full bg-brand-50 border border-brand-200/80"
					>
						{data.filters.date_from} → {data.filters.date_to}
					</span>
				{/if}
			</div>
			<p class="text-brand-700 text-xs sm:text-sm leading-relaxed">
				Scannable financial ledger with multi-envelope splits, installment financing, and audit
				reversals.
			</p>
		</div>

		<!-- Action Controls -->
		<div class="flex items-center gap-2 flex-wrap">
			<!-- Instant Search Input -->
			<div class="relative flex-1 sm:w-56">
				<span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-brand-400 select-none">
					🔍
				</span>
				<input
					type="text"
					placeholder="Search merchant, memo..."
					bind:value={searchInput}
					class="w-full pl-7 pr-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 placeholder:text-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
				/>
			</div>

			<!-- Filters Toggle Button -->
			<button
				type="button"
				onclick={() => (isFilterOpen = !isFilterOpen)}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-300 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 transition-colors cursor-pointer shadow-2xs"
			>
				<span>⚙️ Filters</span>
				{#if activeFilterCount > 0}
					<span
						class="w-4 h-4 rounded-full bg-brand-500 text-brand-50 text-[10px] font-mono flex items-center justify-center font-bold"
					>
						{activeFilterCount}
					</span>
				{/if}
			</button>

			<!-- Mobile Select Toggle Button -->
			<button
				type="button"
				onclick={() => (isMobileSelectMode = !isMobileSelectMode)}
				class="sm:hidden inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-brand-300 bg-white text-brand-800 text-xs font-semibold cursor-pointer"
			>
				{isMobileSelectMode ? 'Cancel' : 'Select'}
			</button>

			<!-- Primary New Transaction Button -->
			<button
				type="button"
				onclick={openNewModal}
				class="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer"
			>
				<span>+ New Transaction</span>
			</button>
		</div>
	</div>

	<!-- Collapsible Filter Drawer -->
	<TransactionFilterDrawer
		open={isFilterOpen}
		accounts={data.accounts}
		categories={data.categories}
		filters={data.filters}
		onclose={() => (isFilterOpen = false)}
	/>

	<!-- Pinned Desktop Quick-Add Bar -->
	<div class="hidden sm:block">
		<TransactionQuickAdd
			formData={data.quickAddForm}
			accounts={data.accounts}
			categories={data.categories}
			onsplit={handleQuickAddSplit}
		/>
	</div>

	<!-- Ledger View: Desktop Table vs Mobile Cards -->
	{#if paginatedTransactions.length > 0}
		<!-- Desktop View -->
		<div class="hidden sm:block">
			<TransactionTable
				transactions={paginatedTransactions}
				bind:selectedIds
				bind:sortBy
				bind:sortOrder
				onselect={openTransactionDetail}
			/>
		</div>

		<!-- Mobile View -->
		<div class="sm:hidden">
			<TransactionCardList
				transactions={paginatedTransactions}
				bind:selectedIds
				bind:isSelectMode={isMobileSelectMode}
				onselect={openTransactionDetail}
			/>
		</div>

		<!-- Pagination Footer -->
		<div
			class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 text-xs text-brand-700"
		>
			<div class="flex items-center gap-2">
				<span>Show per page:</span>
				<select
					bind:value={pageSize}
					onchange={() => (currentPage = 1)}
					class="pl-2.5 pr-8 py-1 rounded-lg border border-brand-300 text-xs font-mono bg-white text-brand-900 cursor-pointer"
				>
					<option value={25}>25</option>
					<option value={50}>50</option>
					<option value={100}>100</option>
				</select>
				<span class="text-brand-500 font-mono">
					({(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalItems)} of {totalItems})
				</span>
			</div>

			<div class="flex items-center gap-1.5 font-mono">
				<button
					type="button"
					disabled={currentPage <= 1}
					onclick={() => currentPage--}
					class="px-2.5 py-1 rounded-lg border border-brand-300 bg-white hover:bg-brand-50 disabled:opacity-40 transition-colors cursor-pointer"
				>
					← Prev
				</button>
				<span class="px-2 font-bold text-brand-900">
					{currentPage} / {totalPages}
				</span>
				<button
					type="button"
					disabled={currentPage >= totalPages}
					onclick={() => currentPage++}
					class="px-2.5 py-1 rounded-lg border border-brand-300 bg-white hover:bg-brand-50 disabled:opacity-40 transition-colors cursor-pointer"
				>
					Next →
				</button>
			</div>
		</div>
	{:else}
		<!-- Zero / Empty State -->
		<div
			class="p-10 rounded-2xl border border-dashed border-brand-300 bg-brand-50/50 text-center space-y-3"
		>
			<div
				class="w-12 h-12 mx-auto rounded-2xl bg-brand-100 flex items-center justify-center text-xl"
			>
				🧾
			</div>
			<div class="space-y-1">
				<h3 class="text-base font-bold text-brand-900 font-sans">No transactions found</h3>
				<p class="text-xs text-brand-600 max-w-sm mx-auto">
					{searchInput
						? `No entries matched "${searchInput}". Try adjusting your search query.`
						: 'No transactions match the selected filters or date range.'}
				</p>
			</div>
			<div class="pt-2 flex justify-center gap-2">
				<button
					type="button"
					onclick={openNewModal}
					class="px-4 py-1.5 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors cursor-pointer"
				>
					+ Add First Transaction
				</button>
			</div>
		</div>
	{/if}
</div>

<!-- Slide-Over Detail Drawer -->
<TransactionDrawer
	open={isDrawerOpen}
	transaction={activeTransaction}
	updateFormData={data.updateForm}
	updateFinancedFormData={data.updateFinancedForm}
	accounts={data.accounts}
	categories={data.categories}
	onclose={() => (isDrawerOpen = false)}
	ondelete={confirmDelete}
/>

<!-- Unified New Transaction Modal (Expense with Split Builder + Financed) -->
<TransactionModal
	open={isModalOpen}
	expenseFormData={data.expenseForm}
	financedFormData={data.financedForm}
	accounts={data.accounts}
	categories={data.categories}
	draft={modalDraft}
	onclose={() => {
		isModalOpen = false;
		modalDraft = null;
	}}
/>

<!-- Accounting Reversal Confirmation Modal -->
<TransactionDeleteModal
	open={isDeleteModalOpen}
	formData={data.deleteForm}
	transaction={transactionToDelete}
	onclose={() => {
		isDeleteModalOpen = false;
		transactionToDelete = null;
	}}
/>

<!-- Floating Bulk Reconcile Action Bar -->
<TransactionBulkBar
	bind:selectedIds
	formData={data.bulkReconcileForm}
	onclear={() => (selectedIds = [])}
/>

<!-- Mobile Sticky Floating Action Button (FAB) -->
<div class="sm:hidden fixed bottom-6 right-6 z-30">
	<button
		type="button"
		onclick={openNewModal}
		class="w-12 h-12 rounded-full bg-brand-500 text-brand-50 shadow-lg flex items-center justify-center text-xl font-bold hover:bg-brand-600 active:scale-95 transition-all cursor-pointer"
		aria-label="Add transaction"
	>
		+
	</button>
</div>
