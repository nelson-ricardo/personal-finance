<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type {
		createCategorySchema,
		updateCategorySchema,
		EnvelopeCategoryWithEnvelopes
	} from '#lib/schemas/category.ts';
	import Modal from '#lib/components/Modal.svelte';

	let {
		open = false,
		category = null,
		createFormData,
		updateFormData,
		onclose
	}: {
		open: boolean;
		category: EnvelopeCategoryWithEnvelopes | null;
		createFormData: SuperValidated<Infer<typeof createCategorySchema>>;
		updateFormData: SuperValidated<Infer<typeof updateCategorySchema>>;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: createForm,
		errors: createErrors,
		enhance: enhanceCreate,
		submitting: creating
	} = superForm(createFormData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	// svelte-ignore state_referenced_locally
	const {
		form: updateForm,
		errors: updateErrors,
		enhance: enhanceUpdate,
		submitting: updating
	} = superForm(updateFormData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) onclose();
		}
	});

	let showDeleteConfirm = $state(false);

	$effect(() => {
		if (open) {
			showDeleteConfirm = false;
			if (category) {
				$updateForm.original_name = category.name;
				$updateForm.name = category.name;
				$updateForm.order_index = category.order_index;
			} else {
				$createForm.name = '';
				$createForm.order_index = 0;
			}
		}
	});

	const isEditing = $derived(category !== null);
</script>

<Modal
	{open}
	title={isEditing ? `Edit Category: ${category?.name}` : 'Create New Category'}
	description={isEditing
		? 'Update category name, presentation ordering, or delete category group.'
		: 'Group your budgeting envelopes into logical financial sections.'}
	{onclose}
>
	<!-- Oxblood Error Banners -->
	{#if isEditing && $updateErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $updateErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}
	{#if !isEditing && $createErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $createErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	{#if isEditing}
		<!-- Edit Form -->
		<form method="POST" action="?/updateCategory" use:enhanceUpdate class="space-y-4">
			<input type="hidden" name="original_name" bind:value={$updateForm.original_name} />

			<div>
				<label
					for="edit-cat-name"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Category Name
				</label>
				<input
					id="edit-cat-name"
					name="name"
					type="text"
					bind:value={$updateForm.name}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $updateErrors.name}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$updateErrors.name}</p>
				{/if}
			</div>

			<div>
				<label
					for="edit-cat-order"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Display Order Index
				</label>
				<input
					id="edit-cat-order"
					name="order_index"
					type="number"
					bind:value={$updateForm.order_index}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
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

		<!-- Delete Category Section -->
		{#if category && category.name !== 'System'}
			<div class="mt-6 pt-5 border-t border-brand-200/80">
				<div
					class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-[#6b1d2f]/5 border border-[#6b1d2f]/20"
				>
					<div>
						<div class="text-xs font-bold text-[#6b1d2f]">Delete Category</div>
						<div class="text-[11px] text-brand-600">
							Permanently deletes this category. Child envelopes should be reassigned or deleted
							first.
						</div>
					</div>

					{#if !showDeleteConfirm}
						<button
							type="button"
							onclick={() => (showDeleteConfirm = true)}
							class="w-full sm:w-auto px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#6b1d2f]/10 text-[#6b1d2f] hover:bg-[#6b1d2f]/20 transition-colors cursor-pointer shrink-0"
						>
							Delete Category
						</button>
					{:else}
						<div class="flex items-center gap-2 shrink-0">
							<button
								type="button"
								onclick={() => (showDeleteConfirm = false)}
								class="px-2.5 py-1.5 rounded-lg text-xs text-brand-600 hover:bg-brand-100 cursor-pointer"
							>
								Cancel
							</button>
							<form method="POST" action="?/deleteCategory">
								<input type="hidden" name="name" value={category.name} />
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
	{:else}
		<!-- Create Form -->
		<form method="POST" action="?/createCategory" use:enhanceCreate class="space-y-4">
			<div>
				<label
					for="create-cat-name"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Category Name
				</label>
				<input
					id="create-cat-name"
					name="name"
					type="text"
					placeholder="e.g. Subscriptions, Travel & Holidays"
					bind:value={$createForm.name}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $createErrors.name}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$createErrors.name}</p>
				{/if}
			</div>

			<div>
				<label
					for="create-cat-order"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Display Order Index
				</label>
				<input
					id="create-cat-order"
					name="order_index"
					type="number"
					bind:value={$createForm.order_index}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
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
					{$creating ? 'Creating...' : 'Create Category'}
				</button>
			</div>
		</form>
	{/if}
</Modal>
