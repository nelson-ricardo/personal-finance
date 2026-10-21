<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { createExpenseSchema, createFinancedSchema } from '#lib/schemas/transaction.ts';
	import type { Account } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency, getLocalDateString } from '#lib/utils/formatters.ts';

	let {
		open = false,
		expenseFormData,
		financedFormData,
		accounts,
		categories,
		draft,
		onclose
	}: {
		open: boolean;
		expenseFormData: SuperValidated<Infer<typeof createExpenseSchema>>;
		financedFormData: SuperValidated<Infer<typeof createFinancedSchema>>;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		draft?: {
			merchant: string;
			amount: string;
			logged_date: string;
			payment_method_name: string;
			envelope_name: string;
			note: string;
		} | null;
		onclose: () => void;
	} = $props();

	let activeTab = $state<'expense' | 'financed'>('expense');

	// --- Expense Superform ---
	// svelte-ignore state_referenced_locally
	const {
		form: expenseForm,
		errors: expenseErrors,
		enhance: enhanceExpense,
		submitting: creatingExpense
	} = superForm(expenseFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	// --- Financed Superform ---
	// svelte-ignore state_referenced_locally
	const {
		form: financedForm,
		errors: financedErrors,
		enhance: enhanceFinanced,
		submitting: creatingFinanced
	} = superForm(financedFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	// Split allocations state for Expense tab
	let splits = $state<Array<{ envelope_name: string; amount: string }>>([
		{ envelope_name: '', amount: '' }
	]);

	const activeAccounts = $derived(
		accounts.filter(
			(a) => a.is_active && (a.account_type === 'cash' || a.account_type === 'credit_card')
		)
	);
	const creditCardAccounts = $derived(
		activeAccounts.filter((a) => a.account_type === 'credit_card')
	);
	const budgetingCategories = $derived(categories.filter((c) => c.name !== 'System'));

	const allActiveEnvelopes = $derived(
		budgetingCategories.flatMap((c) => c.envelopes).filter((e) => e.is_active)
	);

	// Sync draft when opened from QuickAdd "Split?" button
	$effect(() => {
		if (open && draft) {
			activeTab = 'expense';
			$expenseForm.merchant = draft.merchant || '';
			$expenseForm.logged_date = draft.logged_date || getLocalDateString();
			$expenseForm.payment_method_name =
				draft.payment_method_name || (activeAccounts[0]?.name ?? '');
			$expenseForm.note = draft.note || '';
			$expenseForm.total_amount = draft.amount || '';

			splits = [
				{
					envelope_name: draft.envelope_name || (allActiveEnvelopes[0]?.name ?? ''),
					amount: draft.amount || ''
				}
			];
		} else if (open) {
			if (!$expenseForm.logged_date) {
				$expenseForm.logged_date = getLocalDateString();
			}
			if (!$expenseForm.payment_method_name && activeAccounts.length > 0) {
				$expenseForm.payment_method_name = activeAccounts[0].name;
			}
			if (splits.length === 0 || !splits[0].envelope_name) {
				splits = [{ envelope_name: allActiveEnvelopes[0]?.name || '', amount: '' }];
			}

			if (!$financedForm.logged_date) {
				$financedForm.logged_date = getLocalDateString();
			}
			if (!$financedForm.payment_method_name && creditCardAccounts.length > 0) {
				$financedForm.payment_method_name = creditCardAccounts[0].name;
			}
		}
	});

	// Real-time split calculations
	const parsedTotal = $derived(parseFloat($expenseForm.total_amount || '0') || 0);
	const allocatedSum = $derived(
		splits.reduce((sum, s) => sum + (parseFloat(s.amount || '0') || 0), 0)
	);
	const remainingBalance = $derived(Math.round((parsedTotal - allocatedSum) * 100) / 100);
	const isSplitBalanced = $derived(parsedTotal > 0 && Math.abs(remainingBalance) < 0.005);

	// Financed monthly payment calculation
	const financedPrincipal = $derived(parseFloat($financedForm.amount || '0') || 0);
	const financedMonthlyPayment = $derived(
		$financedForm.term > 0 && financedPrincipal > 0
			? (financedPrincipal / $financedForm.term).toFixed(2)
			: '0.00'
	);

	function addSplitRow() {
		splits = [...splits, { envelope_name: allActiveEnvelopes[0]?.name || '', amount: '' }];
	}

	function removeSplitRow(index: number) {
		if (splits.length > 1) {
			splits = splits.filter((_, i) => i !== index);
		}
	}

	function assignRemainder(index: number) {
		if (remainingBalance > 0) {
			const currentVal = parseFloat(splits[index].amount || '0') || 0;
			splits[index].amount = (currentVal + remainingBalance).toFixed(2);
		}
	}

	// Keep splits_json updated for form submit
	$effect(() => {
		$expenseForm.splits_json = JSON.stringify(splits);
	});
</script>

<Modal
	{open}
	title={activeTab === 'expense' ? 'Record Expense' : 'Record Financed Purchase'}
	description="Track expenditures against your budgeting envelopes or record an installment purchase."
	{onclose}
>
	<!-- Tab Switcher -->
	<div class="flex items-center p-1 bg-brand-100/70 rounded-xl mb-4 border border-brand-200/50">
		<button
			type="button"
			onclick={() => (activeTab = 'expense')}
			class="flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer {activeTab ===
			'expense'
				? 'bg-white text-brand-900 shadow-xs'
				: 'text-brand-600 hover:text-brand-900'}"
		>
			Expense & Splits
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'financed')}
			class="flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer {activeTab ===
			'financed'
				? 'bg-white text-brand-900 shadow-xs'
				: 'text-brand-600 hover:text-brand-900'}"
		>
			Financed Purchase
		</button>
	</div>

	<!-- =================== EXPENSE TAB =================== -->
	{#if activeTab === 'expense'}
		{#if $expenseErrors._errors}
			<div
				class="p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1 mb-3"
			>
				{#each $expenseErrors._errors as err, idx (idx)}
					<p>• {err}</p>
				{/each}
			</div>
		{/if}

		<form method="POST" action="?/createExpense" use:enhanceExpense class="space-y-4">
			<input type="hidden" name="splits_json" bind:value={$expenseForm.splits_json} />

			<!-- Row 1: Total Amount & Merchant -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div>
					<label
						for="exp-total"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Total Amount ($)
					</label>
					<div class="relative">
						<span
							class="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono text-brand-500 select-none"
						>
							$
						</span>
						<input
							id="exp-total"
							name="total_amount"
							type="text"
							inputmode="decimal"
							placeholder="0.00"
							bind:value={$expenseForm.total_amount}
							class="w-full pl-7 pr-3 py-2 rounded-xl border border-brand-300 text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
						/>
					</div>
					{#if $expenseErrors.total_amount}
						<p class="text-xs text-[#6b1d2f] mt-1">{$expenseErrors.total_amount}</p>
					{/if}
				</div>

				<div>
					<label
						for="exp-merchant"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Merchant / Payee
					</label>
					<input
						id="exp-merchant"
						name="merchant"
						type="text"
						placeholder="e.g. Costco, Amazon"
						bind:value={$expenseForm.merchant}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-sm font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
					/>
					{#if $expenseErrors.merchant}
						<p class="text-xs text-[#6b1d2f] mt-1">{$expenseErrors.merchant}</p>
					{/if}
				</div>
			</div>

			<!-- Row 2: Account & Date -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div>
					<label
						for="exp-account"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Payment Method
					</label>
					<select
						id="exp-account"
						name="payment_method_name"
						bind:value={$expenseForm.payment_method_name}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-sm font-sans text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
					>
						{#each activeAccounts as acct (acct.id)}
							<option value={acct.name}>
								{acct.name} ({acct.account_type === 'cash' ? 'Cash' : 'Credit Card'})
							</option>
						{/each}
					</select>
					{#if $expenseErrors.payment_method_name}
						<p class="text-xs text-[#6b1d2f] mt-1">{$expenseErrors.payment_method_name}</p>
					{/if}
				</div>

				<div>
					<label
						for="exp-date"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Transaction Date
					</label>
					<input
						id="exp-date"
						name="logged_date"
						type="date"
						bind:value={$expenseForm.logged_date}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-sm font-mono text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
					/>
				</div>
			</div>

			<!-- Envelope Split Allocations Builder -->
			<div class="pt-2 border-t border-brand-200">
				<div class="flex items-center justify-between mb-2">
					<span class="text-xs font-bold text-brand-800 uppercase tracking-wider">
						Envelope Split Allocations
					</span>
					<button
						type="button"
						onclick={addSplitRow}
						class="text-xs font-semibold text-brand-600 hover:text-brand-900 transition-colors cursor-pointer"
					>
						+ Add Envelope Split
					</button>
				</div>

				<!-- Live Balance Counter Banner -->
				<div
					class="p-2.5 rounded-xl border text-xs font-medium flex items-center justify-between mb-3 {isSplitBalanced
						? 'bg-emerald-50/80 border-emerald-300 text-emerald-900'
						: remainingBalance > 0
							? 'bg-amber-50/80 border-amber-300 text-amber-900'
							: 'bg-[#6b1d2f]/10 border-[#6b1d2f]/20 text-[#6b1d2f]'}"
				>
					<div class="flex items-center gap-2">
						<span class="font-mono tabular-nums">
							Total: {formatCurrency(parsedTotal)}
						</span>
						<span>•</span>
						<span class="font-mono tabular-nums">
							Allocated: {formatCurrency(allocatedSum)}
						</span>
					</div>

					<div class="flex items-center gap-1.5 font-mono">
						{#if isSplitBalanced}
							<span class="font-bold text-emerald-700">✓ Balanced</span>
						{:else if remainingBalance > 0}
							<span>Remaining:</span>
							<span class="font-bold">{formatCurrency(remainingBalance)}</span>
						{:else}
							<span>Over:</span>
							<span class="font-bold">{formatCurrency(Math.abs(remainingBalance))}</span>
						{/if}
					</div>
				</div>

				<!-- Split Rows -->
				<div class="space-y-2 max-h-48 overflow-y-auto pr-1">
					{#each splits as split, idx (idx)}
						<div class="flex items-center gap-2">
							<div class="flex-1">
								<select
									bind:value={split.envelope_name}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
								>
									{#each budgetingCategories as cat (cat.id)}
										<optgroup label={cat.name}>
											{#each cat.envelopes.filter((e) => e.is_active) as env (env.id)}
												<option value={env.name}>{env.name}</option>
											{/each}
										</optgroup>
									{/each}
								</select>
							</div>

							<div class="w-32 relative">
								<span
									class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-mono text-brand-500 select-none"
								>
									$
								</span>
								<input
									type="text"
									inputmode="decimal"
									placeholder="0.00"
									bind:value={split.amount}
									class="w-full pl-6 pr-2 py-1.5 rounded-xl border border-brand-300 text-xs font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
								/>
							</div>

							{#if remainingBalance > 0}
								<button
									type="button"
									onclick={() => assignRemainder(idx)}
									title="Assign remaining balance to this split"
									class="px-2 py-1 text-[11px] rounded-lg bg-brand-100 hover:bg-brand-200 text-brand-800 font-semibold cursor-pointer transition-colors whitespace-nowrap"
								>
									Fill Rest
								</button>
							{/if}

							{#if splits.length > 1}
								<button
									type="button"
									onclick={() => removeSplitRow(idx)}
									class="p-1 text-brand-400 hover:text-[#6b1d2f] rounded-lg transition-colors cursor-pointer"
									title="Remove split"
								>
									✕
								</button>
							{/if}
						</div>
					{/each}
				</div>
				{#if $expenseErrors.splits_json}
					<p class="text-xs text-[#6b1d2f] mt-1">{$expenseErrors.splits_json}</p>
				{/if}
			</div>

			<!-- Note & Reconciliation status -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
				<div>
					<label
						for="exp-note"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Note (Optional)
					</label>
					<input
						id="exp-note"
						name="note"
						type="text"
						placeholder="Receipt notes, tags..."
						bind:value={$expenseForm.note}
						class="w-full px-3 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
				</div>

				<div class="flex items-center pt-5">
					<label class="flex items-center gap-2 text-xs font-medium text-brand-800 cursor-pointer">
						<input
							type="checkbox"
							name="is_reconciled"
							bind:checked={$expenseForm.is_reconciled}
							class="w-4 h-4 rounded text-brand-600 border-brand-300 focus:ring-brand-500 cursor-pointer"
						/>
						<span>Mark as Reconciled / Cleared</span>
					</label>
				</div>
			</div>

			<!-- Submit & Cancel -->
			<div class="flex items-center justify-end gap-2 pt-3 border-t border-brand-100">
				<button
					type="button"
					onclick={onclose}
					class="px-4 py-2 rounded-xl text-xs font-semibold text-brand-700 hover:bg-brand-100/60 transition-colors cursor-pointer"
				>
					Cancel
				</button>
				<button
					type="submit"
					disabled={$creatingExpense}
					class="px-5 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs flex items-center justify-center cursor-pointer"
				>
					{#if $creatingExpense}
						<span
							class="w-3.5 h-3.5 border-2 border-brand-50 border-t-transparent rounded-full animate-spin"
						></span>
					{:else}
						Create Expense
					{/if}
				</button>
			</div>
		</form>
	{:else}
		<!-- =================== FINANCED PURCHASE TAB =================== -->
		{#if $financedErrors._errors}
			<div
				class="p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1 mb-3"
			>
				{#each $financedErrors._errors as err, idx (idx)}
					<p>• {err}</p>
				{/each}
			</div>
		{/if}

		<form method="POST" action="?/createFinanced" use:enhanceFinanced class="space-y-4">
			<!-- Row 1: Merchant & Principal Amount -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div>
					<label
						for="fin-merchant"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Merchant / Payee
					</label>
					<input
						id="fin-merchant"
						name="merchant"
						type="text"
						placeholder="e.g. Apple, Best Buy"
						bind:value={$financedForm.merchant}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-sm font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
					{#if $financedErrors.merchant}
						<p class="text-xs text-[#6b1d2f] mt-1">{$financedErrors.merchant}</p>
					{/if}
				</div>

				<div>
					<label
						for="fin-amount"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Total Principal Amount ($)
					</label>
					<div class="relative">
						<span
							class="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-mono text-brand-500 select-none"
						>
							$
						</span>
						<input
							id="fin-amount"
							name="amount"
							type="text"
							inputmode="decimal"
							placeholder="1200.00"
							bind:value={$financedForm.amount}
							class="w-full pl-7 pr-3 py-2 rounded-xl border border-brand-300 text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
						/>
					</div>
					{#if $financedErrors.amount}
						<p class="text-xs text-[#6b1d2f] mt-1">{$financedErrors.amount}</p>
					{/if}
				</div>
			</div>

			<!-- Row 2: Credit Card & Term -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div>
					<label
						for="fin-account"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Credit Card Account
					</label>
					<select
						id="fin-account"
						name="payment_method_name"
						bind:value={$financedForm.payment_method_name}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-sm font-sans text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						{#if creditCardAccounts.length === 0}
							{#each activeAccounts as acct (acct.id)}
								<option value={acct.name}>{acct.name}</option>
							{/each}
						{:else}
							{#each creditCardAccounts as acct (acct.id)}
								<option value={acct.name}>{acct.name}</option>
							{/each}
						{/if}
					</select>
					{#if $financedErrors.payment_method_name}
						<p class="text-xs text-[#6b1d2f] mt-1">{$financedErrors.payment_method_name}</p>
					{/if}
				</div>

				<div>
					<label
						for="fin-term"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Financing Term (Months)
					</label>
					<div class="space-y-1.5">
						<div class="relative">
							<input
								id="fin-term"
								name="term"
								type="number"
								min="1"
								max="120"
								step="1"
								placeholder="e.g. 12"
								bind:value={$financedForm.term}
								class="w-full pl-3 pr-16 py-2 rounded-xl border border-brand-300 text-sm font-mono tabular-nums text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
							/>
							<span
								class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-sans text-brand-500 select-none"
							>
								months
							</span>
						</div>
						<div class="flex flex-wrap gap-1">
							{#each [3, 6, 12, 18, 24, 36] as preset (preset)}
								<button
									type="button"
									onclick={() => ($financedForm.term = preset)}
									class="px-2 py-0.5 rounded-lg text-[11px] font-mono transition-colors border {$financedForm.term ===
									preset
										? 'bg-brand-500 text-brand-50 border-brand-500 font-bold'
										: 'bg-brand-50 text-brand-700 border-brand-200 hover:bg-brand-100 cursor-pointer'}"
								>
									{preset}mo
								</button>
							{/each}
						</div>
					</div>
					{#if $financedErrors.term}
						<p class="text-xs text-[#6b1d2f] mt-1">{$financedErrors.term}</p>
					{/if}
				</div>
			</div>

			<!-- Dynamic Monthly Installment Banner -->
			<div
				class="p-3 rounded-xl bg-brand-50 border border-brand-200 text-brand-900 flex items-center justify-between"
			>
				<div>
					<span class="block text-[11px] font-bold text-brand-600 uppercase tracking-wider">
						Calculated Monthly Payment
					</span>
					<span class="text-base font-bold font-mono tabular-nums text-brand-900">
						${financedMonthlyPayment} / mo
					</span>
				</div>
				<div class="text-right text-xs text-brand-600 font-mono">
					<span>Term: {$financedForm.term || 1} installments</span>
				</div>
			</div>

			<!-- Optional Custom Envelope Name (Backend auto-generates if empty!) -->
			<div>
				<label
					for="fin-envelope"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Custom Envelope Name (Optional)
				</label>
				<input
					id="fin-envelope"
					name="envelope_name"
					type="text"
					placeholder={`Leave blank to auto-generate: ${$financedForm.merchant?.trim() || 'Merchant'} - ${$financedForm.term || 12}`}
					bind:value={$financedForm.envelope_name}
					class="w-full px-3 py-2 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
				/>
				<p class="text-[11px] text-brand-500 mt-1">
					If left empty, the backend automatically creates an envelope named "{$financedForm.merchant?.trim() ||
						'Merchant'} - {$financedForm.term || 12}".
				</p>
			</div>

			<!-- Date & Note -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div>
					<label
						for="fin-date"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Purchase Date
					</label>
					<input
						id="fin-date"
						name="logged_date"
						type="date"
						bind:value={$financedForm.logged_date}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-xs font-mono text-brand-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
				</div>

				<div>
					<label
						for="fin-note"
						class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Note (Optional)
					</label>
					<input
						id="fin-note"
						name="note"
						type="text"
						placeholder="Item description, warranty..."
						bind:value={$financedForm.note}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
				</div>
			</div>

			<!-- Submit & Cancel -->
			<div class="flex items-center justify-end gap-2 pt-3 border-t border-brand-100">
				<button
					type="button"
					onclick={onclose}
					class="px-4 py-2 rounded-xl text-xs font-semibold text-brand-700 hover:bg-brand-100/60 transition-colors cursor-pointer"
				>
					Cancel
				</button>
				<button
					type="submit"
					disabled={$creatingFinanced}
					class="px-5 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs flex items-center justify-center cursor-pointer"
				>
					{#if $creatingFinanced}
						<span
							class="w-3.5 h-3.5 border-2 border-brand-50 border-t-transparent rounded-full animate-spin"
						></span>
					{:else}
						Create Financed Purchase
					{/if}
				</button>
			</div>
		</form>
	{/if}
</Modal>
