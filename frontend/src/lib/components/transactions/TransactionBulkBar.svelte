<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { bulkReconcileSchema } from '#lib/schemas/transaction.ts';

	let {
		selectedIds = $bindable([]),
		formData,
		onclear
	}: {
		selectedIds: number[];
		formData: SuperValidated<Infer<typeof bulkReconcileSchema>>;
		onclear: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: bulkForm,
		enhance: enhanceBulk,
		submitting: isReconciling
	} = superForm(formData, {
		resetForm: true,
		invalidateAll: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclear();
			}
		}
	});

	$effect(() => {
		$bulkForm.transaction_ids = selectedIds.join(',');
	});
</script>

{#if selectedIds.length > 0}
	<div
		class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-brand-900 text-brand-50 px-4 py-2.5 rounded-2xl shadow-2xl border border-brand-700/60 flex items-center gap-3.5 animate-in slide-in-from-bottom-4 duration-150 max-w-lg w-[90vw] sm:w-auto justify-between"
	>
		<div class="flex items-center gap-2">
			<span class="w-2 h-2 rounded-full bg-emerald-400"></span>
			<span class="text-xs font-bold font-sans">
				{selectedIds.length}
				{selectedIds.length === 1 ? 'transaction' : 'transactions'} selected
			</span>
		</div>

		<form method="POST" action="?/bulkReconcile" use:enhanceBulk class="flex items-center gap-2">
			<input type="hidden" name="transaction_ids" bind:value={$bulkForm.transaction_ids} />
			<input type="hidden" name="is_reconciled" bind:value={$bulkForm.is_reconciled} />

			<button
				type="submit"
				onclick={() => ($bulkForm.is_reconciled = true)}
				disabled={$isReconciling}
				class="px-3 py-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
			>
				<span>✓</span>
				<span>Mark Reconciled</span>
			</button>

			<button
				type="submit"
				onclick={() => ($bulkForm.is_reconciled = false)}
				disabled={$isReconciling}
				class="px-3 py-1.5 rounded-xl bg-brand-800 hover:bg-brand-700 text-brand-200 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
			>
				Unmark
			</button>

			<button
				type="button"
				onclick={onclear}
				class="p-1 text-brand-400 hover:text-white rounded-lg transition-colors cursor-pointer text-xs"
				title="Clear Selection"
			>
				✕
			</button>
		</form>
	</div>
{/if}
