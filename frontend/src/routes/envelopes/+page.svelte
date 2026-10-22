<script lang="ts">
	import type { PageProps } from './$types';
	import type { Envelope, EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import type { ResolvedPathname } from '$app/types';
	import { resolve } from '$app/paths';

	import ReadyToAssignBanner from '#lib/components/envelopes/ReadyToAssignBanner.svelte';
	import CategoryAccordion from '#lib/components/envelopes/CategoryAccordion.svelte';
	import EnvelopeRow from '#lib/components/envelopes/EnvelopeRow.svelte';
	import MoveMoneyModal from '#lib/components/envelopes/MoveMoneyModal.svelte';
	import TransferModal from '#lib/components/envelopes/TransferModal.svelte';
	import AddIncomeModal from '#lib/components/envelopes/AddIncomeModal.svelte';
	import CreateEnvelopeModal from '#lib/components/envelopes/CreateEnvelopeModal.svelte';
	import EditEnvelopeModal from '#lib/components/envelopes/EditEnvelopeModal.svelte';
	import CategoryModal from '#lib/components/envelopes/CategoryModal.svelte';
	import { getUserVisibleCategories } from '#lib/utils/categories.ts';

	let { data }: PageProps = $props();

	// Modal State
	let isIncomeOpen = $state(false);
	let isTransferOpen = $state(false);
	let isCreateEnvelopeOpen = $state(false);
	let preselectedCategoryName = $state('');

	let isMoveMoneyOpen = $state(false);
	let movingEnvelope = $state<Envelope | null>(null);
	let moveMoneyInitialMode = $state<'assign' | 'return'>('assign');

	let isEditEnvelopeOpen = $state(false);
	let editingEnvelope = $state<Envelope | null>(null);

	let isCategoryModalOpen = $state(false);
	let editingCategory = $state<EnvelopeCategoryWithEnvelopes | null>(null);

	// Derived metrics & collections
	const categories = $derived(data.categories);
	const allEnvelopes = $derived(categories.flatMap((c) => c.envelopes));
	const activeEnvelopes = $derived(
		allEnvelopes.filter(
			(e) => e.is_active && e.name !== 'Unassigned' && e.name !== 'Account Adjustment'
		)
	);

	// Extract Unassigned cash balance from System category
	const unassignedEnv = $derived(allEnvelopes.find((e) => e.name === 'Unassigned'));
	const unassignedBalance = $derived(parseFloat(unassignedEnv?.balance ?? '0.00') || 0);

	// User budgeting categories: Credit Card Payments hoisted, internal system envelopes excluded
	const userCategories = $derived(getUserVisibleCategories(categories));

	const allEnvelopesUrl = `${resolve('/envelopes')}?all=true` as unknown as ResolvedPathname;
	const activeEnvelopesUrl = resolve('/envelopes');

	function openCreateEnvelope(categoryName = '') {
		preselectedCategoryName = categoryName;
		isCreateEnvelopeOpen = true;
	}

	function openMoveMoney(envelope: Envelope, mode: 'assign' | 'return' = 'assign') {
		movingEnvelope = envelope;
		moveMoneyInitialMode = mode;
		isMoveMoneyOpen = true;
	}

	function openEditEnvelope(envelope: Envelope) {
		editingEnvelope = envelope;
		isEditEnvelopeOpen = true;
	}

	function openCreateCategory() {
		editingCategory = null;
		isCategoryModalOpen = true;
	}

	function openEditCategory(category: EnvelopeCategoryWithEnvelopes) {
		editingCategory = category;
		isCategoryModalOpen = true;
	}
</script>

<svelte:head>
	<title>Envelopes — Homeledger</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8">
	<!-- Page Header with Summary & Actions -->
	<div
		class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 pb-4 border-b border-brand-200"
	>
		<div class="flex items-center gap-2.5 flex-wrap">
			<h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-brand-900 font-sans">
				Envelopes
			</h1>
			<div class="flex items-center gap-1.5 shrink-0">
				<span
					class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800 border border-brand-200"
				>
					{activeEnvelopes.length} Active
				</span>
				{#if data.showAll}
					<span
						class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300"
					>
						+ Archived
					</span>
				{/if}
			</div>
		</div>

		<!-- Top Action Toolbar -->
		<div class="grid grid-cols-2 gap-2 w-full sm:flex sm:items-center sm:gap-2 sm:w-auto">
			<!-- Toggle Archived / Active -->
			{#if !data.showAll}
				<a
					href={allEnvelopesUrl}
					class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
					title="Show both active and archived envelopes"
				>
					<svg
						class="w-3.5 h-3.5 text-brand-600 shrink-0"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 6h16M4 12h16M4 18h7"
						/>
					</svg>
					<span>Show Archived</span>
				</a>
			{:else}
				<a
					href={activeEnvelopesUrl}
					class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-brand-300 bg-brand-100 text-brand-900 text-xs font-semibold hover:bg-brand-200 shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
					title="Show only active envelopes"
				>
					<svg
						class="w-3.5 h-3.5 text-brand-700 shrink-0"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
						/>
					</svg>
					<span>Active Only</span>
				</a>
			{/if}

			<!-- Global Transfer Button -->
			<button
				type="button"
				onclick={() => (isTransferOpen = true)}
				class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
			>
				<svg
					class="w-3.5 h-3.5 text-brand-600 shrink-0"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
					/>
				</svg>
				<span>Transfer</span>
			</button>

			<!-- New Category Button -->
			<button
				type="button"
				onclick={openCreateCategory}
				class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
			>
				<svg
					class="w-3.5 h-3.5 text-brand-600 shrink-0"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 4v16m8-8H4"
					/>
				</svg>
				<span>Category</span>
			</button>

			<!-- New Envelope Primary CTA -->
			<button
				type="button"
				onclick={() => openCreateEnvelope()}
				class="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs sm:text-sm font-semibold hover:bg-brand-600 active:bg-brand-700 shadow-sm transition-colors cursor-pointer whitespace-nowrap"
			>
				<svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2.5"
						d="M12 4v16m8-8H4"
					/>
				</svg>
				<span>New Envelope</span>
			</button>
		</div>
	</div>

	<!-- Top Ready to Assign Stewardship Hero Banner -->
	<ReadyToAssignBanner {unassignedBalance} onaddincome={() => (isIncomeOpen = true)} />

	<!-- Collapsible Categories Section -->
	<section class="space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans">Budgeting Categories</h2>
			<span class="text-xs font-mono text-brand-600">
				{userCategories.length} categories • {activeEnvelopes.length} envelopes
			</span>
		</div>

		{#if userCategories.length === 0}
			<div
				class="bg-white rounded-2xl border border-dashed border-brand-300 p-8 sm:p-12 text-center space-y-4"
			>
				<div
					class="w-12 h-12 mx-auto rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center text-2xl"
				>
					✉️
				</div>
				<div class="space-y-1 max-w-sm mx-auto">
					<h3 class="text-base font-bold text-brand-900">No Categories</h3>
				</div>
				<button
					type="button"
					onclick={openCreateCategory}
					class="px-4 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer"
				>
					New Category
				</button>
			</div>
		{:else}
			<div class="space-y-4">
				{#each userCategories as category (category.name)}
					<CategoryAccordion
						{category}
						onaddenvelope={(catName) => openCreateEnvelope(catName)}
						oneditcategory={(cat) => openEditCategory(cat)}
					>
						{#each category.envelopes as envelope (envelope.name)}
							<EnvelopeRow
								{envelope}
								{unassignedBalance}
								onmove={(env, mode) => openMoveMoney(env, mode)}
								onedit={(env) => openEditEnvelope(env)}
							/>
						{/each}
					</CategoryAccordion>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Modals with Scroll Lock -->
	<AddIncomeModal
		open={isIncomeOpen}
		formData={data.incomeForm}
		onclose={() => (isIncomeOpen = false)}
	/>

	<TransferModal
		open={isTransferOpen}
		formData={data.transferForm}
		envelopes={activeEnvelopes}
		onclose={() => (isTransferOpen = false)}
	/>

	<MoveMoneyModal
		open={isMoveMoneyOpen}
		assignFormData={data.assignForm}
		transferFormData={data.transferForm}
		targetEnvelope={movingEnvelope}
		{unassignedBalance}
		initialMode={moveMoneyInitialMode}
		onclose={() => (isMoveMoneyOpen = false)}
	/>

	<CreateEnvelopeModal
		open={isCreateEnvelopeOpen}
		formData={data.createEnvelopeForm}
		categories={userCategories}
		preselectedCategory={preselectedCategoryName}
		onclose={() => (isCreateEnvelopeOpen = false)}
	/>

	<EditEnvelopeModal
		open={isEditEnvelopeOpen}
		formData={data.updateEnvelopeForm}
		envelope={editingEnvelope}
		categories={userCategories}
		onclose={() => (isEditEnvelopeOpen = false)}
	/>

	<CategoryModal
		open={isCategoryModalOpen}
		category={editingCategory}
		createFormData={data.createCategoryForm}
		updateFormData={data.updateCategoryForm}
		onclose={() => (isCategoryModalOpen = false)}
	/>
</div>
