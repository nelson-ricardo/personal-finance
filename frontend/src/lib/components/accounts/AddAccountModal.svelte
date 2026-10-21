<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { createAccountSchema } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';

	let {
		open = false,
		formData,
		categories = [],
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof createAccountSchema>>;
		categories?: EnvelopeCategoryWithEnvelopes[];
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: newAccount,
		errors: createErrors,
		enhance: enhanceCreate,
		submitting: creating
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	const userCategories = $derived(categories.filter((c) => c.name !== 'System'));
</script>

<Modal
	{open}
	title="Add New Account"
	description="Establish a credit card or loan account for active tracking"
	{onclose}
>
	<!-- Oxblood Error Banners -->
	{#if $createErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $createErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/create" use:enhanceCreate class="space-y-3.5 sm:space-y-4">
		<!-- Name -->
		<div>
			<label
				for="create-name"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Account Name
			</label>
			<input
				id="create-name"
				name="name"
				type="text"
				placeholder="e.g. Chase Sapphire, Auto Loan"
				bind:value={$newAccount.name}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $createErrors.name}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$createErrors.name}</p>
			{/if}
		</div>

		<!-- Account Type -->
		<div>
			<label
				for="create-type"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Account Type
			</label>
			<select
				name="account_type"
				id="create-type"
				bind:value={$newAccount.account_type}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
			>
				<option value="credit_card">Credit Card</option>
				<option value="loan">Loan</option>
			</select>
		</div>

		<!-- Category Group (Optional for Loan payment envelope) -->
		{#if $newAccount.account_type === 'loan'}
			<div>
				<label
					for="create-category"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Category Group <span class="font-normal lowercase text-brand-500">(optional)</span>
				</label>
				<select
					name="category_name"
					id="create-category"
					bind:value={$newAccount.category_name}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
				>
					<option value="">None (Uncategorized)</option>
					{#each userCategories as cat (cat.id)}
						<option value={cat.name}>{cat.name}</option>
					{/each}
				</select>
				<p class="text-[11px] text-brand-600 mt-1">
					Choose which category group will house this loan's payment envelope.
				</p>
			</div>
		{/if}

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<!-- Current Balance -->
			<div>
				<label
					for="create-balance"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Initial Balance
				</label>
				<input
					id="create-balance"
					name="current_balance"
					type="text"
					placeholder="0.00"
					bind:value={$newAccount.current_balance}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $createErrors.current_balance}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$createErrors.current_balance}</p>
				{/if}
			</div>

			<!-- Monthly Payment -->
			<div>
				<label
					for="create-monthly-payment"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Monthly Payment
				</label>
				<input
					id="create-monthly-payment"
					name="monthly_payment"
					type="text"
					placeholder="0.00"
					bind:value={$newAccount.monthly_payment}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
			</div>
		</div>

		<!-- Due Date -->
		<div>
			<label
				for="create-date"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Due Date (Day 1 - 31)
			</label>
			<input
				id="create-date"
				name="due_date"
				type="number"
				min="1"
				max="31"
				placeholder="15"
				bind:value={$newAccount.due_date}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $createErrors.due_date}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$createErrors.due_date}</p>
			{/if}
		</div>

		<div
			class="pt-4 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2.5 sm:gap-3 border-t border-brand-100"
		>
			<button
				type="button"
				onclick={onclose}
				class="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-brand-300 text-brand-700 text-sm font-semibold hover:bg-brand-50 transition-colors cursor-pointer text-center"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={$creating}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$creating ? 'Creating...' : 'Create Account'}
			</button>
		</div>
	</form>
</Modal>
