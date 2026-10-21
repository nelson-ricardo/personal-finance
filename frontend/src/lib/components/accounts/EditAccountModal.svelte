<script lang="ts">
	import { superForm } from 'sveltekit-superforms';
	import type { SuperValidated, Infer } from 'sveltekit-superforms';
	import type { updateAccountSchema, Account } from '#lib/schemas/account.ts';
	import Modal from '#lib/components/Modal.svelte';

	let {
		open = false,
		formData,
		account = null,
		onclose
	}: {
		open: boolean;
		formData: SuperValidated<Infer<typeof updateAccountSchema>>;
		account: Account | null;
		onclose: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	const {
		form: editAccount,
		errors: updateErrors,
		enhance: enhanceUpdate,
		submitting: updating
	} = superForm(formData, {
		resetForm: true,
		onUpdated({ form }) {
			if (form.valid) {
				onclose();
			}
		}
	});

	$effect(() => {
		if (account && open) {
			$editAccount.id = account.id;
			$editAccount.name = account.name;
			$editAccount.total_statement_balance = account.total_statement_balance ?? undefined;
			$editAccount.interest_saving_balance = account.interest_saving_balance ?? undefined;
			$editAccount.due_date = account.due_date ?? undefined;
			$editAccount.is_active = account.is_active;
		}
	});
</script>

<Modal
	{open}
	title="Edit Account"
	description={account
		? `Update balances and schedule obligations for ID #${account.id}`
		: 'Update balances and obligations'}
	{onclose}
>
	<!-- Oxblood Error Banners -->
	{#if $updateErrors._errors}
		<div
			class="p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1"
		>
			{#each $updateErrors._errors as err, idx (idx)}
				<p>• {err}</p>
			{/each}
		</div>
	{/if}

	<form method="POST" action="?/update" use:enhanceUpdate class="space-y-3.5 sm:space-y-4">
		<input type="hidden" name="id" bind:value={$editAccount.id} />

		<!-- Account Name -->
		<div>
			<label
				for="edit-name"
				class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
			>
				Account Name
			</label>
			<input
				id="edit-name"
				name="name"
				type="text"
				bind:value={$editAccount.name}
				class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			{#if $updateErrors.name}
				<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$updateErrors.name}</p>
			{/if}
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<!-- Total Statement Balance -->
			<div>
				<label
					for="tot-statement-bal"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Statement Balance
				</label>
				<input
					id="tot-statement-bal"
					name="total_statement_balance"
					type="text"
					bind:value={$editAccount.total_statement_balance}
					placeholder="0.00"
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $updateErrors.total_statement_balance}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">
						{$updateErrors.total_statement_balance}
					</p>
				{/if}
			</div>

			<!-- Interest Saving Balance -->
			<div>
				<label
					for="int-saving-bal"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Interest Saving Balance
				</label>
				<input
					id="int-saving-bal"
					name="interest_saving_balance"
					type="text"
					bind:value={$editAccount.interest_saving_balance}
					placeholder="0.00"
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $updateErrors.interest_saving_balance}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">
						{$updateErrors.interest_saving_balance}
					</p>
				{/if}
			</div>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
			<!-- Due Date -->
			<div>
				<label
					for="due-date"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Due Date (1 - 31)
				</label>
				<input
					id="due-date"
					name="due_date"
					type="number"
					min="1"
					max="31"
					bind:value={$editAccount.due_date}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm font-mono tabular-nums text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				/>
				{#if $updateErrors.due_date}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$updateErrors.due_date}</p>
				{/if}
			</div>

			<!-- Status -->
			<div>
				<label
					for="edit-status"
					class="block text-xs font-bold text-brand-800 uppercase tracking-wider mb-1"
				>
					Account Status
				</label>
				<select
					name="is_active"
					id="edit-status"
					bind:value={$editAccount.is_active}
					class="w-full px-3 py-2.5 rounded-xl border border-brand-300 text-base sm:text-sm text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
				>
					<option value={true}>Active</option>
					<option value={false}>Archived</option>
				</select>
				{#if $updateErrors.is_active}
					<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$updateErrors.is_active}</p>
				{/if}
			</div>
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

	<!-- Account Lifecycle Actions (Archive & Reactivate) -->
	{#if account && account.name !== 'Cash'}
		<div class="mt-5 pt-4 border-t border-brand-200/80">
			<div
				class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl {account.is_active
					? 'bg-amber-50/70 border border-amber-200/80'
					: 'bg-emerald-50/70 border border-emerald-200/80'}"
			>
				<div>
					<div
						class="text-xs font-bold {account.is_active ? 'text-amber-900' : 'text-emerald-900'}"
					>
						{account.is_active ? 'Archive Account' : 'Reactivate Account'}
					</div>
					<div class="text-[11px] text-brand-600 mt-0.5 max-w-sm">
						{account.is_active
							? 'Archiving hides this account from active lists. Accounts with non-starting transactions cannot be archived.'
							: 'Reactivates this account, making it available again for transactions and budgeting.'}
					</div>
				</div>

				{#if account.is_active}
					<form method="POST" action="?/archiveAccount">
						<input type="hidden" name="name" value={account.name} />
						<button
							type="submit"
							class="w-full sm:w-auto px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 text-amber-900 hover:bg-amber-200 transition-colors cursor-pointer border border-amber-300 shadow-2xs whitespace-nowrap"
						>
							Archive Account
						</button>
					</form>
				{:else}
					<form method="POST" action="?/activateAccount">
						<input type="hidden" name="name" value={account.name} />
						<button
							type="submit"
							class="w-full sm:w-auto px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-900 hover:bg-emerald-200 transition-colors cursor-pointer border border-emerald-300 shadow-2xs whitespace-nowrap"
						>
							Reactivate Account
						</button>
					</form>
				{/if}
			</div>
		</div>
	{/if}
</Modal>
