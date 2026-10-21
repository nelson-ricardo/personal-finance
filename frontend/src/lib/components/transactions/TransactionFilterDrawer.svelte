<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import type { Account } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import type { ResolvedPathname } from '$app/types';
	import { getLocalDateString } from '#lib/utils/formatters.ts';

	let {
		open = false,
		accounts,
		categories,
		filters,
		onclose
	}: {
		open: boolean;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		filters: {
			date_from: string | null;
			date_to: string | null;
			allTime: boolean;
			account: string | null;
			envelope: string | null;
			transaction_type: string | null;
			include_reversed: boolean;
		};
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	let selectedDateFrom = $state(filters.date_from || '');
	// svelte-ignore state_referenced_locally
	let selectedDateTo = $state(filters.date_to || '');
	// svelte-ignore state_referenced_locally
	let isAllTime = $state(filters.allTime);
	// svelte-ignore state_referenced_locally
	let selectedAccount = $state(filters.account || '');
	// svelte-ignore state_referenced_locally
	let selectedEnvelope = $state(filters.envelope || '');
	// svelte-ignore state_referenced_locally
	let selectedType = $state(filters.transaction_type || '');
	// svelte-ignore state_referenced_locally
	let showReversed = $state(filters.include_reversed);

	$effect(() => {
		selectedDateFrom = filters.date_from || '';
		selectedDateTo = filters.date_to || '';
		isAllTime = filters.allTime;
		selectedAccount = filters.account || '';
		selectedEnvelope = filters.envelope || '';
		selectedType = filters.transaction_type || '';
		showReversed = filters.include_reversed;
	});

	function applyPreset(preset: 'this-month' | 'last-month' | 'last-30' | 'all-time') {
		const now = new Date();
		const year = now.getFullYear();
		const month = now.getMonth(); // 0-based

		if (preset === 'this-month') {
			isAllTime = false;
			selectedDateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`;
			selectedDateTo = getLocalDateString(now);
		} else if (preset === 'last-month') {
			isAllTime = false;
			const lastMonthDate = new Date(year, month - 1, 1);
			const lastMonthEnd = new Date(year, month, 0); // last day of prev month
			selectedDateFrom = getLocalDateString(lastMonthDate);
			selectedDateTo = getLocalDateString(lastMonthEnd);
		} else if (preset === 'last-30') {
			isAllTime = false;
			const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
			selectedDateFrom = getLocalDateString(thirtyDaysAgo);
			selectedDateTo = getLocalDateString(now);
		} else if (preset === 'all-time') {
			isAllTime = true;
			selectedDateFrom = '';
			selectedDateTo = '';
		}
	}

	function handleApply() {
		const url = new URL(page.url.href);

		if (isAllTime) {
			url.searchParams.set('all_time', 'true');
			url.searchParams.delete('date_from');
			url.searchParams.delete('date_to');
		} else {
			url.searchParams.delete('all_time');
			if (selectedDateFrom) url.searchParams.set('date_from', selectedDateFrom);
			else url.searchParams.delete('date_from');
			if (selectedDateTo) url.searchParams.set('date_to', selectedDateTo);
			else url.searchParams.delete('date_to');
		}

		if (selectedAccount) url.searchParams.set('account', selectedAccount);
		else url.searchParams.delete('account');

		if (selectedEnvelope) url.searchParams.set('envelope', selectedEnvelope);
		else url.searchParams.delete('envelope');

		if (selectedType) url.searchParams.set('transaction_type', selectedType);
		else url.searchParams.delete('transaction_type');

		if (showReversed) url.searchParams.set('include_reversed', 'true');
		else url.searchParams.delete('include_reversed');

		const targetUrl =
			`${resolve('/transactions')}?${url.searchParams.toString()}` as unknown as ResolvedPathname;
		goto(targetUrl, { reset: false, replace: true });
		onclose();
	}

	function handleReset() {
		applyPreset('this-month');
		selectedAccount = '';
		selectedEnvelope = '';
		selectedType = '';
		showReversed = false;

		const targetUrl = resolve('/transactions');
		goto(targetUrl, { reset: false, replace: true });
		onclose();
	}
</script>

{#if open}
	<div
		class="bg-brand-50/70 border border-brand-200 rounded-2xl p-4 sm:p-5 mb-5 shadow-xs animate-in slide-in-from-top-2 duration-150"
	>
		<div class="flex items-center justify-between border-b border-brand-200/80 pb-3 mb-4">
			<div class="flex items-center gap-2">
				<span class="text-sm">🔍</span>
				<h3 class="text-sm font-bold text-brand-900 font-sans">Advanced Filters</h3>
			</div>
			<div class="flex items-center gap-2">
				<button
					type="button"
					onclick={handleReset}
					class="text-xs font-semibold text-brand-600 hover:text-brand-900 transition-colors cursor-pointer"
				>
					Reset Defaults
				</button>
				<button
					type="button"
					onclick={onclose}
					class="p-1 text-brand-500 hover:text-brand-800 rounded-lg hover:bg-brand-200/50 transition-colors cursor-pointer"
					aria-label="Close filters"
				>
					✕
				</button>
			</div>
		</div>

		<div class="space-y-4">
			<!-- Date Presets & Custom Pickers -->
			<div>
				<span class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-2">
					Date Range Preset
				</span>
				<div class="flex flex-wrap gap-1.5 mb-2.5">
					<button
						type="button"
						onclick={() => applyPreset('this-month')}
						class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer border {selectedDateFrom &&
						!isAllTime &&
						selectedDateFrom.endsWith('-01')
							? 'bg-brand-500 text-brand-50 border-brand-500'
							: 'bg-white text-brand-700 border-brand-200 hover:bg-brand-100/60'}"
					>
						This Month
					</button>
					<button
						type="button"
						onclick={() => applyPreset('last-month')}
						class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer border bg-white text-brand-700 border-brand-200 hover:bg-brand-100/60"
					>
						Last Month
					</button>
					<button
						type="button"
						onclick={() => applyPreset('last-30')}
						class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer border bg-white text-brand-700 border-brand-200 hover:bg-brand-100/60"
					>
						Last 30 Days
					</button>
					<button
						type="button"
						onclick={() => applyPreset('all-time')}
						class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer border {isAllTime
							? 'bg-brand-500 text-brand-50 border-brand-500'
							: 'bg-white text-brand-700 border-brand-200 hover:bg-brand-100/60'}"
					>
						All Time
					</button>
				</div>

				{#if !isAllTime}
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						<div>
							<span class="block text-[11px] font-medium text-brand-600 mb-1">From Date</span>
							<input
								type="date"
								bind:value={selectedDateFrom}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-mono text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
							/>
						</div>
						<div>
							<span class="block text-[11px] font-medium text-brand-600 mb-1">To Date</span>
							<input
								type="date"
								bind:value={selectedDateTo}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-mono text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
							/>
						</div>
					</div>
				{/if}
			</div>

			<!-- Selectors Grid -->
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
				<!-- Account -->
				<div>
					<label
						for="filter-account"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Account
					</label>
					<select
						id="filter-account"
						bind:value={selectedAccount}
						class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						<option value="">All Accounts</option>
						{#each accounts as acct (acct.id)}
							<option value={acct.name}>{acct.name}</option>
						{/each}
					</select>
				</div>

				<!-- Envelope -->
				<div>
					<label
						for="filter-envelope"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Envelope
					</label>
					<select
						id="filter-envelope"
						bind:value={selectedEnvelope}
						class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						<option value="">All Envelopes</option>
						{#each categories.filter((c) => c.name !== 'System') as cat (cat.id)}
							<optgroup label={cat.name}>
								{#each cat.envelopes as env (env.id)}
									<option value={env.name}>{env.name}</option>
								{/each}
							</optgroup>
						{/each}
					</select>
				</div>

				<!-- Type -->
				<div>
					<label
						for="filter-type"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Transaction Type
					</label>
					<select
						id="filter-type"
						bind:value={selectedType}
						class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						<option value="">All Types</option>
						<option value="EXPENSE">Expense</option>
						<option value="FINANCED">Financed</option>
						<option value="INCOME">Income</option>
						<option value="TRANSFER">Transfer</option>
						<option value="REVERSAL">Reversal</option>
					</select>
				</div>
			</div>

			<!-- Reversals Checkbox -->
			<div class="pt-2 border-t border-brand-200/60 flex items-center justify-between">
				<label class="flex items-center gap-2 text-xs font-medium text-brand-800 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={showReversed}
						class="w-4 h-4 rounded text-brand-600 border-brand-300 focus:ring-brand-500 cursor-pointer"
					/>
					<span>Show Reversed Transactions (Audit Trail)</span>
				</label>

				<div class="flex items-center gap-2">
					<button
						type="button"
						onclick={handleApply}
						class="px-4 py-1.5 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer"
					>
						Apply Filters
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
