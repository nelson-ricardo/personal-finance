<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { assignEnvelopeSchema, transferEnvelopeSchema } from '#lib/schemas/envelope.ts';
	import type { Envelope } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		assignFormData,
		transferFormData,
		targetEnvelope = null,
		unassignedBalance = 0,
		initialMode = 'assign',
		onclose
	}: {
		open: boolean;
		assignFormData: SuperValidated<Infer<typeof assignEnvelopeSchema>>;
		transferFormData: SuperValidated<Infer<typeof transferEnvelopeSchema>>;
		targetEnvelope: Envelope | null;
		unassignedBalance: number;
		initialMode?: 'assign' | 'return';
		onclose: () => void;
	} = $props();

	let mode = $state<'assign' | 'return'>('assign');

	const envelopeBalance = $derived(targetEnvelope ? parseFloat(targetEnvelope.balance) || 0 : 0);
	const isNegative = $derived(envelopeBalance < 0);
	const overageAmount = $derived(isNegative ? Math.abs(envelopeBalance) : 0);

	// svelte-ignore state_referenced_locally
	const {
		form: assignForm,
		errors: assignErrors,
		enhance: enhanceAssign,
		submitting: assigning
	} = superForm(assignFormData, {
		resetForm: true,
		onResult({ result }) {
			if (result.type === 'success') {
				onclose();
			}
		},
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	// svelte-ignore state_referenced_locally
	const {
		form: transferForm,
		errors: transferErrors,
		enhance: enhanceTransfer,
		submitting: transferring
	} = superForm(transferFormData, {
		resetForm: true,
		onResult({ result }) {
			if (result.type === 'success') {
				onclose();
			}
		},
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	$effect(() => {
		if (targetEnvelope && open) {
			mode = initialMode;
			// Prep assign form
			$assignForm.envelope_name = targetEnvelope.name;
			$assignForm.amount = isNegative ? overageAmount.toFixed(2) : '';

			// Prep transfer (return) form
			$transferForm.source_envelope = targetEnvelope.name;
			$transferForm.destination_envelope = 'Unassigned';
			$transferForm.amount = '';
			$transferForm.note = `Return funds from ${targetEnvelope.name} to Ready to Assign`;
		}
	});

	function coverOverage() {
		if (overageAmount > 0) {
			$assignForm.amount = overageAmount.toFixed(2);
		}
	}

	// Quick chips for Assign mode
	function addAssignAmount(delta: number) {
		const current = parseFloat($assignForm.amount) || 0;
		const next = Math.min(Math.max(0, unassignedBalance), current + delta);
		$assignForm.amount = next.toFixed(2);
	}

	function fillMaxAssign() {
		if (unassignedBalance > 0) {
			$assignForm.amount = unassignedBalance.toFixed(2);
		}
	}

	// Quick chips for Return mode
	function addReturnAmount(delta: number) {
		const current = parseFloat($transferForm.amount) || 0;
		const next = Math.min(Math.max(0, envelopeBalance), current + delta);
		$transferForm.amount = next.toFixed(2);
	}

	function returnAll() {
		if (envelopeBalance > 0) {
			$transferForm.amount = envelopeBalance.toFixed(2);
		}
	}
</script>

<Modal
	{open}
	title={targetEnvelope ? `Move Money: ${targetEnvelope.name}` : 'Move Money'}
	description="Reallocate cash between this envelope and Ready to Assign."
	{onclose}
>
	<!-- Direction Toggle Tabs -->
	<div
		class="grid grid-cols-2 p-1 bg-brand-100/70 border border-brand-200/80 rounded-xl text-xs font-semibold"
	>
		<button
			type="button"
			onclick={() => (mode = 'assign')}
			class="py-2 px-3 rounded-lg transition-all cursor-pointer text-center {mode === 'assign'
				? 'bg-white text-emerald-900 shadow-2xs font-bold'
				: 'text-brand-600 hover:text-brand-900'}"
		>
			+ Add from Unassigned
		</button>
		<button
			type="button"
			onclick={() => (mode = 'return')}
			class="py-2 px-3 rounded-lg transition-all cursor-pointer text-center {mode === 'return'
				? 'bg-white text-[#6b1d2f] shadow-2xs font-bold'
				: 'text-brand-600 hover:text-brand-900'}"
		>
			− Return to Unassigned
		</button>
	</div>

	{#if mode === 'assign'}
		<!-- MODE 1: Add funds from Unassigned into Envelope -->
		{#if $assignErrors._errors}
			<div
				class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
			>
				{#each $assignErrors._errors as err, idx (idx)}
					<p>• {err}</p>
				{/each}
			</div>
		{/if}

		<div
			class="p-3 rounded-xl bg-emerald-50/80 border border-emerald-200/90 flex items-center justify-between"
		>
			<div class="text-xs text-emerald-800 font-medium">Available in Ready to Assign:</div>
			<div class="font-mono font-bold text-sm text-emerald-950 tabular-nums">
				{formatCurrency(unassignedBalance)}
			</div>
		</div>

		<form method="POST" action="?/assign" use:enhanceAssign class="space-y-4">
			<input
				type="hidden"
				name="envelope_name"
				value={targetEnvelope?.name ?? $assignForm.envelope_name}
			/>

			{#if isNegative}
				<!-- Cover Overage Banner & Instant Action -->
				<div class="p-3 rounded-xl bg-amber-50/90 border border-amber-200/90 space-y-2">
					<div class="flex items-center justify-between text-xs gap-2">
						<div class="text-amber-900 font-semibold flex items-center gap-1.5 min-w-0">
							<span>⚠️ Overspent:</span>
							<strong class="font-mono text-amber-950 shrink-0"
								>{formatCurrency(overageAmount)}</strong
							>
						</div>
						<div class="text-amber-800 font-mono text-[11px] tabular-nums shrink-0">
							Balance: {formatCurrency(envelopeBalance)}
						</div>
					</div>
					<button
						type="button"
						onclick={coverOverage}
						class="w-full py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white text-xs font-bold transition-all shadow-2xs cursor-pointer flex items-center justify-center gap-1.5"
					>
						<svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						<span>Cover Overage Exactly ({formatCurrency(overageAmount)})</span>
					</button>
				</div>
			{/if}

			<div>
				<label
					for="assign-amount"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Amount to Add ($)
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
				{#if isNegative}
					<button
						type="button"
						onclick={coverOverage}
						class="px-2.5 py-1 text-xs font-mono font-bold rounded-lg bg-amber-100 text-amber-900 hover:bg-amber-200 border border-amber-300 transition-colors cursor-pointer"
					>
						Cover {formatCurrency(overageAmount)}
					</button>
				{/if}
				<button
					type="button"
					onclick={() => addAssignAmount(25)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					+$25
				</button>
				<button
					type="button"
					onclick={() => addAssignAmount(50)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					+$50
				</button>
				<button
					type="button"
					onclick={() => addAssignAmount(100)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					+$100
				</button>
				<button
					type="button"
					onclick={fillMaxAssign}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-emerald-100 text-emerald-900 hover:bg-emerald-200 transition-colors cursor-pointer"
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
					class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-700 text-white text-sm font-semibold hover:bg-emerald-800 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
				>
					{$assigning ? 'Adding...' : 'Add to Envelope'}
				</button>
			</div>
		</form>
	{:else}
		<!-- MODE 2: Return funds from Envelope back to Unassigned -->
		{#if $transferErrors._errors}
			<div
				class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
			>
				{#each $transferErrors._errors as err, idx (idx)}
					<p>• {err}</p>
				{/each}
			</div>
		{/if}

		<div
			class="p-3 rounded-xl bg-amber-50/80 border border-amber-200/90 flex items-center justify-between"
		>
			<div class="text-xs text-amber-900 font-medium">Currently in {targetEnvelope?.name}:</div>
			<div class="font-mono font-bold text-sm text-amber-950 tabular-nums">
				{formatCurrency(envelopeBalance)}
			</div>
		</div>

		<form method="POST" action="?/transfer" use:enhanceTransfer class="space-y-4">
			<input
				type="hidden"
				name="source_envelope"
				value={targetEnvelope?.name ?? $transferForm.source_envelope}
			/>
			<input type="hidden" name="destination_envelope" value="Unassigned" />
			<input type="hidden" name="note" bind:value={$transferForm.note} />

			<div>
				<label
					for="return-amount"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Amount to Return ($)
				</label>
				<input
					id="return-amount"
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

			<!-- Quick Chips -->
			<div class="flex items-center gap-1.5 flex-wrap">
				<span class="text-xs text-brand-500 font-medium mr-1">Quick return:</span>
				<button
					type="button"
					onclick={() => addReturnAmount(25)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					−$25
				</button>
				<button
					type="button"
					onclick={() => addReturnAmount(50)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					−$50
				</button>
				<button
					type="button"
					onclick={() => addReturnAmount(100)}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 transition-colors cursor-pointer"
				>
					−$100
				</button>
				<button
					type="button"
					onclick={returnAll}
					class="px-2.5 py-1 text-xs font-mono font-semibold rounded-lg bg-[#6b1d2f]/10 text-[#6b1d2f] hover:bg-[#6b1d2f]/20 transition-colors cursor-pointer font-bold"
				>
					Return All (Reset to $0)
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
					disabled={$transferring}
					class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-[#6b1d2f] text-white text-sm font-semibold hover:bg-[#521624] disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
				>
					{$transferring ? 'Returning...' : 'Return to Ready to Assign'}
				</button>
			</div>
		</form>
	{/if}
</Modal>
