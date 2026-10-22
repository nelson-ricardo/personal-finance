<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type {
		paymentSchema,
		accountAdjustmentSchema,
		interestChargeSchema,
		interestEarnedSchema,
		Account
	} from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes, Envelope } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency, getLocalDateString } from '#lib/utils/formatters.ts';
	import { getUserVisibleCategories } from '#lib/utils/categories.ts';

	export type OperationTab = 'payment' | 'adjustment' | 'interest_charge' | 'interest_earned';

	let {
		open = false,
		initialTab = 'payment',
		initialAccountName = '',
		accounts = [],
		categories = [],
		envelopes = [],
		paymentFormData,
		adjustmentFormData,
		interestChargeFormData,
		interestEarnedFormData,
		onclose
	}: {
		open: boolean;
		initialTab?: OperationTab;
		initialAccountName?: string;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		envelopes?: Envelope[];
		paymentFormData: SuperValidated<Infer<typeof paymentSchema>>;
		adjustmentFormData: SuperValidated<Infer<typeof accountAdjustmentSchema>>;
		interestChargeFormData: SuperValidated<Infer<typeof interestChargeSchema>>;
		interestEarnedFormData: SuperValidated<Infer<typeof interestEarnedSchema>>;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	let activeTab = $state<OperationTab>(initialTab);

	const displayCategories = $derived(getUserVisibleCategories(categories));

	// Sync activeTab and pre-selected accounts when modal opens
	$effect(() => {
		if (open) {
			if (initialTab) {
				activeTab = initialTab;
			}
			if (initialAccountName) {
				const target = accounts.find((a) => a.name === initialAccountName);
				if (target) {
					if (target.account_type === 'cash') {
						$earnedForm.account_name = target.name;
						$adjForm.account_name = target.name;
					} else {
						$payForm.account = target.name;
						$chargeForm.account_name = target.name;
						$adjForm.account_name = target.name;
					}
				}
			}
		}
	});

	// Superforms for the 4 actions
	// svelte-ignore state_referenced_locally
	const {
		form: payForm,
		errors: payErrors,
		message: payMessage,
		enhance: enhancePay,
		submitting: paying
	} = superForm(paymentFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	// svelte-ignore state_referenced_locally
	const {
		form: adjForm,
		errors: adjErrors,
		message: adjMessage,
		enhance: enhanceAdj,
		submitting: adjusting
	} = superForm(adjustmentFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	// svelte-ignore state_referenced_locally
	const {
		form: chargeForm,
		errors: chargeErrors,
		message: chargeMessage,
		enhance: enhanceCharge,
		submitting: charging
	} = superForm(interestChargeFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	// svelte-ignore state_referenced_locally
	const {
		form: earnedForm,
		errors: earnedErrors,
		message: earnedMessage,
		enhance: enhanceEarned,
		submitting: earning
	} = superForm(interestEarnedFormData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	// Filtered account lists
	const debtAccounts = $derived(
		accounts.filter(
			(a) => a.is_active && (a.account_type === 'credit_card' || a.account_type === 'loan')
		)
	);
	const investmentAccounts = $derived(
		accounts.filter((a) => a.is_active && a.account_type === 'investment')
	);
	const payableAccounts = $derived(
		accounts.filter(
			(a) =>
				a.is_active &&
				(a.account_type === 'credit_card' ||
					a.account_type === 'loan' ||
					a.account_type === 'investment')
		)
	);
	const cashAccounts = $derived(accounts.filter((a) => a.is_active && a.account_type === 'cash'));
	const allActiveAccounts = $derived(accounts.filter((a) => a.is_active));

	// Context for Payment tab
	const selectedPayAccount = $derived(
		payableAccounts.find((a) => a.name === $payForm.account) || payableAccounts[0] || null
	);
	const isInvestmentPay = $derived(selectedPayAccount?.account_type === 'investment');

	const allEnvelopes = $derived.by(() => {
		const combined: Envelope[] = [...envelopes];
		for (const cat of categories) {
			for (const env of cat.envelopes || []) {
				if (
					!combined.some(
						(e) =>
							(e.id != null && e.id === env.id) || e.name.toLowerCase() === env.name.toLowerCase()
					)
				) {
					combined.push(env);
				}
			}
		}
		return combined;
	});

	const fundingEnvelopes = $derived(
		allEnvelopes.filter(
			(e) =>
				e.is_active &&
				e.name !== 'Unassigned' &&
				e.name !== 'Account Adjustment' &&
				!e.name.startsWith('Credit Card Payment')
		)
	);

	const selectedFundingEnvelope = $derived.by(() => {
		if (!isInvestmentPay) return null;
		if ($payForm.envelope_name) {
			const found = fundingEnvelopes.find((e) => e.name === $payForm.envelope_name);
			if (found) return found;
		}
		const defaultInv = fundingEnvelopes.find(
			(e) => e.name.toLowerCase() === 'investments' || e.name.toLowerCase() === 'investment'
		);
		return defaultInv || fundingEnvelopes[0] || null;
	});

	const linkedEnvelope = $derived.by(() => {
		if (!selectedPayAccount) return null;

		// 1. Match by account.envelope_id
		if (selectedPayAccount.envelope_id) {
			const found = allEnvelopes.find((e) => e.id === selectedPayAccount.envelope_id);
			if (found) return found;
		}

		const acctNameLower = selectedPayAccount.name.toLowerCase();

		// 2. If Credit Card
		if (selectedPayAccount.account_type === 'credit_card') {
			const found = allEnvelopes.find(
				(e) =>
					e.system_role?.toUpperCase() === 'CREDIT_CARD_PAYMENT' ||
					e.name.toLowerCase() === 'credit card payment' ||
					e.name.toLowerCase() === `credit card payment - ${acctNameLower}` ||
					e.name.toLowerCase().includes(acctNameLower)
			);
			if (found) return found;
		}

		// 3. If Loan (or fallback for CC)
		const found = allEnvelopes.find(
			(e) => e.name.toLowerCase() === acctNameLower || e.name.toLowerCase().includes(acctNameLower)
		);
		if (found) return found;

		return null;
	});

	const displayEnvelopeName = $derived(
		isInvestmentPay
			? (selectedFundingEnvelope?.name ?? null)
			: (selectedPayAccount?.envelope_name ?? linkedEnvelope?.name ?? null)
	);
	const displayEnvelopeBalance = $derived(
		isInvestmentPay
			? (selectedFundingEnvelope?.balance ?? null)
			: (selectedPayAccount?.envelope_balance ?? linkedEnvelope?.balance ?? null)
	);

	// Context for Adjustment tab
	const selectedAdjAccount = $derived(
		allActiveAccounts.find((a) => a.name === $adjForm.account_name) || allActiveAccounts[0] || null
	);

	const adjDelta = $derived.by(() => {
		if (
			!selectedAdjAccount ||
			$adjForm.target_balance === '' ||
			isNaN(parseFloat($adjForm.target_balance))
		) {
			return null;
		}
		const current = parseFloat(selectedAdjAccount.current_balance) || 0;
		const target = parseFloat($adjForm.target_balance) || 0;
		return target - current;
	});

	// Context for Interest Charge tab
	const selectedChargeAccount = $derived(
		debtAccounts.find((a) => a.name === $chargeForm.account_name) || debtAccounts[0] || null
	);

	// Context for Interest Earned tab
	const selectedEarnedAccount = $derived(
		cashAccounts.find((a) => a.name === $earnedForm.account_name) || cashAccounts[0] || null
	);

	// Set initial account defaults if empty
	$effect(() => {
		if (open) {
			if (!$payForm.account && debtAccounts.length > 0) {
				$payForm.account = debtAccounts[0].name;
			}
			if (!$adjForm.account_name && allActiveAccounts.length > 0) {
				$adjForm.account_name = allActiveAccounts[0].name;
			}
			if (!$chargeForm.account_name && debtAccounts.length > 0) {
				$chargeForm.account_name = debtAccounts[0].name;
			}
			if (!$earnedForm.account_name && cashAccounts.length > 0) {
				$earnedForm.account_name = cashAccounts[0].name;
			}
			const today = getLocalDateString();
			if (!$adjForm.logged_date) $adjForm.logged_date = today;
			if (!$chargeForm.logged_date) $chargeForm.logged_date = today;
			if (!$earnedForm.logged_date) $earnedForm.logged_date = today;
		}
	});

	function setPayAmount(amountVal: string | number | null | undefined) {
		if (amountVal === null || amountVal === undefined) return;
		const num = typeof amountVal === 'string' ? parseFloat(amountVal) : amountVal;
		if (isNaN(num) || num <= 0) return;
		$payForm.amount = num.toFixed(2);
	}
</script>

<Modal
	{open}
	title="Account Operations"
	description="Record debt payments, reconcile balances, and manage interest charges or APY earnings."
	{onclose}
>
	<!-- Tab Bar -->
	<div
		class="grid grid-cols-2 sm:grid-cols-4 gap-1.5 p-1 bg-brand-100/70 rounded-xl border border-brand-200/80 text-xs font-semibold"
	>
		<button
			type="button"
			onclick={() => (activeTab = 'payment')}
			class="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg transition-all cursor-pointer {activeTab ===
			'payment'
				? 'bg-white text-brand-900 shadow-2xs font-bold'
				: 'text-brand-700 hover:text-brand-950 hover:bg-white/50'}"
		>
			<span>💳</span>
			<span class="truncate">Payment</span>
		</button>

		<button
			type="button"
			onclick={() => (activeTab = 'adjustment')}
			class="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg transition-all cursor-pointer {activeTab ===
			'adjustment'
				? 'bg-white text-brand-900 shadow-2xs font-bold'
				: 'text-brand-700 hover:text-brand-950 hover:bg-white/50'}"
		>
			<span>⚖️</span>
			<span class="truncate">Adjustment</span>
		</button>

		<button
			type="button"
			onclick={() => (activeTab = 'interest_charge')}
			class="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg transition-all cursor-pointer {activeTab ===
			'interest_charge'
				? 'bg-white text-brand-900 shadow-2xs font-bold'
				: 'text-brand-700 hover:text-brand-950 hover:bg-white/50'}"
		>
			<span>📈</span>
			<span class="truncate">Interest Fee</span>
		</button>

		<button
			type="button"
			onclick={() => (activeTab = 'interest_earned')}
			class="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg transition-all cursor-pointer {activeTab ===
			'interest_earned'
				? 'bg-white text-brand-900 shadow-2xs font-bold'
				: 'text-brand-700 hover:text-brand-950 hover:bg-white/50'}"
		>
			<span>💰</span>
			<span class="truncate">Earned APY</span>
		</button>
	</div>

	<!-- TAB 1: MAKE PAYMENT -->
	{#if activeTab === 'payment'}
		<div class="space-y-4 pt-1">
			<!-- Context Banner -->
			<div
				class="p-3 rounded-xl bg-brand-50 border border-brand-200/80 text-xs text-brand-800 space-y-1"
			>
				<div class="font-bold text-brand-900 flex items-center gap-1.5">
					<span>ℹ️</span>
					<span>{isInvestmentPay ? 'Transfer Cash to Investment' : 'Debt Payment'}</span>
				</div>
				<p class="leading-relaxed">
					{#if isInvestmentPay}
						Transfers cash from your liquid balance into your investment account. Funds are deducted
						from the selected budget envelope and increase your portfolio asset balance.
					{:else}
						Transfers cash to pay down your credit card or loan. Funds are drawn from the account's
						linked payment envelope and reduce the debt balance.
					{/if}
				</p>
			</div>

			{#if $payMessage}
				<div
					class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold"
				>
					{$payMessage}
				</div>
			{/if}

			{#if $payErrors._errors}
				<div
					class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs space-y-1 font-medium"
				>
					{#each $payErrors._errors as err, idx (idx)}
						<p>• {err}</p>
					{/each}
				</div>
			{/if}

			{#if payableAccounts.length === 0}
				<div
					class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1"
				>
					<p class="font-bold">No payable or investment accounts found.</p>
					<p>Create a credit card, loan, or investment account first.</p>
				</div>
			{:else}
				<form method="POST" action="?/makePayment" use:enhancePay class="space-y-4 text-xs">
					<!-- Account Selection -->
					<div>
						<label
							for="pay-account"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Destination Account
						</label>
						<select
							id="pay-account"
							name="account"
							bind:value={$payForm.account}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						>
							{#if debtAccounts.length > 0}
								<optgroup label="Credit Cards & Loans">
									{#each debtAccounts as acct (acct.id)}
										<option value={acct.name}>
											{acct.name} ({acct.account_type === 'credit_card' ? 'Credit Card' : 'Loan'})
										</option>
									{/each}
								</optgroup>
							{/if}
							{#if investmentAccounts.length > 0}
								<optgroup label="Investments & Portfolio">
									{#each investmentAccounts as acct (acct.id)}
										<option value={acct.name}>
											{acct.name} (Investment)
										</option>
									{/each}
								</optgroup>
							{/if}
						</select>
						{#if $payErrors.account}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$payErrors.account}</span
							>
						{/if}
					</div>

					<!-- For Investment Accounts: Choose funding envelope -->
					{#if isInvestmentPay}
						<div>
							<label
								for="pay-envelope"
								class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
							>
								Source Budget Envelope
							</label>
							<select
								id="pay-envelope"
								name="envelope_name"
								bind:value={$payForm.envelope_name}
								class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
							>
								{#each fundingEnvelopes as env (env.id)}
									<option value={env.name}>
										{env.name} ({formatCurrency(env.balance)})
									</option>
								{/each}
							</select>
							<p class="text-[11px] text-brand-500 mt-1">
								Cash is deducted from your liquid account and covered by this budget envelope.
							</p>
						</div>
					{/if}

					<!-- Account Status Snapshot Card -->
					{#if selectedPayAccount}
						<div
							class="grid grid-cols-2 gap-2.5 p-3 rounded-xl bg-brand-50/70 border border-brand-200 text-xs"
						>
							<div>
								<span class="text-brand-600 block text-[11px]">
									{isInvestmentPay ? 'Current Portfolio Value' : 'Current Debt Balance'}
								</span>
								<span
									class="font-mono tabular-nums font-bold text-sm {isInvestmentPay
										? 'text-emerald-900'
										: 'text-brand-900'}"
								>
									{formatCurrency(selectedPayAccount.current_balance)}
								</span>
							</div>
							<div>
								<span class="text-brand-600 block text-[11px]">
									Available in Envelope
									{#if displayEnvelopeName}
										<span class="font-sans text-[10px] text-brand-500 font-normal"
											>({displayEnvelopeName})</span
										>
									{/if}
								</span>
								<span class="font-mono tabular-nums font-bold text-emerald-800 text-sm">
									{displayEnvelopeBalance != null ? formatCurrency(displayEnvelopeBalance) : '—'}
								</span>
							</div>
						</div>
					{/if}

					<!-- Amount Input & Quick Fill Pills -->
					<div>
						<div class="flex items-center justify-between mb-1">
							<label for="pay-amount" class="font-bold text-brand-800 uppercase tracking-wider">
								{isInvestmentPay ? 'Transfer Amount ($)' : 'Payment Amount ($)'}
							</label>
							{#if selectedPayAccount}
								<div class="flex items-center gap-1">
									{#if !isInvestmentPay}
										<button
											type="button"
											onclick={() => setPayAmount(selectedPayAccount?.current_balance)}
											class="px-2 py-0.5 rounded-md bg-brand-100 hover:bg-brand-200 text-brand-800 text-[10px] font-mono font-semibold cursor-pointer"
										>
											Pay Full
										</button>
									{/if}
									{#if displayEnvelopeBalance && parseFloat(displayEnvelopeBalance) > 0}
										<button
											type="button"
											onclick={() => setPayAmount(displayEnvelopeBalance)}
											class="px-2 py-0.5 rounded-md bg-emerald-100 hover:bg-emerald-200 text-emerald-900 text-[10px] font-mono font-semibold cursor-pointer"
										>
											Available
										</button>
									{/if}
									{#if !isInvestmentPay && selectedPayAccount.total_statement_balance && parseFloat(selectedPayAccount.total_statement_balance) > 0}
										<button
											type="button"
											onclick={() => setPayAmount(selectedPayAccount?.total_statement_balance)}
											class="px-2 py-0.5 rounded-md bg-brand-100 hover:bg-brand-200 text-brand-800 text-[10px] font-mono font-semibold cursor-pointer"
										>
											Statement
										</button>
									{/if}
								</div>
							{/if}
						</div>

						<input
							id="pay-amount"
							name="amount"
							type="text"
							inputmode="decimal"
							placeholder="0.00"
							bind:value={$payForm.amount}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-base tabular-nums text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						/>
						{#if $payErrors.amount}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$payErrors.amount}</span
							>
						{/if}
					</div>

					<button
						type="submit"
						disabled={$paying}
						class="w-full py-2.5 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 active:bg-brand-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-sm"
					>
						{#if $paying}
							{isInvestmentPay ? 'Transferring Funds...' : 'Recording Payment...'}
						{:else}
							{isInvestmentPay ? '💸 Transfer to Investment' : '💸 Record Payment'}
						{/if}
					</button>
				</form>
			{/if}
		</div>

		<!-- TAB 2: ADJUST BALANCE -->
	{:else if activeTab === 'adjustment'}
		<div class="space-y-4 pt-1">
			<!-- Context Banner -->
			<div
				class="p-3 rounded-xl bg-brand-50 border border-brand-200/80 text-xs text-brand-800 space-y-1"
			>
				<div class="font-bold text-brand-900 flex items-center gap-1.5">
					<span>⚖️</span>
					<span>Reconcile Real-World Account Balance</span>
				</div>
				<p class="leading-relaxed">
					Logs a compensating balance adjustment so your ledger matches your statement. Surpluses
					credit <strong>Unassigned</strong>. Cash deficits must be deducted from an envelope.
				</p>
			</div>

			{#if $adjMessage}
				<div
					class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold"
				>
					{$adjMessage}
				</div>
			{/if}

			{#if $adjErrors._errors}
				<div
					class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs space-y-1 font-medium"
				>
					{#each $adjErrors._errors as err, idx (idx)}
						<p>• {err}</p>
					{/each}
				</div>
			{/if}

			<form method="POST" action="?/adjustBalance" use:enhanceAdj class="space-y-4 text-xs">
				<!-- Account Selection -->
				<div>
					<label
						for="adj-account"
						class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Account to Reconcile
					</label>
					<select
						id="adj-account"
						name="account_name"
						bind:value={$adjForm.account_name}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					>
						{#each allActiveAccounts as acct (acct.id)}
							<option value={acct.name}>
								{acct.name} ({acct.account_type.replace('_', ' ')})
							</option>
						{/each}
					</select>
					{#if $adjErrors.account_name}
						<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
							>{$adjErrors.account_name}</span
						>
					{/if}
				</div>

				<!-- Current Balance & Live Delta Preview -->
				{#if selectedAdjAccount}
					<div class="p-3 rounded-xl bg-brand-50/70 border border-brand-200 text-xs space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-brand-600">Current Tracked Balance:</span>
							<span class="font-mono tabular-nums font-bold text-brand-900">
								{formatCurrency(selectedAdjAccount.current_balance)}
							</span>
						</div>

						{#if adjDelta !== null}
							<div class="flex items-center justify-between pt-1.5 border-t border-brand-200/60">
								<span class="text-brand-700 font-semibold">Calculated Adjustment:</span>
								<span
									class="font-mono tabular-nums font-bold {adjDelta > 0
										? 'text-emerald-700'
										: adjDelta < 0
											? 'text-[#6b1d2f]'
											: 'text-brand-600'}"
								>
									{adjDelta > 0 ? `+${formatCurrency(adjDelta)}` : formatCurrency(adjDelta)}
								</span>
							</div>

							<!-- Explanatory feedback based on accounting rules -->
							{#if selectedAdjAccount.account_type === 'cash'}
								{#if adjDelta > 0}
									<p
										class="text-[11px] text-emerald-800 bg-emerald-100/60 p-2 rounded-lg font-medium"
									>
										✓ Cash surplus of {formatCurrency(adjDelta)} will be credited to
										<strong>Unassigned</strong> (Ready to Assign).
									</p>
								{:else if adjDelta < 0}
									<p class="text-[11px] text-[#6b1d2f] bg-[#6b1d2f]/10 p-2 rounded-lg font-medium">
										⚠️ Cash reduction of {formatCurrency(Math.abs(adjDelta))} must be deducted from a
										budgeting envelope below.
									</p>
								{:else}
									<p class="text-[11px] text-brand-600 italic">
										Balances match. No adjustment needed.
									</p>
								{/if}
							{:else if selectedAdjAccount?.account_type === 'investment'}
								{#if adjDelta > 0}
									<p
										class="text-[11px] text-emerald-800 bg-emerald-100/60 p-2 rounded-lg font-medium"
									>
										Portfolio gain of {formatCurrency(adjDelta)} will be recorded to
										<strong>Account Adjustment</strong>.
									</p>
								{:else if adjDelta < 0}
									<p class="text-[11px] text-[#6b1d2f] bg-[#6b1d2f]/10 p-2 rounded-lg font-medium">
										Portfolio drop of {formatCurrency(Math.abs(adjDelta))} will be recorded to
										<strong>Account Adjustment</strong>.
									</p>
								{:else}
									<p class="text-[11px] text-brand-600 italic">
										Balances match. No adjustment needed.
									</p>
								{/if}
							{:else}
								{#if adjDelta > 0}
									<p class="text-[11px] text-amber-900 bg-amber-100/60 p-2 rounded-lg font-medium">
										Debt will increase by {formatCurrency(adjDelta)}, recorded in Account
										Adjustment.
									</p>
								{:else if adjDelta < 0}
									<p
										class="text-[11px] text-emerald-900 bg-emerald-100/60 p-2 rounded-lg font-medium"
									>
										Debt will decrease by {formatCurrency(Math.abs(adjDelta))}, recorded in Account
										Adjustment.
									</p>
								{/if}
							{/if}
						{/if}
					</div>
				{/if}

				<!-- Target Balance Input -->
				<div>
					<label
						for="adj-target"
						class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
					>
						Target Real-World Balance ($)
					</label>
					<input
						id="adj-target"
						name="target_balance"
						type="text"
						inputmode="decimal"
						placeholder="0.00"
						bind:value={$adjForm.target_balance}
						class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-base tabular-nums text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
					/>
					{#if $adjErrors.target_balance}
						<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
							>{$adjErrors.target_balance}</span
						>
					{/if}
				</div>

				<!-- If Cash Account with Deficit: Require Envelope Selection -->
				{#if selectedAdjAccount?.account_type === 'cash' && adjDelta !== null && adjDelta < 0}
					<div class="space-y-1">
						<label
							for="adj-envelope"
							class="block font-bold text-brand-800 uppercase tracking-wider"
						>
							Deduct Deficit From Envelope <span class="text-[#6b1d2f]">*</span>
						</label>
						<select
							id="adj-envelope"
							name="envelope_name"
							bind:value={$adjForm.envelope_name}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						>
							<option value="">Select an envelope to absorb reduction...</option>
							{#each displayCategories as cat (cat.id ?? cat.name)}
								<optgroup label={cat.name}>
									{#each cat.envelopes.filter((e) => e.is_active && e.name !== 'Account Adjustment') as env (env.id ?? env.name)}
										<option value={env.name}>
											{env.name} ({formatCurrency(env.balance)} available)
										</option>
									{/each}
								</optgroup>
							{/each}
						</select>
						{#if $adjErrors.envelope_name}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$adjErrors.envelope_name}</span
							>
						{/if}
					</div>
				{/if}

				<!-- Date & Note -->
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					<div>
						<label
							for="adj-date"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Date
						</label>
						<input
							id="adj-date"
							name="logged_date"
							type="date"
							bind:value={$adjForm.logged_date}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						/>
						{#if $adjErrors.logged_date}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$adjErrors.logged_date}</span
							>
						{/if}
					</div>

					<div>
						<label
							for="adj-note"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Note (Optional)
						</label>
						<input
							id="adj-note"
							name="note"
							type="text"
							placeholder="e.g. Bank statement reconciliation"
							bind:value={$adjForm.note}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						/>
						{#if $adjErrors.note}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$adjErrors.note}</span
							>
						{/if}
					</div>
				</div>

				<button
					type="submit"
					disabled={$adjusting || (adjDelta !== null && adjDelta === 0)}
					class="w-full py-2.5 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 active:bg-brand-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-sm"
				>
					{#if $adjusting}Reconciling...{:else}Reconcile Balance{/if}
				</button>
			</form>
		</div>

		<!-- TAB 3: INTEREST CHARGE -->
	{:else if activeTab === 'interest_charge'}
		<div class="space-y-4 pt-1">
			<!-- Context Banner -->
			<div
				class="p-3 rounded-xl bg-brand-50 border border-brand-200/80 text-xs text-brand-800 space-y-1"
			>
				<div class="font-bold text-brand-900 flex items-center gap-1.5">
					<span>📈</span>
					<span>Log Interest or Finance Charge</span>
				</div>
				<p class="leading-relaxed">
					Adds interest or finance fees to a debt account (Credit Card or Loan). The transaction is
					absorbed by <strong>Account Adjustment</strong> without impacting your user budgeting envelopes.
				</p>
			</div>

			{#if $chargeMessage}
				<div
					class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold"
				>
					{$chargeMessage}
				</div>
			{/if}

			{#if $chargeErrors._errors}
				<div
					class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs space-y-1 font-medium"
				>
					{#each $chargeErrors._errors as err, idx (idx)}
						<p>• {err}</p>
					{/each}
				</div>
			{/if}

			{#if debtAccounts.length === 0}
				<div
					class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1"
				>
					<p class="font-bold">No active debt accounts found.</p>
					<p>Interest charges can only be logged against credit card or loan accounts.</p>
				</div>
			{:else}
				<form
					method="POST"
					action="?/addInterestCharge"
					use:enhanceCharge
					class="space-y-4 text-xs"
				>
					<!-- Account Selection -->
					<div>
						<label
							for="charge-account"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Debt Account
						</label>
						<select
							id="charge-account"
							name="account_name"
							bind:value={$chargeForm.account_name}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						>
							{#each debtAccounts as acct (acct.id)}
								<option value={acct.name}>
									{acct.name} ({acct.account_type === 'credit_card' ? 'Credit Card' : 'Loan'})
								</option>
							{/each}
						</select>
						{#if $chargeErrors.account_name}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$chargeErrors.account_name}</span
							>
						{/if}
					</div>

					{#if selectedChargeAccount}
						<div
							class="p-2.5 rounded-xl bg-brand-50/70 border border-brand-200 text-xs flex items-center justify-between"
						>
							<span class="text-brand-600">Current Debt Balance:</span>
							<span class="font-mono tabular-nums font-bold text-brand-900">
								{formatCurrency(selectedChargeAccount.current_balance)}
							</span>
						</div>
					{/if}

					<!-- Amount Input -->
					<div>
						<label
							for="charge-amount"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Interest Amount ($)
						</label>
						<input
							id="charge-amount"
							name="amount"
							type="text"
							inputmode="decimal"
							placeholder="0.00"
							bind:value={$chargeForm.amount}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-base tabular-nums text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						/>
						{#if $chargeErrors.amount}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$chargeErrors.amount}</span
							>
						{/if}
					</div>

					<!-- Date & Note -->
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						<div>
							<label
								for="charge-date"
								class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
							>
								Date
							</label>
							<input
								id="charge-date"
								name="logged_date"
								type="date"
								bind:value={$chargeForm.logged_date}
								class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
							/>
							{#if $chargeErrors.logged_date}
								<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
									>{$chargeErrors.logged_date}</span
								>
							{/if}
						</div>

						<div>
							<label
								for="charge-note"
								class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
							>
								Note
							</label>
							<input
								id="charge-note"
								name="note"
								type="text"
								bind:value={$chargeForm.note}
								class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
							/>
							{#if $chargeErrors.note}
								<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
									>{$chargeErrors.note}</span
								>
							{/if}
						</div>
					</div>

					<button
						type="submit"
						disabled={$charging}
						class="w-full py-2.5 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 active:bg-brand-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-sm"
					>
						{#if $charging}Logging Interest...{:else}Log Interest Charge{/if}
					</button>
				</form>
			{/if}
		</div>

		<!-- TAB 4: INTEREST EARNED -->
	{:else if activeTab === 'interest_earned'}
		<div class="space-y-4 pt-1">
			<!-- Context Banner -->
			<div
				class="p-3 rounded-xl bg-brand-50 border border-brand-200/80 text-xs text-brand-800 space-y-1"
			>
				<div class="font-bold text-brand-900 flex items-center gap-1.5">
					<span>💰</span>
					<span>Log Interest Earned / APY Dividends</span>
				</div>
				<p class="leading-relaxed">
					Logs interest received into a liquid cash or savings account. Automatically credited to <strong
						>Unassigned</strong
					> (Ready to Assign) so you can budget the earned income immediately.
				</p>
			</div>

			{#if $earnedMessage}
				<div
					class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold"
				>
					{$earnedMessage}
				</div>
			{/if}

			{#if $earnedErrors._errors}
				<div
					class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs space-y-1 font-medium"
				>
					{#each $earnedErrors._errors as err, idx (idx)}
						<p>• {err}</p>
					{/each}
				</div>
			{/if}

			{#if cashAccounts.length === 0}
				<div
					class="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1"
				>
					<p class="font-bold">No active cash accounts found.</p>
					<p>Interest earned can only be deposited into cash/savings accounts.</p>
				</div>
			{:else}
				<form
					method="POST"
					action="?/addInterestEarned"
					use:enhanceEarned
					class="space-y-4 text-xs"
				>
					<!-- Account Selection -->
					<div>
						<label
							for="earned-account"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Cash / Savings Account
						</label>
						<select
							id="earned-account"
							name="account_name"
							bind:value={$earnedForm.account_name}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						>
							{#each cashAccounts as acct (acct.id)}
								<option value={acct.name}>{acct.name}</option>
							{/each}
						</select>
						{#if $earnedErrors.account_name}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$earnedErrors.account_name}</span
							>
						{/if}
					</div>

					{#if selectedEarnedAccount}
						<div
							class="p-2.5 rounded-xl bg-brand-50/70 border border-brand-200 text-xs flex items-center justify-between"
						>
							<span class="text-brand-600">Current Cash Balance:</span>
							<span class="font-mono tabular-nums font-bold text-brand-900">
								{formatCurrency(selectedEarnedAccount.current_balance)}
							</span>
						</div>
					{/if}

					<!-- Amount Input -->
					<div>
						<label
							for="earned-amount"
							class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
						>
							Interest Earned ($)
						</label>
						<input
							id="earned-amount"
							name="amount"
							type="text"
							inputmode="decimal"
							placeholder="0.00"
							bind:value={$earnedForm.amount}
							class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-base tabular-nums text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
						/>
						{#if $earnedErrors.amount}
							<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
								>{$earnedErrors.amount}</span
							>
						{/if}
					</div>

					<!-- Date & Note -->
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						<div>
							<label
								for="earned-date"
								class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
							>
								Date
							</label>
							<input
								id="earned-date"
								name="logged_date"
								type="date"
								bind:value={$earnedForm.logged_date}
								class="w-full px-3 py-2 rounded-xl border border-brand-300 font-mono text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
							/>
							{#if $earnedErrors.logged_date}
								<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
									>{$earnedErrors.logged_date}</span
								>
							{/if}
						</div>

						<div>
							<label
								for="earned-note"
								class="block font-bold text-brand-800 uppercase tracking-wider mb-1"
							>
								Note
							</label>
							<input
								id="earned-note"
								name="note"
								type="text"
								bind:value={$earnedForm.note}
								class="w-full px-3 py-2 rounded-xl border border-brand-300 font-sans text-brand-900 bg-white shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
							/>
							{#if $earnedErrors.note}
								<span class="text-[#6b1d2f] text-[11px] block mt-1 font-medium"
									>{$earnedErrors.note}</span
								>
							{/if}
						</div>
					</div>

					<button
						type="submit"
						disabled={$earning}
						class="w-full py-2.5 rounded-xl bg-brand-500 text-brand-50 font-semibold hover:bg-brand-600 active:bg-brand-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-sm"
					>
						{#if $earning}Depositing Interest...{:else}Record Interest Earned{/if}
					</button>
				</form>
			{/if}
		</div>
	{/if}
</Modal>
