<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { quickAddSchema } from '#lib/schemas/transaction.ts';
	import type { Account } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import { getLocalDateString } from '#lib/utils/formatters.ts';

	let {
		formData,
		accounts,
		categories,
		onsplit
	}: {
		formData: SuperValidated<Infer<typeof quickAddSchema>>;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		onsplit?: (draft: {
			merchant: string;
			amount: string;
			logged_date: string;
			payment_method_name: string;
			envelope_name: string;
			note: string;
		}) => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: quickForm,
		errors: quickErrors,
		enhance: enhanceQuick,
		submitting: adding
	} = superForm(formData, {
		resetForm: true,
		invalidateAll: true
	});

	// Flat list of active envelopes (excluding System category)
	const activeEnvelopes = $derived(
		categories
			.filter((c) => c.name !== 'System')
			.flatMap((c) => c.envelopes)
			.filter((e) => e.is_active)
	);

	const activeAccounts = $derived(
		accounts.filter(
			(a) => a.is_active && (a.account_type === 'cash' || a.account_type === 'credit_card')
		)
	);

	// Preselect first account and envelope if empty
	$effect(() => {
		if (!$quickForm.payment_method_name && activeAccounts.length > 0) {
			const cashAcct = activeAccounts.find((a) => a.account_type === 'cash');
			$quickForm.payment_method_name = (cashAcct || activeAccounts[0]).name;
		}
		if (!$quickForm.envelope_name && activeEnvelopes.length > 0) {
			$quickForm.envelope_name = activeEnvelopes[0].name;
		}
		if (!$quickForm.logged_date) {
			$quickForm.logged_date = getLocalDateString();
		}
	});

	function handleSplitClick() {
		if (onsplit) {
			onsplit({
				merchant: $quickForm.merchant,
				amount: $quickForm.amount,
				logged_date: $quickForm.logged_date,
				payment_method_name: $quickForm.payment_method_name,
				envelope_name: $quickForm.envelope_name,
				note: $quickForm.note || ''
			});
		}
	}
</script>

<div
	class="bg-white rounded-2xl border border-brand-200/80 shadow-xs p-3.5 sm:p-4 transition-all duration-150"
>
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-2">
			<span class="w-2 h-2 rounded-full bg-brand-500 animate-pulse" aria-hidden="true"></span>
			<h2 class="text-xs font-bold uppercase tracking-wider text-brand-800">
				Quick-Add Single Expense
			</h2>
		</div>
		<span class="text-xs text-brand-600 hidden sm:inline">
			Need multiple envelopes?
			<button
				type="button"
				onclick={handleSplitClick}
				class="font-semibold text-brand-700 hover:text-brand-900 underline underline-offset-2 ml-1 cursor-pointer transition-colors"
			>
				Use Split Builder →
			</button>
		</span>
	</div>

	{#if $quickErrors._errors}
		<div
			class="mb-3 p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $quickErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form
		method="POST"
		action="?/quickAdd"
		use:enhanceQuick
		class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-2.5 items-end"
	>
		<!-- Date (2 cols) -->
		<div class="lg:col-span-2">
			<label
				for="qa-date"
				class="block text-[11px] font-bold text-brand-700 uppercase tracking-wider mb-1"
			>
				Date
			</label>
			<input
				id="qa-date"
				name="logged_date"
				type="date"
				bind:value={$quickForm.logged_date}
				class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-mono text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow bg-brand-50/30"
			/>
			{#if $quickErrors.logged_date}
				<p class="text-[11px] text-[#6b1d2f] mt-0.5">{$quickErrors.logged_date}</p>
			{/if}
		</div>

		<!-- Merchant (3 cols) -->
		<div class="lg:col-span-3">
			<label
				for="qa-merchant"
				class="block text-[11px] font-bold text-brand-700 uppercase tracking-wider mb-1"
			>
				Merchant / Payee
			</label>
			<input
				id="qa-merchant"
				name="merchant"
				type="text"
				placeholder="e.g. Trader Joe's"
				bind:value={$quickForm.merchant}
				class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 placeholder:text-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow"
			/>
			{#if $quickErrors.merchant}
				<p class="text-[11px] text-[#6b1d2f] mt-0.5">{$quickErrors.merchant}</p>
			{/if}
		</div>

		<!-- Account (2 cols) -->
		<div class="lg:col-span-2">
			<label
				for="qa-account"
				class="block text-[11px] font-bold text-brand-700 uppercase tracking-wider mb-1"
			>
				Account
			</label>
			<select
				id="qa-account"
				name="payment_method_name"
				bind:value={$quickForm.payment_method_name}
				class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow bg-white"
			>
				{#each activeAccounts as acct (acct.id)}
					<option value={acct.name}>
						{acct.name} ({acct.account_type === 'cash' ? 'Cash' : 'Card'})
					</option>
				{/each}
			</select>
			{#if $quickErrors.payment_method_name}
				<p class="text-[11px] text-[#6b1d2f] mt-0.5">{$quickErrors.payment_method_name}</p>
			{/if}
		</div>

		<!-- Envelope (2 cols) -->
		<div class="lg:col-span-2">
			<label
				for="qa-envelope"
				class="block text-[11px] font-bold text-brand-700 uppercase tracking-wider mb-1"
			>
				Envelope
			</label>
			<select
				id="qa-envelope"
				name="envelope_name"
				bind:value={$quickForm.envelope_name}
				class="w-full px-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-sans text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow bg-white"
			>
				{#each categories.filter((c) => c.name !== 'System') as cat (cat.id)}
					<optgroup label={cat.name}>
						{#each cat.envelopes.filter((e) => e.is_active) as env (env.id)}
							<option value={env.name}>{env.name}</option>
						{/each}
					</optgroup>
				{/each}
			</select>
			{#if $quickErrors.envelope_name}
				<p class="text-[11px] text-[#6b1d2f] mt-0.5">{$quickErrors.envelope_name}</p>
			{/if}
		</div>

		<!-- Amount (1.5 cols) -->
		<div class="lg:col-span-2">
			<label
				for="qa-amount"
				class="block text-[11px] font-bold text-brand-700 uppercase tracking-wider mb-1"
			>
				Amount ($)
			</label>
			<div class="relative">
				<span
					class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-mono text-brand-500 select-none"
				>
					$
				</span>
				<input
					id="qa-amount"
					name="amount"
					type="text"
					inputmode="decimal"
					placeholder="0.00"
					bind:value={$quickForm.amount}
					class="w-full pl-6 pr-2.5 py-1.5 rounded-xl border border-brand-300 text-xs font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-shadow"
				/>
			</div>
			{#if $quickErrors.amount}
				<p class="text-[11px] text-[#6b1d2f] mt-0.5">{$quickErrors.amount}</p>
			{/if}
		</div>

		<!-- Action Buttons (1.5 cols) -->
		<div class="lg:col-span-1 flex items-center gap-1.5">
			<button
				type="submit"
				disabled={$adding}
				class="w-full py-1.5 px-3 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs flex items-center justify-center cursor-pointer"
				title="Add Quick Expense"
			>
				{#if $adding}
					<span
						class="w-3 h-3 border-2 border-brand-50 border-t-transparent rounded-full animate-spin"
					></span>
				{:else}
					Add
				{/if}
			</button>
			<button
				type="button"
				onclick={handleSplitClick}
				class="sm:hidden py-1.5 px-2 rounded-xl border border-brand-300 text-brand-800 text-xs font-semibold hover:bg-brand-50 transition-colors cursor-pointer"
				title="Split into multiple envelopes"
			>
				Split
			</button>
		</div>
	</form>
</div>
