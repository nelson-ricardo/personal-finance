<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { transferEnvelopeSchema } from '#lib/schemas/envelope.ts';
	import type { Envelope } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		formData,
		envelopes = [],
		initialSource = '',
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof transferEnvelopeSchema>>;
		envelopes: Envelope[];
		initialSource?: string;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: transferForm,
		errors: transferErrors,
		enhance: enhanceTransfer,
		submitting: transferring
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	$effect(() => {
		if (open) {
			if (initialSource) {
				$transferForm.source_envelope = initialSource;
			} else if (envelopes.length > 0 && !$transferForm.source_envelope) {
				$transferForm.source_envelope = envelopes[0].name;
			}
		}
	});

	const sourceEnvelopeObj = $derived(
		envelopes.find((e) => e.name === $transferForm.source_envelope)
	);
</script>

<Modal
	{open}
	title="Transfer Funds Between Envelopes"
	description="Reallocate money between two budgeting envelopes without impacting account balances."
	{onclose}
>
	{#if $transferErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $transferErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/transfer" use:enhanceTransfer class="space-y-4">
		<!-- Source Envelope -->
		<div>
			<div class="flex items-center justify-between mb-1">
				<label
					for="transfer-source"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider"
				>
					From (Source Envelope)
				</label>
				{#if sourceEnvelopeObj}
					<span class="text-xs font-mono text-brand-600">
						Balance: {formatCurrency(sourceEnvelopeObj.balance)}
					</span>
				{/if}
			</div>
			<select
				id="transfer-source"
				name="source_envelope"
				bind:value={$transferForm.source_envelope}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
			>
				{#each envelopes as env (env.name)}
					<option value={env.name}>
						{env.name} ({formatCurrency(env.balance)})
					</option>
				{/each}
			</select>
			{#if $transferErrors.source_envelope}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$transferErrors.source_envelope}</p>
			{/if}
		</div>

		<!-- Destination Envelope -->
		<div>
			<label
				for="transfer-dest"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				To (Destination Envelope)
			</label>
			<select
				id="transfer-dest"
				name="destination_envelope"
				bind:value={$transferForm.destination_envelope}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
			>
				{#each envelopes.filter((e) => e.name !== $transferForm.source_envelope) as env (env.name)}
					<option value={env.name}>
						{env.name} ({formatCurrency(env.balance)})
					</option>
				{/each}
			</select>
			{#if $transferErrors.destination_envelope}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">
					{$transferErrors.destination_envelope}
				</p>
			{/if}
		</div>

		<!-- Amount -->
		<div>
			<label
				for="transfer-amount"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Amount ($)
			</label>
			<input
				id="transfer-amount"
				name="amount"
				type="text"
				placeholder="0.00"
				bind:value={$transferForm.amount}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $transferErrors.amount}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$transferErrors.amount}</p>
			{/if}
		</div>

		<!-- Optional Note -->
		<div>
			<label
				for="transfer-note"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Note (Optional)
			</label>
			<input
				id="transfer-note"
				name="note"
				type="text"
				placeholder="e.g. Covering dining overspend"
				bind:value={$transferForm.note}
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
				disabled={$transferring}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$transferring ? 'Transferring...' : 'Execute Transfer'}
			</button>
		</div>
	</form>
</Modal>
