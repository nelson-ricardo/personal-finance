<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { assignEnvelopeSchema } from '#lib/schemas/envelope.ts';
	import type { Envelope } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		formData,
		targetEnvelope = null,
		unassignedBalance = 0,
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof assignEnvelopeSchema>>;
		targetEnvelope: Envelope | null;
		unassignedBalance: number;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: assignForm,
		errors: assignErrors,
		enhance: enhanceAssign,
		submitting: assigning
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	$effect(() => {
		if (targetEnvelope && open) {
			$assignForm.envelope_name = targetEnvelope.name;
			$assignForm.amount = '';
		}
	});

	function addAmount(delta: number) {
		const current = parseFloat($assignForm.amount) || 0;
		const next = Math.min(unassignedBalance, current + delta);
		$assignForm.amount = next.toFixed(2);
	}

	function fillMax() {
		if (unassignedBalance > 0) {
			$assignForm.amount = unassignedBalance.toFixed(2);
		}
	}
</script>

<Modal
	{open}
	title={targetEnvelope ? `Assign to ${targetEnvelope.name}` : 'Assign from Unassigned'}
	description="Move liquid funds from Ready to Assign directly into this budgeting envelope."
	{onclose}
>
	<!-- Oxblood Error Banner -->
	{#if $assignErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $assignErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<!-- Available Unassigned Metric Callout -->
	<div
		class="p-3.5 rounded-xl bg-emerald-50/80 border border-emerald-200/90 flex items-center justify-between"
	>
		<div class="text-xs text-emerald-800 font-medium">Available in Unassigned:</div>
		<div class="font-mono font-bold text-sm text-emerald-950 tabular-nums">
			{formatCurrency(unassignedBalance)}
		</div>
	</div>

	<form method="POST" action="?/assign" use:enhanceAssign class="space-y-4">
		<input type="hidden" name="envelope_name" bind:value={$assignForm.envelope_name} />

		<!-- Amount Input -->
		<div>
			<label
				for="assign-amount"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Amount to Assign ($)
			</label>
			<input
				id="assign-amount"
				name="amount"
				type="text"
				placeholder="0.00"
				bind:value={$assignForm.amount}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $assignErrors.amount}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$assignErrors.amount}</p>
			{/if}
		</div>

		<!-- Quick Chips -->
		<div class="flex items-center gap-1.5 flex-wrap">
			<span class="text-xs text-brand-500 font-medium mr-1">Quick add:</span>
			<button
				type="button"
				onclick={() => addAmount(25)}
				class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
			>
				+$25
			</button>
			<button
				type="button"
				onclick={() => addAmount(50)}
				class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
			>
				+$50
			</button>
			<button
				type="button"
				onclick={() => addAmount(100)}
				class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
			>
				+$100
			</button>
			<button
				type="button"
				onclick={fillMax}
				class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-emerald-100 text-emerald-800 hover:bg-emerald-200 transition-colors cursor-pointer"
			>
				Fill Max
			</button>
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
				disabled={$assigning}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$assigning ? 'Assigning...' : 'Confirm Assignment'}
			</button>
		</div>
	</form>
</Modal>
