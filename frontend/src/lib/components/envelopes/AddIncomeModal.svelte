<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { addIncomeSchema } from '#lib/schemas/envelope.ts';
	import Modal from '#lib/components/Modal.svelte';

	let {
		open = false,
		formData,
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof addIncomeSchema>>;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: incomeForm,
		errors: incomeErrors,
		enhance: enhanceIncome,
		submitting: adding
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	$effect(() => {
		if (open && !$incomeForm.source) {
			$incomeForm.source = 'Paycheck';
		}
	});
</script>

<Modal
	{open}
	title="Add Income"
	description="Deposit funds into your primary Cash account, making them immediately Ready to Assign in Unassigned."
	{onclose}
>
	{#if $incomeErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $incomeErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/addIncome" use:enhanceIncome class="space-y-4">
		<!-- Amount -->
		<div>
			<label
				for="income-amount"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Income Amount ($)
			</label>
			<input
				id="income-amount"
				name="amount"
				type="text"
				placeholder="0.00"
				bind:value={$incomeForm.amount}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $incomeErrors.amount}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$incomeErrors.amount}</p>
			{/if}
		</div>

		<!-- Source -->
		<div>
			<label
				for="income-source"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Source / Payer
			</label>
			<input
				id="income-source"
				name="source"
				type="text"
				placeholder="e.g. Acme Corp, Client Invoice, Tax Refund"
				bind:value={$incomeForm.source}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $incomeErrors.source}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$incomeErrors.source}</p>
			{/if}
		</div>

		<!-- Note -->
		<div>
			<label
				for="income-note"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Note (Optional)
			</label>
			<input
				id="income-note"
				name="note"
				type="text"
				placeholder="e.g. Bi-weekly direct deposit"
				bind:value={$incomeForm.note}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
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
				disabled={$adding}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$adding ? 'Adding...' : 'Deposit Income'}
			</button>
		</div>
	</form>
</Modal>
