<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type {
		updateTransactionSchema,
		updateFinancedSchema,
		TransactionItem,
		TransactionDetail
	} from '#lib/schemas/transaction.ts';
	import type { Account } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		transaction,
		updateFormData,
		updateFinancedFormData,
		accounts,
		categories,
		onclose,
		ondelete
	}: {
		open: boolean;
		transaction: TransactionItem | null;
		updateFormData: SuperValidated<Infer<typeof updateTransactionSchema>>;
		updateFinancedFormData: SuperValidated<Infer<typeof updateFinancedSchema>>;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		onclose: () => void;
		ondelete: (tx: TransactionItem) => void;
	} = $props();

	let isEditing = $state(false);
	let detailData = $state<TransactionDetail | null>(null);
	let isLoadingDetail = $state(false);

	// Regular update superform
	// svelte-ignore state_referenced_locally
	const {
		form: regForm,
		errors: regErrors,
		enhance: enhanceReg,
		submitting: savingReg
	} = superForm(updateFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				isEditing = false;
				onclose();
			}
		}
	});

	// Financed update superform
	// svelte-ignore state_referenced_locally
	const {
		form: finForm,
		errors: finErrors,
		enhance: enhanceFin,
		submitting: savingFin
	} = superForm(updateFinancedFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				isEditing = false;
				onclose();
			}
		}
	});

	// Split allocations state for editing regular transaction
	let editSplits = $state<Array<{ envelope_name: string; amount: string }>>([]);

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

	function isCcBalancingSplit(split: {
		envelope_name: string;
		envelope_id?: number | null;
	}): boolean {
		if (
			split.envelope_name === 'Credit Card Payment' ||
			split.envelope_name.startsWith('Credit Card Payment')
		) {
			return true;
		}
		const currentAccount = accounts.find((a) => a.name === transaction?.payment_method_name);
		if (currentAccount?.envelope_id && split.envelope_id === currentAccount.envelope_id) {
			return true;
		}
		return false;
	}

	const userSplits = $derived((detailData?.splits || []).filter((s) => !isCcBalancingSplit(s)));
	const ccBalancingSplits = $derived(
		(detailData?.splits || []).filter((s) => isCcBalancingSplit(s))
	);

	// Fetch detail when transaction changes
	let lastLoadedId = $state<number | null>(null);

	$effect(() => {
		if (open && transaction) {
			if (lastLoadedId !== transaction.id) {
				lastLoadedId = transaction.id;
				isEditing = false;
				isLoadingDetail = true;
				fetch(`/api/transactions/${transaction.id}`)
					.then((res) => {
						if (!res.ok) throw new Error('Failed to load transaction detail');
						return res.json();
					})
					.then((data: TransactionDetail) => {
						detailData = data;
						isLoadingDetail = false;

						// Sync edit forms
						if (transaction.transaction_type === 'FINANCED') {
							$finForm.id = data.id;
							$finForm.merchant = data.merchant;
							$finForm.logged_date = data.logged_date;
							$finForm.posted_date = data.posted_date || '';
							$finForm.payment_method_name = data.payment_method_name;
							$finForm.amount = String(data.total);
							$finForm.term = 12; // default if not provided
							$finForm.note = data.note || '';
							$finForm.is_reconciled = data.is_reconciled || false;
							$finForm.was_reconciled = data.is_reconciled || false;
						} else {
							$regForm.id = data.id;
							$regForm.merchant = data.merchant;
							$regForm.logged_date = data.logged_date;
							$regForm.posted_date = data.posted_date || '';
							$regForm.payment_method_name = data.payment_method_name;
							$regForm.note = data.note || '';
							$regForm.is_reconciled = data.is_reconciled || false;
							$regForm.was_reconciled = data.is_reconciled || false;

							// Exclude automated CC balancing entries so user only edits true expenditure splits
							const filtered = (data.splits || []).filter((s) => !isCcBalancingSplit(s));
							editSplits = filtered.map((s) => ({
								envelope_name: s.envelope_name,
								amount: String(Math.abs(parseFloat(s.amount)))
							}));
							if (editSplits.length === 0) {
								editSplits = [{ envelope_name: allActiveEnvelopes[0]?.name || '', amount: '' }];
							}
						}
					})
					.catch((err) => {
						console.error('Error fetching detail:', err);
						isLoadingDetail = false;
					});
			}
		} else {
			lastLoadedId = null;
			detailData = null;
			isEditing = false;
		}
	});

	// Sync edit splits into regForm
	$effect(() => {
		if (isEditing && transaction && transaction.transaction_type !== 'FINANCED') {
			// Per backend contract: If transaction is reconciled, splits cannot be modified/sent
			$regForm.splits_json = transaction.is_reconciled ? '' : JSON.stringify(editSplits);
		}
	});

	function addEditSplit() {
		editSplits = [...editSplits, { envelope_name: allActiveEnvelopes[0]?.name || '', amount: '' }];
	}

	function removeEditSplit(idx: number) {
		if (editSplits.length > 1) {
			editSplits = editSplits.filter((_, i) => i !== idx);
		}
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (open && e.key === 'Escape') onclose();
	}}
