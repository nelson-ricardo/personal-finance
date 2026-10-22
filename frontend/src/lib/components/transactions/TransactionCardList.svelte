<script lang="ts">
	import type { TransactionItem } from '#lib/schemas/transaction.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		transactions,
		selectedIds = $bindable([]),
		isSelectMode = $bindable(false),
		onselect
	}: {
		transactions: TransactionItem[];
		selectedIds: number[];
		isSelectMode: boolean;
		onselect: (tx: TransactionItem) => void;
	} = $props();

	function toggleSelect(id: number, e: MouseEvent) {
		e.stopPropagation();
		if (selectedIds.includes(id)) {
			selectedIds = selectedIds.filter((item) => item !== id);
		} else {
			selectedIds = [...selectedIds, id];
		}
	}
</script>

<div class="space-y-2.5">
	{#each transactions as tx (tx.id)}
		{@const isSelected = selectedIds.includes(tx.id)}
		{@const isReversal = tx.transaction_type === 'REVERSAL'}
		{@const isFinanced = tx.transaction_type === 'FINANCED'}
		{@const isIncome = tx.transaction_type === 'INCOME'}

		<div
			onclick={() => {
				if (isSelectMode) {
					toggleSelect(tx.id, {} as MouseEvent);
				} else {
					onselect(tx);
				}
			}}
			role="button"
			tabindex="0"
			onkeydown={(e) => {
				if (e.key === 'Enter') onselect(tx);
			}}
			class="bg-white rounded-2xl border p-3.5 shadow-xs transition-all active:scale-[0.99] cursor-pointer {isSelected
				? 'border-brand-500 bg-brand-50/60'
				: 'border-brand-200/80 hover:border-brand-300'}"
		>
			<div class="flex items-start justify-between gap-3">
				<!-- Left: Select Checkbox (if in select mode) + Merchant + Account -->
				<div class="flex items-start gap-2.5 min-w-0">
					{#if isSelectMode}
						<input
							type="checkbox"
							checked={isSelected}
							onclick={(e) => e.stopPropagation()}
							onchange={(e) => toggleSelect(tx.id, e as unknown as MouseEvent)}
							class="w-4 h-4 mt-0.5 rounded text-brand-600 border-brand-300 focus:ring-brand-500 cursor-pointer"
						/>
					{/if}

					<div class="min-w-0">
						<h4
							class="text-sm font-bold text-brand-900 truncate font-sans {isReversal
								? 'line-through text-brand-500'
								: ''}"
						>
							{tx.merchant}
						</h4>

						<div class="flex items-center gap-1.5 mt-1">
							<span
								class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-brand-100 text-brand-800"
							>
								{#if tx.destination_account_name}
									<span>{tx.payment_method_name}</span>
									<span class="text-brand-400">→</span>
									<span class="font-semibold text-brand-950">{tx.destination_account_name}</span>
								{:else}
									<span>{tx.payment_method_name}</span>
								{/if}
							</span>

							{#if isFinanced}
								<span
									class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800"
								>
									Financed
								</span>
							{:else if isReversal}
								<span
									class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#6b1d2f]/10 text-[#6b1d2f]"
								>
									Reversal
								</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Right: Amount + Status -->
				<div class="text-right whitespace-nowrap">
					<div
						class="text-sm font-bold font-mono tabular-nums {isReversal
							? 'line-through text-brand-400'
							: isIncome
								? 'text-emerald-700'
								: 'text-brand-900'}"
					>
						{isIncome ? '+' : '-'}{formatCurrency(tx.total)}
					</div>

					<div class="mt-1 flex items-center justify-end gap-1">
						{#if tx.is_reconciled}
							<span class="text-[10px] font-semibold text-emerald-700">✓ Cleared</span>
						{:else}
							<span class="text-[10px] font-semibold text-amber-700">⏳ Pending</span>
						{/if}
					</div>
				</div>
			</div>

			<!-- Bottom Row: Date & Note -->
			<div
				class="mt-2.5 pt-2 border-t border-brand-100 flex items-center justify-between text-[11px] text-brand-500 font-mono"
			>
				<span>{tx.logged_date}</span>
				{#if tx.note}
					<span class="text-brand-600 truncate max-w-[180px] font-sans">{tx.note}</span>
				{/if}
			</div>
		</div>
	{/each}
</div>
