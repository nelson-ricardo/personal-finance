<script lang="ts">
	import type { TransactionItem } from '#lib/schemas/transaction.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		transactions,
		selectedIds = $bindable([]),
		sortBy = $bindable('date'),
		sortOrder = $bindable('desc'),
		onselect
	}: {
		transactions: TransactionItem[];
		selectedIds: number[];
		sortBy: 'date' | 'merchant' | 'account' | 'amount';
		sortOrder: 'asc' | 'desc';
		onselect: (tx: TransactionItem) => void;
	} = $props();

	function toggleSelectAll() {
		if (selectedIds.length === transactions.length) {
			selectedIds = [];
		} else {
			selectedIds = transactions.map((t) => t.id);
		}
	}

	function toggleSelectOne(id: number, e: MouseEvent) {
		e.stopPropagation();
		if (selectedIds.includes(id)) {
			selectedIds = selectedIds.filter((item) => item !== id);
		} else {
			selectedIds = [...selectedIds, id];
		}
	}

	function handleSort(column: 'date' | 'merchant' | 'account' | 'amount') {
		if (sortBy === column) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = column;
			sortOrder = 'desc';
		}
	}

	// Calculate monthly payment if financed
	function getMonthlyEstimate(tx: TransactionItem): string | null {
		if (tx.transaction_type !== 'FINANCED') return null;
		const total = typeof tx.total === 'number' ? tx.total : parseFloat(tx.total);
		if (isNaN(total)) return null;
		// Estimate standard 12 mo term if not in summary schema
		const mo = (total / 12).toFixed(2);
		return `$${mo}/mo`;
	}
</script>

<div class="overflow-x-auto rounded-2xl border border-brand-200/80 shadow-xs bg-white">
	<table class="w-full text-left border-collapse">
		<thead>
			<tr
				class="border-b border-brand-200 bg-brand-50/80 text-[11px] font-bold text-brand-700 uppercase tracking-wider select-none"
			>
				<!-- Checkbox -->
				<th class="py-3 px-3.5 w-10 text-center">
					<input
						type="checkbox"
						checked={transactions.length > 0 && selectedIds.length === transactions.length}
						onchange={toggleSelectAll}
						class="w-4 h-4 rounded text-brand-600 border-brand-300 focus:ring-brand-500 cursor-pointer"
						aria-label="Select all transactions"
					/>
				</th>

				<!-- Date -->
				<th
					onclick={() => handleSort('date')}
					class="py-3 px-3 cursor-pointer hover:text-brand-900 transition-colors"
				>
					<div class="flex items-center gap-1">
						<span>Date</span>
						{#if sortBy === 'date'}
							<span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
						{/if}
					</div>
				</th>

				<!-- Merchant & Note -->
				<th
					onclick={() => handleSort('merchant')}
					class="py-3 px-4 cursor-pointer hover:text-brand-900 transition-colors"
				>
					<div class="flex items-center gap-1">
						<span>Merchant / Payee</span>
						{#if sortBy === 'merchant'}
							<span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
						{/if}
					</div>
				</th>

				<!-- Account -->
				<th
					onclick={() => handleSort('account')}
					class="py-3 px-3 cursor-pointer hover:text-brand-900 transition-colors"
				>
					<div class="flex items-center gap-1">
						<span>Account</span>
						{#if sortBy === 'account'}
							<span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
						{/if}
					</div>
				</th>

				<!-- Type & Reconciled -->
				<th class="py-3 px-3">Status</th>

				<!-- Amount -->
				<th
					onclick={() => handleSort('amount')}
					class="py-3 px-4 text-right cursor-pointer hover:text-brand-900 transition-colors"
				>
					<div class="flex items-center justify-end gap-1">
						<span>Amount</span>
						{#if sortBy === 'amount'}
							<span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
						{/if}
					</div>
				</th>

				<!-- Actions -->
				<th class="py-3 px-3 text-right w-16"></th>
			</tr>
		</thead>

		<tbody class="divide-y divide-brand-100 text-xs">
			{#each transactions as tx (tx.id)}
				{@const isSelected = selectedIds.includes(tx.id)}
				{@const isReversal = tx.transaction_type === 'REVERSAL'}
				{@const isFinanced = tx.transaction_type === 'FINANCED'}
				{@const isIncome = tx.transaction_type === 'INCOME'}
				{@const monthlyEst = getMonthlyEstimate(tx)}

				<tr
					onclick={() => onselect(tx)}
					class="transition-colors cursor-pointer group {isSelected
						? 'bg-brand-100/50'
						: isReversal
							? 'bg-rose-50/40 text-brand-500'
							: 'hover:bg-brand-50/60'}"
				>
					<!-- Checkbox -->
					<td class="py-3 px-3.5 text-center" onclick={(e) => e.stopPropagation()}>
						<input
							type="checkbox"
							checked={isSelected}
							onchange={(e) => toggleSelectOne(tx.id, e as unknown as MouseEvent)}
							class="w-4 h-4 rounded text-brand-600 border-brand-300 focus:ring-brand-500 cursor-pointer"
							aria-label="Select transaction"
						/>
					</td>

					<!-- Date -->
					<td class="py-3 px-3 font-mono text-brand-700 whitespace-nowrap">
						{tx.logged_date}
					</td>

					<!-- Merchant & Note -->
					<td class="py-3 px-4">
						<div class="flex flex-col">
							<span
								class="font-semibold text-brand-900 {isReversal
									? 'line-through text-brand-500'
									: ''}"
							>
								{tx.merchant}
							</span>
							{#if tx.note}
								<span class="text-[11px] text-brand-500 truncate max-w-xs">{tx.note}</span>
							{/if}
						</div>
					</td>

					<!-- Account -->
					<td class="py-3 px-3 whitespace-nowrap">
						<span
							class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-brand-100 text-brand-800"
						>
							{tx.payment_method_name}
						</span>
					</td>

					<!-- Status & Type -->
					<td class="py-3 px-3 whitespace-nowrap">
						<div class="flex items-center gap-1.5">
							{#if isReversal}
								<span
									class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#6b1d2f]/10 text-[#6b1d2f]"
								>
									REVERSAL
								</span>
							{:else if isFinanced}
								<span
									class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800"
								>
									FINANCED
								</span>
							{:else if isIncome}
								<span
									class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800"
								>
									INCOME
								</span>
							{/if}

							{#if tx.is_reconciled}
								<span
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200"
									title="Reconciled / Cleared"
								>
									✓ Cleared
								</span>
							{:else}
								<span
									class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold text-amber-800 bg-amber-50 border border-amber-200"
									title="Pending Clearance"
								>
									⏳ Pending
								</span>
							{/if}
						</div>
					</td>

					<!-- Amount -->
					<td class="py-3 px-4 text-right whitespace-nowrap">
						<div class="flex flex-col items-end">
							<span
								class="font-mono tabular-nums font-bold text-sm {isReversal
									? 'line-through text-brand-400'
									: isIncome
										? 'text-emerald-700'
										: 'text-brand-900'}"
							>
								{isIncome ? '+' : '-'}{formatCurrency(tx.total)}
							</span>
							{#if monthlyEst}
								<span class="text-[10px] font-mono text-purple-700">
									est. {monthlyEst}
								</span>
							{/if}
						</div>
					</td>

					<!-- Inspect Action -->
					<td class="py-3 px-3 text-right">
						<span
							class="text-brand-400 group-hover:text-brand-700 transition-colors text-xs font-semibold"
						>
							→
						</span>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