/>

{#if open && transaction}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-40 bg-brand-900/40 backdrop-blur-xs transition-opacity duration-200"
		onclick={onclose}
		role="presentation"
	></div>

	<!-- Drawer Panel: Slide-in right on desktop, Bottom sheet on mobile -->
	<div
		class="fixed inset-y-0 right-0 z-50 w-full sm:max-w-md bg-white shadow-2xl flex flex-col border-l border-brand-200 animate-in slide-in-from-right duration-200"
		role="dialog"
		aria-modal="true"
		aria-labelledby="drawer-title"
	>
		<!-- Drawer Header -->
		<div
			class="px-5 py-4 border-b border-brand-100 flex items-center justify-between bg-brand-50/50"
		>
			<div>
				<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider">
					Transaction #{transaction.id}
				</span>
				<h3 id="drawer-title" class="text-lg font-bold text-brand-900 font-sans">
					{transaction.merchant}
				</h3>
			</div>
			<div class="flex items-center gap-2">
				{#if !isEditing && transaction.transaction_type !== 'REVERSAL'}
					<button
						type="button"
						onclick={() => (isEditing = true)}
						class="px-3 py-1 rounded-lg border border-brand-300 text-brand-700 hover:bg-white text-xs font-semibold transition-colors cursor-pointer"
					>
						Edit
					</button>
				{:else if isEditing}
					<button
						type="button"
						onclick={() => (isEditing = false)}
						class="px-3 py-1 rounded-lg border border-brand-300 text-brand-700 hover:bg-white text-xs font-semibold transition-colors cursor-pointer"
					>
						Cancel
					</button>
				{/if}
				<button
					type="button"
					onclick={onclose}
					class="p-1.5 text-brand-400 hover:text-brand-800 rounded-lg hover:bg-brand-200/50 transition-colors cursor-pointer"
					aria-label="Close drawer"
				>
					✕
				</button>
			</div>
		</div>

		<!-- Drawer Body -->
		<div class="flex-1 overflow-y-auto p-5 space-y-5">
			{#if !isEditing}
				<!-- ================= VIEW MODE ================= -->
				<!-- Primary Amount Card -->
				<div class="p-4 rounded-2xl bg-brand-50 border border-brand-200/70 space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-xs font-bold text-brand-600 uppercase tracking-wider">
							Total Amount
						</span>
						<span
							class="px-2 py-0.5 rounded-full text-[11px] font-bold font-sans {transaction.transaction_type ===
							'REVERSAL'
								? 'bg-[#6b1d2f]/10 text-[#6b1d2f]'
								: transaction.transaction_type === 'FINANCED'
									? 'bg-purple-100 text-purple-800'
									: 'bg-brand-200 text-brand-800'}"
						>
							{transaction.transaction_type}
						</span>
					</div>

					<div class="text-3xl font-bold font-mono tabular-nums text-brand-900">
						{formatCurrency(transaction.total)}
					</div>

					{#if transaction.transaction_type === 'FINANCED'}
						<p class="text-xs text-brand-700 font-mono">Credit Card Installment Purchase</p>
					{/if}
				</div>

				<!-- Key Metadata Grid -->
				<div class="grid grid-cols-2 gap-3 text-xs">
					<div class="p-3 rounded-xl bg-white border border-brand-200/60 space-y-1">
						<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider block">
							Logged Date
						</span>
						<span class="font-mono font-semibold text-brand-900">{transaction.logged_date}</span>
					</div>

					<div class="p-3 rounded-xl bg-white border border-brand-200/60 space-y-1">
						<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider block">
							Payment Method
						</span>
						<span class="font-sans font-semibold text-brand-900">
							{transaction.payment_method_name}
						</span>
					</div>

					<div class="p-3 rounded-xl bg-white border border-brand-200/60 space-y-1">
						<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider block">
							Reconciled
						</span>
						<span
							class="font-semibold {transaction.is_reconciled
								? 'text-emerald-700'
								: 'text-amber-700'}"
						>
							{transaction.is_reconciled ? '✓ Cleared' : '⏳ Pending'}
						</span>
					</div>

					<div class="p-3 rounded-xl bg-white border border-brand-200/60 space-y-1">
						<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider block">
							Posted Date
						</span>
						<span class="font-mono text-brand-800">
							{transaction.posted_date || 'Not posted yet'}
						</span>
					</div>
				</div>

				<!-- Notes -->
				{#if transaction.note}
					<div class="p-3 rounded-xl bg-white border border-brand-200/60 space-y-1 text-xs">
						<span class="text-[11px] font-bold text-brand-600 uppercase tracking-wider block">
							Note / Memo
						</span>
						<p class="text-brand-800 font-sans leading-relaxed">{transaction.note}</p>
					</div>
				{/if}

				<!-- Envelope Split Allocations -->
				<div class="space-y-2">
					<span class="text-xs font-bold text-brand-800 uppercase tracking-wider block">
						Envelope Allocations ({userSplits.length})
					</span>

					{#if isLoadingDetail}
						<div class="p-4 text-center text-xs text-brand-500 animate-pulse">
							Loading envelope allocations...
						</div>
					{:else if userSplits.length > 0}
						<div
							class="border border-brand-200 rounded-xl overflow-hidden divide-y divide-brand-100"
						>
							{#each userSplits as split (split.id || split.envelope_name)}
								<div class="p-2.5 flex items-center justify-between text-xs bg-white">
									<div class="flex items-center gap-2">
										<span class="text-brand-500">✉️</span>
										<span class="font-semibold text-brand-900">{split.envelope_name}</span>
									</div>
									<span class="font-mono tabular-nums font-bold text-brand-900">
										{formatCurrency(Math.abs(parseFloat(split.amount)))}
									</span>
								</div>
							{/each}
						</div>
					{:else}
						<div class="p-3 rounded-xl bg-brand-50 text-xs text-brand-600">
							No user envelope splits found for this transaction.
						</div>
					{/if}

					<!-- Automated Credit Card Balancing Info -->
					{#if ccBalancingSplits.length > 0}
						<div
							class="p-2.5 rounded-xl bg-brand-100/60 border border-brand-200 text-xs flex items-center justify-between mt-2"
						>
							<div class="flex items-center gap-1.5 text-brand-800">
								<span>💳</span>
								<span class="font-medium">CC Payment Transfer:</span>
							</div>
							<span class="font-mono tabular-nums font-bold text-brand-900">
								+{formatCurrency(
									ccBalancingSplits.reduce((acc, s) => acc + Math.abs(parseFloat(s.amount)), 0)
								)}
							</span>
						</div>
					{/if}
				</div>
			{:else}
				<!-- ================= EDIT MODE ================= -->
				{#if transaction.transaction_type === 'FINANCED'}
					<!-- Financed Edit Form -->
					{#if transaction.is_reconciled}
						<div
							class="p-2.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs flex items-center gap-2"
						>
							<span>🔒</span>
							<span
								>Reconciled: Principal, terms, envelope, and account are locked by accounting rules.
								Only metadata can be updated.</span
							>
						</div>
					{/if}

					{#if $finErrors._errors}
						<div class="p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] text-xs">
							{#each $finErrors._errors as err, idx (idx)}
								<p>• {err}</p>
							{/each}
						</div>
					{/if}

					<form method="POST" action="?/updateFinanced" use:enhanceFin class="space-y-3 text-xs">
						<input type="hidden" name="id" bind:value={$finForm.id} />
						<input
							type="hidden"
							name="was_reconciled"
							value={transaction.is_reconciled ? 'true' : 'false'}
						/>
						<input type="hidden" name="payment_method_name" value={$finForm.payment_method_name} />

						<div>
							<label for="edit-fin-m" class="block font-bold text-brand-800 uppercase mb-1">
								Merchant
							</label>
							<input
								id="edit-fin-m"
								name="merchant"
								type="text"
								bind:value={$finForm.merchant}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900"
							/>
							{#if $finErrors.merchant}
								<span class="text-[#6b1d2f] text-[11px] block mt-0.5">{$finErrors.merchant}</span>
							{/if}
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div>
								<label for="edit-fin-date" class="block font-bold text-brand-800 uppercase mb-1">
									Date
								</label>
								<input
									id="edit-fin-date"
									name="logged_date"
									type="date"
									bind:value={$finForm.logged_date}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-mono text-brand-900"
								/>
								{#if $finErrors.logged_date}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5"
										>{$finErrors.logged_date}</span
									>
								{/if}
							</div>
							<div>
								<label for="edit-fin-acct" class="block font-bold text-brand-800 uppercase mb-1">
									Credit Card Account
								</label>
								<select
									id="edit-fin-acct"
									disabled={transaction.is_reconciled}
									bind:value={$finForm.payment_method_name}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white disabled:bg-brand-100/50 disabled:cursor-not-allowed"
								>
									{#each creditCardAccounts as acct (acct.id)}
										<option value={acct.name}>{acct.name}</option>
									{/each}
								</select>
								{#if $finErrors.payment_method_name}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5"
										>{$finErrors.payment_method_name}</span
									>
								{/if}
							</div>
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div>
								<label for="edit-fin-amt" class="block font-bold text-brand-800 uppercase mb-1">
									Amount ($)
								</label>
								<input
									id="edit-fin-amt"
									name="amount"
									type="text"
									disabled={transaction.is_reconciled}
									bind:value={$finForm.amount}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-mono text-brand-900 disabled:bg-brand-100/50 disabled:cursor-not-allowed"
								/>
								{#if $finErrors.amount}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5">{$finErrors.amount}</span>
								{/if}
							</div>
							<div>
								<label for="edit-fin-term" class="block font-bold text-brand-800 uppercase mb-1">
									Term (Mo)
								</label>
								<input
									id="edit-fin-term"
									name="term"
									type="number"
									min="1"
									disabled={transaction.is_reconciled}
									bind:value={$finForm.term}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900 disabled:bg-brand-100/50 disabled:cursor-not-allowed"
								/>
								{#if $finErrors.term}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5">{$finErrors.term}</span>
								{/if}
							</div>
						</div>

						<div>
							<label for="edit-fin-env" class="block font-bold text-brand-800 uppercase mb-1">
								Custom Envelope
							</label>
							<input
								id="edit-fin-env"
								name="envelope_name"
								type="text"
								disabled={transaction.is_reconciled}
								placeholder={`Leave blank to use default: ${$finForm.merchant?.trim() || 'Merchant'} - ${$finForm.term || 12}`}
								bind:value={$finForm.envelope_name}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900 disabled:bg-brand-100/50 disabled:cursor-not-allowed"
							/>
							{#if $finErrors.envelope_name}
								<span class="text-[#6b1d2f] text-[11px] block mt-0.5"
									>{$finErrors.envelope_name}</span
								>
							{/if}
						</div>

						<div>
							<label for="edit-fin-note" class="block font-bold text-brand-800 uppercase mb-1">
								Note
							</label>
							<input
								id="edit-fin-note"
								name="note"
								type="text"
								bind:value={$finForm.note}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900"
							/>
						</div>

						<div class="flex items-center pt-2">
							<label class="flex items-center gap-2 cursor-pointer font-medium text-brand-800">
								<input
									type="checkbox"
									name="is_reconciled"
									bind:checked={$finForm.is_reconciled}
									class="w-4 h-4 rounded text-brand-600 border-brand-300"
								/>
								<span>Mark as Reconciled</span>
							</label>
						</div>

						<button
							type="submit"
							disabled={$savingFin}
							class="w-full py-2 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs"
						>
							{#if $savingFin}Saving...{:else}Save Financed Updates{/if}
						</button>
					</form>
				{:else}
					<!-- Regular Transaction Edit Form -->
					{#if transaction.is_reconciled}
						<div
							class="p-2.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs flex items-center gap-2"
						>
							<span>🔒</span>
							<span
								>Reconciled: Envelope splits and payment account are locked by accounting rules.
								Only metadata can be updated.</span
							>
						</div>
					{/if}

					{#if $regErrors._errors}
						<div class="p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] text-xs">
							{#each $regErrors._errors as err, idx (idx)}
								<p>• {err}</p>
							{/each}
						</div>
					{/if}

					<form method="POST" action="?/updateRegular" use:enhanceReg class="space-y-3 text-xs">
						<input type="hidden" name="id" bind:value={$regForm.id} />
						<input
							type="hidden"
							name="was_reconciled"
							value={transaction.is_reconciled ? 'true' : 'false'}
						/>
						<input type="hidden" name="payment_method_name" value={$regForm.payment_method_name} />
						<input type="hidden" name="splits_json" bind:value={$regForm.splits_json} />

						<div>
							<label for="edit-reg-m" class="block font-bold text-brand-800 uppercase mb-1">
								Merchant
							</label>
							<input
								id="edit-reg-m"
								name="merchant"
								type="text"
								bind:value={$regForm.merchant}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900"
							/>
							{#if $regErrors.merchant}
								<span class="text-[#6b1d2f] text-[11px] block mt-0.5">{$regErrors.merchant}</span>
							{/if}
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div>
								<label for="edit-reg-date" class="block font-bold text-brand-800 uppercase mb-1">
									Date
								</label>
								<input
									id="edit-reg-date"
									name="logged_date"
									type="date"
									bind:value={$regForm.logged_date}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-mono text-brand-900"
								/>
								{#if $regErrors.logged_date}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5"
										>{$regErrors.logged_date}</span
									>
								{/if}
							</div>

							<div>
								<label for="edit-reg-acct" class="block font-bold text-brand-800 uppercase mb-1">
									Account
								</label>
								<select
									id="edit-reg-acct"
									disabled={transaction.is_reconciled}
									bind:value={$regForm.payment_method_name}
									class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white disabled:bg-brand-100/50 disabled:cursor-not-allowed"
								>
									{#each activeAccounts as acct (acct.id)}
										<option value={acct.name}>
											{acct.name} ({acct.account_type === 'cash' ? 'Cash' : 'Card'})
										</option>
									{/each}
								</select>
								{#if $regErrors.payment_method_name}
									<span class="text-[#6b1d2f] text-[11px] block mt-0.5"
										>{$regErrors.payment_method_name}</span
									>
								{/if}
							</div>
						</div>

						<!-- Editable Splits (Locked if transaction is reconciled per backend contract) -->
						{#if !transaction.is_reconciled}
							<div>
								<div class="flex items-center justify-between mb-1.5">
									<span class="font-bold text-brand-800 uppercase">Splits</span>
									<button
										type="button"
										onclick={addEditSplit}
										class="text-[11px] font-semibold text-brand-600 hover:text-brand-900 cursor-pointer"
									>
										+ Add Split
									</button>
								</div>

								<div class="space-y-1.5">
									{#each editSplits as split, idx (idx)}
										<div class="flex items-center gap-1.5">
											<select
												bind:value={split.envelope_name}
												class="flex-1 px-2 py-1 rounded-lg border border-brand-300 text-xs text-brand-900 bg-white"
											>
												{#each budgetingCategories as cat (cat.id)}
													<optgroup label={cat.name}>
														{#each cat.envelopes.filter((e) => e.is_active) as env (env.id)}
															<option value={env.name}>{env.name}</option>
														{/each}
													</optgroup>
												{/each}
											</select>

											<input
												type="text"
												bind:value={split.amount}
												placeholder="0.00"
												class="w-24 px-2 py-1 rounded-lg border border-brand-300 text-xs font-mono tabular-nums text-brand-900"
											/>

											{#if editSplits.length > 1}
												<button
													type="button"
													onclick={() => removeEditSplit(idx)}
													class="p-1 text-brand-400 hover:text-[#6b1d2f] cursor-pointer"
												>
													✕
												</button>
											{/if}
										</div>
									{/each}
								</div>
							</div>
							{#if $regErrors.splits_json}
								<span class="text-[#6b1d2f] text-[11px] block mt-0.5">{$regErrors.splits_json}</span
								>
							{/if}
						{/if}

						<div>
							<label for="edit-reg-note" class="block font-bold text-brand-800 uppercase mb-1">
								Note
							</label>
							<input
								id="edit-reg-note"
								name="note"
								type="text"
								bind:value={$regForm.note}
								class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 font-sans text-brand-900"
							/>
						</div>

						<div class="flex items-center pt-2">
							<label class="flex items-center gap-2 cursor-pointer font-medium text-brand-800">
								<input
									type="checkbox"
									name="is_reconciled"
									bind:checked={$regForm.is_reconciled}
									class="w-4 h-4 rounded text-brand-600 border-brand-300"
								/>
								<span>Mark as Reconciled</span>
							</label>
						</div>

						<button
							type="submit"
							disabled={$savingReg}
							class="w-full py-2 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs"
						>
							{#if $savingReg}Saving...{:else}Save Changes{/if}
						</button>
					</form>
				{/if}
			{/if}
		</div>

		<!-- Drawer Footer Actions -->
		{#if !isEditing}
			<div
				class="p-4 border-t border-brand-100 bg-brand-50/50 flex items-center justify-between text-xs"
			>
				{#if transaction.transaction_type !== 'REVERSAL'}
					<button
						type="button"
						onclick={() => ondelete(transaction)}
						class="text-[#6b1d2f] hover:text-[#521624] font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
					>
						<span>🗑️</span>
						<span>Delete / Reverse</span>
					</button>
				{:else}
					<span class="text-xs text-brand-500 italic">Reversal records are read-only</span>
				{/if}

				<button
					type="button"
					onclick={onclose}
					class="px-3.5 py-1.5 rounded-xl bg-white border border-brand-200 text-brand-800 font-semibold hover:bg-brand-100/60 transition-colors cursor-pointer"
				>
					Close
				</button>
			</div>
		{/if}
	</div>
{/if}
