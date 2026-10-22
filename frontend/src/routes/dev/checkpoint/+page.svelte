<script lang="ts">
	import type { PageProps } from './$types';
	import { superForm } from 'sveltekit-superforms';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { formatCurrency } from '#lib/utils/formatters.ts';

	let { data }: PageProps = $props();

	// svelte-ignore state_referenced_locally
	const { form, errors, enhance, submitting } = superForm(data.form, {
		resetForm: true
	});

	function formatTimestamp(isoStr: string): string {
		if (!isoStr) return '—';
		try {
			const d = new Date(isoStr);
			return d.toLocaleString(undefined, {
				month: 'short',
				day: 'numeric',
				year: 'numeric',
				hour: 'numeric',
				minute: '2-digit',
				second: '2-digit'
			});
		} catch {
			return isoStr;
		}
	}

	function formatBytes(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<svelte:head>
	<title>Database Checkpoints — Homeledger Dev</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8 max-w-5xl mx-auto">
	<!-- Navigation Link Back to Main App Routes -->
	<div class="flex flex-wrap items-center justify-between gap-3 pt-2">
		<div class="flex items-center gap-2">
			<span
				class="text-xs font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-amber-100 text-amber-900 border border-amber-300"
			>
				🛠️ Developer Mode
			</span>
			<span class="text-xs text-brand-600 font-mono">/dev/checkpoint</span>
		</div>

		<!-- Breadcrumb Links back to regular app routes -->
		<div class="flex flex-wrap items-center gap-1.5 text-xs font-medium">
			<span class="text-brand-400">Navigate to:</span>
			<a
				href={resolve('/accounts')}
				class="px-2.5 py-1 rounded-lg bg-white border border-brand-200 text-brand-700 hover:text-brand-950 hover:bg-brand-50 transition-colors shadow-2xs"
			>
				Accounts
			</a>
			<a
				href={resolve('/envelopes')}
				class="px-2.5 py-1 rounded-lg bg-white border border-brand-200 text-brand-700 hover:text-brand-950 hover:bg-brand-50 transition-colors shadow-2xs"
			>
				Envelopes
			</a>
			<a
				href={resolve('/transactions')}
				class="px-2.5 py-1 rounded-lg bg-white border border-brand-200 text-brand-700 hover:text-brand-950 hover:bg-brand-50 transition-colors shadow-2xs"
			>
				Transactions
			</a>
			<a
				href={resolve('/')}
				class="px-2.5 py-1 rounded-lg bg-white border border-brand-200 text-brand-700 hover:text-brand-950 hover:bg-brand-50 transition-colors shadow-2xs"
			>
				Home
			</a>
		</div>
	</div>

	<!-- Flash Feedback Banners -->
	{#if page.form?.errorMessage}
		<div
			class="p-4 rounded-2xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/30 text-xs sm:text-sm font-medium flex items-center gap-2.5 shadow-2xs"
		>
			<span class="text-base">⚠️</span>
			<span>{page.form.errorMessage}</span>
		</div>
	{/if}

	{#if page.form?.message}
		<div
			class="p-4 rounded-2xl bg-emerald-50 text-emerald-900 border border-emerald-200 text-xs sm:text-sm font-medium flex items-center gap-2.5 shadow-2xs"
		>
			<span class="text-base">✅</span>
			<span>{page.form.message}</span>
		</div>
	{/if}

	<!-- Header Banner -->
	<div class="bg-white rounded-2xl border border-brand-200 p-5 sm:p-6 shadow-2xs space-y-2">
		<h1 class="text-xl sm:text-2xl font-extrabold text-brand-900 font-sans tracking-tight">
			Point-in-Time Database Snapshots
		</h1>
		<p class="text-xs sm:text-sm text-brand-600 leading-relaxed max-w-3xl">
			Create instant checkpoints of all accounts, envelopes, and transactions before testing
			experimental actions (like credit card payments or balance adjustments). If something behaves
			unexpectedly, simply restore from your checkpoint to rewind the database.
		</p>
	</div>

	<!-- Create Checkpoint Box -->
	<div class="bg-white rounded-2xl border border-brand-200 p-5 sm:p-6 shadow-2xs space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans flex items-center gap-2">
				<span>📸</span>
				<span>Create New Checkpoint</span>
			</h2>
			<span class="text-[11px] font-mono text-brand-500">Stored in server folder: checkpoints/</span
			>
		</div>

		<form method="POST" action="?/create" use:enhance class="space-y-3">
			<div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
				<div class="flex-1 min-w-0">
					<input
						type="text"
						name="name"
						bind:value={$form.name}
						placeholder="Optional label (e.g. Pre-Oct 25 CC Payment, Before Groceries Split)"
						class="w-full px-3.5 py-2.5 rounded-xl border border-brand-300 text-sm text-brand-900 placeholder:text-brand-400 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 shadow-2xs"
					/>
					{#if $errors.name}
						<p class="text-xs text-[#6b1d2f] mt-1 font-medium">{$errors.name}</p>
					{/if}
				</div>

				<button
					type="submit"
					disabled={$submitting}
					class="px-5 py-2.5 rounded-xl bg-brand-500 text-brand-50 text-xs sm:text-sm font-semibold hover:bg-brand-600 active:bg-brand-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer flex items-center justify-center gap-2 shrink-0"
				>
					{#if $submitting}
						<span>Saving Dump...</span>
					{:else}
						<span>📸 Take Snapshot</span>
					{/if}
				</button>
			</div>
		</form>
	</div>

	<!-- Checkpoints List -->
	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<h2 class="text-sm sm:text-base font-bold text-brand-900 font-sans">
				Saved Checkpoints ({data.checkpoints.length})
			</h2>
			<span class="text-xs font-mono text-brand-500">Ordered by newest first</span>
		</div>

		{#if data.checkpoints.length === 0}
			<div class="bg-white rounded-2xl border border-brand-200/80 p-8 text-center space-y-2">
				<div class="text-3xl">📦</div>
				<h3 class="text-sm font-bold text-brand-900 font-sans">No saved checkpoints yet</h3>
				<p class="text-xs text-brand-600 max-w-sm mx-auto">
					Take a snapshot above before testing payments or adjustments. Your snapshots will be
					listed here with instant 1-click restore.
				</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each data.checkpoints as checkpoint (checkpoint.id)}
					<div
						class="bg-white rounded-2xl border border-brand-200/90 p-4 sm:p-5 shadow-2xs hover:shadow-xs transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-4"
					>
						<!-- Left: Metadata & Stats -->
						<div class="space-y-2 min-w-0">
							<div class="flex flex-wrap items-center gap-2">
								<h3 class="text-sm sm:text-base font-bold text-brand-900 font-sans truncate">
									{checkpoint.name}
								</h3>
								<span
									class="text-[11px] font-mono text-brand-500 bg-brand-100/70 px-2 py-0.5 rounded-md"
								>
									{formatTimestamp(checkpoint.created_at)}
								</span>
								<span class="text-[11px] font-mono text-brand-400">
									({formatBytes(checkpoint.size_bytes)})
								</span>
							</div>

							<!-- Financial Overview Snapshot -->
							<div class="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
								<div
									class="flex items-center gap-1 font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200"
								>
									<span class="font-sans font-semibold text-[11px]">Cash:</span>
									<span class="font-bold tabular-nums"
										>{formatCurrency(checkpoint.stats.total_cash)}</span
									>
								</div>

								<div
									class="flex items-center gap-1 font-mono text-brand-900 bg-brand-100/60 px-2 py-0.5 rounded-md border border-brand-200"
								>
									<span class="font-sans font-semibold text-[11px]">Debt:</span>
									<span class="font-bold tabular-nums"
										>{formatCurrency(checkpoint.stats.total_debt)}</span
									>
								</div>

								<div class="flex items-center gap-2 text-brand-600 font-mono text-[11px]">
									<span>{checkpoint.stats.accounts_count} Accounts</span>
									<span>•</span>
									<span>{checkpoint.stats.envelopes_count} Envelopes</span>
									<span>•</span>
									<span>{checkpoint.stats.transactions_count} Transactions</span>
								</div>
							</div>
						</div>

						<!-- Right: Actions -->
						<div
							class="flex items-center gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-brand-100"
						>
							<!-- Restore Form -->
							<form method="POST" action="?/restore">
								<input type="hidden" name="id" value={checkpoint.id} />
								<button
									type="submit"
									onclick={(e) => {
										if (
											!confirm(
												`⚠️ RESTORE DATABASE WARNING:\n\nAre you sure you want to restore from '${checkpoint.name}'?\n\nAll current database transactions and balances created after this checkpoint will be replaced.`
											)
										) {
											e.preventDefault();
										}
									}}
									class="px-3.5 py-1.5 rounded-xl text-xs font-semibold text-emerald-900 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 transition-colors cursor-pointer flex items-center gap-1.5 shadow-2xs"
									title="Restore database state from this snapshot"
								>
									<span>🔄</span>
									<span>Restore State</span>
								</button>
							</form>

							<!-- Delete Form -->
							<form method="POST" action="?/delete">
								<input type="hidden" name="id" value={checkpoint.id} />
								<button
									type="submit"
									onclick={(e) => {
										if (
											!confirm(
												`Delete checkpoint '${checkpoint.name}' from the server? This cannot be undone.`
											)
										) {
											e.preventDefault();
										}
									}}
									class="px-2.5 py-1.5 rounded-xl text-xs font-semibold text-[#6b1d2f] hover:bg-[#6b1d2f]/10 border border-[#6b1d2f]/20 transition-colors cursor-pointer"
									title="Delete this snapshot file from server"
								>
									🗑️
								</button>
							</form>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Reset to Initial Seed State Section -->
	<div class="bg-white rounded-2xl border border-brand-200/90 p-5 sm:p-6 shadow-2xs space-y-3">
		<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
			<div>
				<h3 class="text-sm sm:text-base font-bold text-brand-900 font-sans flex items-center gap-2">
					<span>⚡</span>
					<span>Reset Database to Seed State</span>
				</h3>
				<p class="text-xs text-brand-600 mt-0.5 max-w-xl leading-relaxed">
					Triggers the backend <code
						class="px-1.5 py-0.5 rounded bg-brand-100 text-brand-800 font-mono text-[11px]"
						>POST /dev/reset</code
					> endpoint to discard current live data and recreate the database from the original template
					seed.
				</p>
			</div>

			<form method="POST" action="?/resetToSeed" class="shrink-0">
				<button
					type="submit"
					onclick={(e) => {
						if (
							!confirm(
								'⚠️ RESET TO SEED STATE WARNING:\n\nAre you sure you want to reset the database to the template seed state?\n\nAll current live accounts, envelopes, and transactions will be replaced.'
							)
						) {
							e.preventDefault();
						}
					}}
					class="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 font-semibold text-xs sm:text-sm transition-colors shadow-2xs cursor-pointer flex items-center justify-center gap-2"
				>
					<span>🔄</span>
					<span>Reset to Seed State</span>
				</button>
			</form>
		</div>
	</div>
</div>
