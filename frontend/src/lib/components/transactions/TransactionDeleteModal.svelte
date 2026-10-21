<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { deleteTransactionSchema, TransactionItem } from '#lib/schemas/transaction.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		formData,
		transaction,
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof deleteTransactionSchema>>;
		transaction: TransactionItem | null;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: deleteForm,
		errors: deleteErrors,
		enhance: enhanceDelete,
		submitting: deleting
	} = superForm(formData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	$effect(() => {
		if (open && transaction) {
			$deleteForm.id = transaction.id;
		}
	});
</script>

<Modal
	{open}
	title="Reverse Transaction"
	description="Double-entry accounting maintains audit integrity by issuing an offset reversal."
	{onclose}
>
	{#if $deleteErrors._errors}
		<div
			class="p-2.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1 mb-3"
		>
			{#each $deleteErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	{#if transaction}
		<div class="space-y-4">
			<!-- Transaction Snapshot Box -->
			<div class="p-3.5 rounded-xl bg-brand-50/70 border border-brand-200/80 space-y-2">
				<div class="flex items-center justify-between">
					<span class="text-xs font-bold text-brand-700 uppercase tracking-wider">
						{transaction.transaction_type}
					</span>
					<span class="text-xs font-mono text-brand-600">{transaction.logged_date}</span>
				</div>
				<div class="flex items-center justify-between">
					<h4 class="text-base font-bold text-brand-900 font-sans">{transaction.merchant}</h4>
					<span class="text-base font-bold font-mono tabular-nums text-brand-900">
						{formatCurrency(transaction.total)}
					</span>
				</div>
				<div class="text-xs text-brand-600">
					Account: <span class="font-semibold text-brand-800"
						>{transaction.payment_method_name}</span
					>
				</div>
			</div>

			<!-- Accounting Notice -->
			<div
				class="p-3 rounded-xl bg-[#6b1d2f]/10 border border-[#6b1d2f]/20 text-[#6b1d2f] text-xs leading-relaxed space-y-1"
			>
				<p class="font-bold">⚠️ Ledger Reversal Notice</p>
				<p>
					In accordance with envelope budgeting principles, this transaction is not hard-deleted.
					Instead, a <strong>REVERSAL</strong> entry is recorded to restore deducted funds back to your
					envelopes and restore account balances.
				</p>
			</div>

			<!-- Action Buttons -->
			<form method="POST" action="?/deleteTransaction" use:enhanceDelete>
				<input type="hidden" name="id" bind:value={$deleteForm.id} />

				<div class="flex items-center justify-end gap-2 pt-2 border-t border-brand-100">
					<button
						type="button"
						onclick={onclose}
						class="px-4 py-2 rounded-xl text-xs font-semibold text-brand-700 hover:bg-brand-100/60 transition-colors cursor-pointer"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={$deleting}
						class="px-5 py-2 rounded-xl bg-[#6b1d2f] text-white text-xs font-semibold hover:bg-[#521624] disabled:opacity-50 transition-colors shadow-xs flex items-center justify-center cursor-pointer"
					>
						{#if $deleting}
							<span
								class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"
							></span>
						{:else}
							Confirm Reversal
						{/if}
					</button>
				</div>
			</form>
		</div>
	{/if}
</Modal>
