<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { createEnvelopeSchema } from '#lib/schemas/envelope.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';

	let {
		open = false,
		formData,
		categories = [],
		preselectedCategory = '',
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof createEnvelopeSchema>>;
		categories: EnvelopeCategoryWithEnvelopes[];
		preselectedCategory?: string;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: createForm,
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

	$effect(() => {
		if (open) {
			if (preselectedCategory) {
				$createForm.category_name = preselectedCategory;
			} else if (categories.length > 0 && !$createForm.category_name) {
				$createForm.category_name = categories[0].name;
			}
		}
	});
</script>

<Modal
	{open}
	title="Create New Envelope"
	description="Set up an envelope bucket to allocate and spend your funds with zero-based intentionality."
	{onclose}
>
	{#if $createErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $createErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/createEnvelope" use:enhanceCreate class="space-y-4">
		<!-- Name -->
		<div>
			<label
				for="create-env-name"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Envelope Name
			</label>
			<input
				id="create-env-name"
				name="name"
				type="text"
				placeholder="e.g. Coffee, Car Insurance, Travel"
				bind:value={$createForm.name}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $createErrors.name}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$createErrors.name}</p>
			{/if}
		</div>

		<!-- Category -->
		<div>
			<label
				for="create-env-cat"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Category Group
			</label>
			<select
				id="create-env-cat"
				name="category_name"
				bind:value={$createForm.category_name}
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
				for="create-env-note"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Target or Purpose Note (Optional)
			</label>
			<input
				id="create-env-note"
				name="note"
				type="text"
				placeholder="e.g. $150 monthly limit"
				bind:value={$createForm.note}
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
				disabled={$creating}
				class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer text-center"
			>
				{$creating ? 'Creating...' : 'Create Envelope'}
			</button>
		</div>
	</form>
</Modal>
