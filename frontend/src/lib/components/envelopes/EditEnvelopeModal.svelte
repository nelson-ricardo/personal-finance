<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { updateEnvelopeSchema } from '#lib/schemas/envelope.ts';
	import type { Envelope, EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let {
		open = false,
		formData,
		envelope = null,
		categories = [],
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof updateEnvelopeSchema>>;
		envelope: Envelope | null;
		categories: EnvelopeCategoryWithEnvelopes[];
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: editForm,
		errors: editErrors,
		enhance: enhanceEdit,
		submitting: updating
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	let showDeleteConfirm = $state(false);

	$effect(() => {
		if (envelope && open) {
			$editForm.original_name = envelope.name;
			$editForm.name = envelope.name;
			$editForm.category_name = envelope.category_name || '';
			$editForm.note = envelope.note || '';
			showDeleteConfirm = false;
		}
	});

	const balanceNum = $derived(envelope ? parseFloat(envelope.balance) || 0 : 0);
	const canDeactivate = $derived(balanceNum === 0);
</script>

<Modal
	{open}
	title={envelope ? `Edit ${envelope.name}` : 'Edit Envelope'}
	description="Update envelope name, category assignment, or lifecycle status."
	{onclose}
>
	{#if $editErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $editErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/updateEnvelope" use:enhanceEdit class="space-y-4">
		<input type="hidden" name="original_name" bind:value={$editForm.original_name} />

		<!-- Name -->
		<div>
			<label
				for="edit-env-name"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Envelope Name
			</label>
			<input
				id="edit-env-name"
				name="name"
				type="text"
				bind:value={$editForm.name}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $editErrors.name}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$editErrors.name}</p>
			{/if}
		</div>

		<!-- Category -->
		<div>
			<label
				for="edit-env-cat"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Category Group
			</label>
			<select
				id="edit-env-cat"
				name="category_name"
				bind:value={$editForm.category_name}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
			>
				{#each categories as cat (cat.name)}
					<option value={cat.name}>{cat.name}</option>
				{/each}
			</select>
		</div>

		<!-- Note -->
		<div>
			<label
				for="edit-env-note"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Target or Purpose Note
			</label>
			<input
				id="edit-env-note"
				name="note"
				type="text"
				bind:value={$editForm.note}
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
				disabled={$updating}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$updating ? 'Saving...' : 'Save Changes'}
			</button>
		</div>
	</form>

	<!-- Envelope Lifecycle Actions (Deactivate/Reactivate & Delete) -->
	{#if envelope && !envelope.system_role}
		<div class="mt-6 pt-5 border-t border-brand-200/80 space-y-3">
			<div class="text-xs font-bold uppercase tracking-wider text-brand-600">
				Envelope Lifecycle Management
			</div>

			<!-- Deactivate or Reactivate -->
			<div
				class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-brand-50/70 border border-brand-200/80"
			>
				<div>
					<div class="text-xs font-semibold text-brand-900">
						{envelope.is_active ? 'Deactivate (Archive) Envelope' : 'Reactivate Envelope'}
					</div>
					<div class="text-[11px] text-brand-600">
						{#if envelope.is_active}
							{canDeactivate
								? 'Archives this envelope. It can be reactivated anytime.'
								: `Balance must be $0.00 to deactivate (currently ${formatCurrency(envelope.balance)}).`}
						{:else}
							Restore this envelope to active budgeting status.
						{/if}
					</div>
				</div>

				{#if envelope.is_active}
					<form method="POST" action="?/deactivateEnvelope">
						<input type="hidden" name="name" value={envelope.name} />
						<button
							type="submit"
							disabled={!canDeactivate}
							class="w-full sm:w-auto px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors {canDeactivate
								? 'bg-amber-100 text-amber-900 hover:bg-amber-200 cursor-pointer'
								: 'bg-slate-100 text-slate-400 cursor-not-allowed'}"
						>
							Deactivate
						</button>
					</form>
				{:else}
					<form method="POST" action="?/activateEnvelope">
						<input type="hidden" name="name" value={envelope.name} />
						<button
							type="submit"
							class="w-full sm:w-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-900 hover:bg-emerald-200 transition-colors cursor-pointer"
						>
							Reactivate
						</button>
					</form>
				{/if}
			</div>

			<!-- Permanent Delete -->
			<div
				class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-[#6b1d2f]/5 border border-[#6b1d2f]/20"
			>
				<div>
					<div class="text-xs font-semibold text-[#6b1d2f]">Delete Permanently</div>
					<div class="text-[11px] text-brand-600">
						Permanently removes this envelope if it has never recorded ledger transactions.
					</div>
				</div>

				{#if !showDeleteConfirm}
					<button
						type="button"
						onclick={() => (showDeleteConfirm = true)}
						class="w-full sm:w-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#6b1d2f]/10 text-[#6b1d2f] hover:bg-[#6b1d2f]/20 transition-colors cursor-pointer"
					>
						Delete Envelope
					</button>
				{:else}
					<div class="flex items-center gap-2">
						<button
							type="button"
							onclick={() => (showDeleteConfirm = false)}
							class="px-2.5 py-1.5 rounded-lg text-xs text-brand-600 hover:bg-brand-100 cursor-pointer"
						>
							Cancel
						</button>
						<form method="POST" action="?/deleteEnvelope">
							<input type="hidden" name="name" value={envelope.name} />
							<button
								type="submit"
								class="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#6b1d2f] text-white hover:bg-[#521624] transition-colors cursor-pointer"
							>
								Confirm Delete
							</button>
						</form>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</Modal>
