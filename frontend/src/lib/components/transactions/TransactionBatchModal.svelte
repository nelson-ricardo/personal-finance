<script lang="ts">
	import type { Account } from '#lib/schemas/account.ts';
	import type { EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';
	import { getUserVisibleCategories } from '#lib/utils/categories.ts';
	import { getLocalDateString } from '#lib/utils/formatters.ts';
	import {
		downloadCsvTemplate,
		parseBatchCsv,
		getRowValidation,
		type BatchRow,
		type BatchSplit
	} from '#lib/utils/csv.ts';

	let {
		open = false,
		accounts = [],
		categories = [],
		onclose,
		onsuccess
	}: {
		open: boolean;
		accounts: Account[];
		categories: EnvelopeCategoryWithEnvelopes[];
		onclose: () => void;
		onsuccess?: () => void;
	} = $props();

	// Derived active accounts and envelopes
	const activeAccounts = $derived(
		accounts.filter(
			(a) => a.is_active && (a.account_type === 'cash' || a.account_type === 'credit_card')
		)
	);
	const activeAccountNames = $derived(activeAccounts.map((a) => a.name));

	const displayCategories = $derived(getUserVisibleCategories(categories));
	const activeEnvelopes = $derived(
		displayCategories
			.flatMap((c) => c.envelopes)
			.filter((e) => e.is_active && e.name !== 'Unassigned')
	);
	const activeEnvelopeNames = $derived(activeEnvelopes.map((e) => e.name));

	// State for batch rows
	let rows = $state<BatchRow[]>([]);
	let isSubmitting = $state(false);
	let submitError = $state<string | null>(null);
	let fileNotice = $state<string | null>(null);
	let validationSummary = $state<string[]>([]);
	let isDraggingOver = $state(false);
	let isGuideOpen = $state(false);
	let copiedText = $state<string | null>(null);

	// Trip defaults
	let defaultDate = $state(getLocalDateString());
	let defaultAccount = $state('');

	$effect(() => {
		if (activeAccounts.length > 0 && !defaultAccount) {
			defaultAccount = activeAccounts[0].name;
		}
	});

	// File input ref
	let fileInputRef: HTMLInputElement | null = $state(null);

	// Prevent background scroll when open
	$effect(() => {
		if (!open) return;
		const originalOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';

		// Seed with 3 blank rows if empty
		if (rows.length === 0) {
			addNewRow(3);
		}

		return () => {
			document.body.style.overflow = originalOverflow;
		};
	});

	function createEmptyRow(): BatchRow {
		const acc = defaultAccount || activeAccountNames[0] || '';
		const env = activeEnvelopeNames[0] || '';
		return {
			id: crypto.randomUUID(),
			selected: true,
			date: defaultDate || getLocalDateString(),
			account: acc,
			merchant: '',
			total: '',
			note: '',
			splits: [
				{
					id: crypto.randomUUID(),
					envelope: env,
					amount: ''
				}
			],
			isExpanded: false
		};
	}

	function addNewRow(count = 1) {
		const newRows: BatchRow[] = [];
		for (let i = 0; i < count; i++) {
			newRows.push(createEmptyRow());
		}
		rows = [...rows, ...newRows];
	}

	function removeRow(index: number) {
		rows = rows.filter((_, i) => i !== index);
	}

	function clearAllRows() {
		rows = [];
		addNewRow(2);
		submitError = null;
		fileNotice = null;
		validationSummary = [];
	}

	function toggleSelectAll() {
		const allSelected = actionableRows.every((r) => r.selected);
		for (const r of rows) {
			if (!isRowBlank(r)) {
				r.selected = !allSelected;
			}
		}
	}

	function applyDefaultsToAll() {
		for (const r of rows) {
			if (defaultDate) r.date = defaultDate;
			if (defaultAccount) r.account = defaultAccount;
		}
		rows = [...rows];
	}

	function addSplitToRow(row: BatchRow) {
		const validation = getRowValidation(row, activeAccountNames, activeEnvelopeNames);
		const remainderStr =
			validation.remainingBalance > 0 ? validation.remainingBalance.toFixed(2) : '';
		const newSplit: BatchSplit = {
			id: crypto.randomUUID(),
			envelope: activeEnvelopeNames[0] || '',
			amount: remainderStr
		};
		row.splits = [...row.splits, newSplit];
		row.isExpanded = true;
		rows = [...rows];
	}

	function removeSplitFromRow(row: BatchRow, splitIndex: number) {
		if (row.splits.length > 1) {
			row.splits = row.splits.filter((_, i) => i !== splitIndex);
		}
		if (row.splits.length === 1) {
			row.isExpanded = false;
		}
		rows = [...rows];
	}

	function autoBalanceSplit(row: BatchRow, splitIndex: number) {
		const validation = getRowValidation(row, activeAccountNames, activeEnvelopeNames);
		if (validation.remainingBalance !== 0) {
			const current = parseFloat(row.splits[splitIndex].amount || '0') || 0;
			const nextAmount = current + validation.remainingBalance;
			if (nextAmount > 0) {
				row.splits[splitIndex].amount = nextAmount.toFixed(2);
			}
		}
		rows = [...rows];
	}

	function syncSingleSplit(row: BatchRow) {
		if (row.splits.length === 1 && row.total) {
			row.splits[0].amount = row.total;
			rows = [...rows];
		}
	}

	function handleTotalChange(row: BatchRow) {
		if (row.splits.length === 1) {
			row.splits[0].amount = row.total;
			rows = [...rows];
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files && input.files[0]) {
			processFile(input.files[0]);
		}
		if (input) input.value = '';
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDraggingOver = false;
		if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
			processFile(e.dataTransfer.files[0]);
		}
	}

	function processFile(file: File) {
		submitError = null;
		fileNotice = null;
		validationSummary = [];
		const reader = new FileReader();
		reader.onload = (evt) => {
			const text = evt.target?.result as string;
			if (text) {
				const result = parseBatchCsv(text, activeAccountNames, activeEnvelopeNames);
				if (result.errors.length > 0) {
					submitError = result.errors.join(' ');
				}
				if (result.rows.length > 0) {
					// Override current grid
					rows = result.rows;
					fileNotice = `Loaded ${result.rows.length} transactions from "${file.name}" (replaced grid).`;
				}
			}
		};
		reader.readAsText(file);
	}

	async function handlePasteFromClipboard() {
		try {
			const text = await navigator.clipboard.readText();
			if (!text.trim()) {
				submitError = 'Clipboard is empty.';
				return;
			}
			const result = parseBatchCsv(text, activeAccountNames, activeEnvelopeNames);
			if (result.rows.length > 0) {
				rows = result.rows;
				fileNotice = `Loaded ${result.rows.length} transactions from clipboard (replaced grid).`;
				submitError = null;
				validationSummary = [];
			} else {
				submitError = 'Could not parse clipboard text into transaction rows.';
			}
		} catch {
			submitError = 'Unable to access clipboard. Please check browser permissions.';
		}
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
		copiedText = text;
		setTimeout(() => {
			if (copiedText === text) copiedText = null;
		}, 2000);
	}

	// Helper to check if a row is completely blank (e.g. placeholder rows)
	function isRowBlank(r: BatchRow): boolean {
		return (
			!r.merchant.trim() &&
			(!r.total || parseFloat(r.total) === 0) &&
			(!r.note || !r.note.trim())
		);
	}

	// Actionable rows exclude empty placeholders
	const actionableRows = $derived(rows.filter((r) => !isRowBlank(r)));
	const selectedRows = $derived(actionableRows.filter((r) => r.selected));
	const selectedCount = $derived(selectedRows.length);

	const rowsValidation = $derived(
		rows.map((r) => getRowValidation(r, activeAccountNames, activeEnvelopeNames))
	);

	const selectedValidRows = $derived(
		selectedRows.filter((r) => {
			const v = getRowValidation(r, activeAccountNames, activeEnvelopeNames);
			return v.isValid;
		})
	);

	const allSelectedAreValid = $derived(
		selectedCount > 0 && selectedRows.length === selectedValidRows.length
	);

	const selectedTotalSum = $derived(
		selectedRows.reduce((sum, r) => sum + (parseFloat(r.total || '0') || 0), 0)
	);

	const invalidCount = $derived(
		actionableRows.filter(
			(r) => !getRowValidation(r, activeAccountNames, activeEnvelopeNames).isValid
		).length
	);

	async function submitBatch() {
		submitError = null;
		validationSummary = [];

		if (selectedCount === 0) {
			submitError = 'No transactions selected to save.';
			return;
		}

		// Collect all validation errors across selected rows
		const invalidList: string[] = [];
		selectedRows.forEach((r, idx) => {
			const v = getRowValidation(r, activeAccountNames, activeEnvelopeNames);
			if (!v.isValid) {
				const name = r.merchant.trim() || `Row #${idx + 1}`;
				invalidList.push(`${name}: ${v.issues.join(' ')}`);
			}
		});

		if (invalidList.length > 0) {
			validationSummary = invalidList;
			submitError = `Please resolve ${invalidList.length} ${invalidList.length === 1 ? 'issue' : 'issues'} before saving.`;
			return;
		}

		isSubmitting = true;

		const payload = selectedRows.map((r) => ({
			merchant: r.merchant.trim(),
			logged_date: r.date,
			posted_date: null,
			payment_method_name: r.account,
			transaction_type: 'EXPENSE',
			note: r.note.trim() ? r.note.trim() : null,
			is_reconciled: false,
			splits: r.splits.map((s) => ({
				envelope_name: s.envelope,
				amount: `-${Math.abs(parseFloat(s.amount)).toFixed(2)}`
			}))
		}));

		try {
			const res = await fetch('/api/transactions/bulk', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});

			if (!res.ok) {
				const errData = await res.json().catch(() => null);
				throw new Error(errData?.message || errData?.detail || 'Failed to save batch transactions');
			}

			// Success!
			if (onsuccess) onsuccess();
			onclose();
		} catch (err: unknown) {
			submitError = err instanceof Error ? err.message : 'Unknown error occurred while submitting.';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (open && e.key === 'Escape' && !isSubmitting) {
			onclose();
		}
	}}
/>

{#if open}
	<div
		class="fixed inset-0 z-50 overflow-y-auto overscroll-contain bg-brand-900/60 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 md:p-6"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget && !isSubmitting) onclose();
		}}
	>
		<div
			class="bg-white rounded-2xl border border-brand-200 shadow-2xl w-full max-w-6xl max-h-[94vh] flex flex-col animate-in fade-in zoom-in-95 duration-150 overflow-hidden"
			role="dialog"
			tabindex="-1"
			aria-modal="true"
			aria-labelledby="batch-modal-title"
			ondragover={(e) => {
				e.preventDefault();
				isDraggingOver = true;
			}}
			ondragleave={() => (isDraggingOver = false)}
			ondrop={handleDrop}
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between px-5 py-4 border-b border-brand-100 bg-brand-50/50 flex-shrink-0"
			>
				<div>
					<div class="flex items-center gap-2.5">
						<span class="w-2.5 h-2.5 rounded-full bg-brand-500"></span>
						<h2 id="batch-modal-title" class="text-lg sm:text-xl font-extrabold text-brand-900 font-sans tracking-tight">
							Batch Transaction Entry & CSV Import
						</h2>
					</div>
					<p class="text-xs text-brand-600 mt-0.5">
						Rapidly draft multiple purchases, import a filled CSV template, and allocate single or split envelopes.
					</p>
				</div>
				<button
					type="button"
					onclick={onclose}
					disabled={isSubmitting}
					class="p-1.5 text-brand-400 hover:text-brand-700 hover:bg-brand-100/60 rounded-xl transition-colors cursor-pointer text-sm"
					title="Close (Esc)"
				>
					✕
				</button>
			</div>

			<!-- Toolbar: Template, Upload, Defaults, Guide Toggle -->
			<div class="px-5 py-3 bg-brand-50/30 border-b border-brand-200/60 flex flex-wrap items-center justify-between gap-3 flex-shrink-0">
				<!-- Left: Actions -->
				<div class="flex items-center gap-2 flex-wrap">
					<!-- Hidden file input -->
					<input
						type="file"
						accept=".csv,.txt,.tsv"
						class="hidden"
						bind:this={fileInputRef}
						onchange={handleFileSelect}
					/>

					<!-- Download template button -->
					<button
						type="button"
						onclick={() => downloadCsvTemplate(activeAccountNames, activeEnvelopeNames)}
						class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 transition-colors shadow-2xs cursor-pointer"
						title="Download a clean CSV template ready for Excel or Numbers"
					>
						<span>📥 Download CSV Template</span>
					</button>

					<!-- Upload CSV button -->
					<button
						type="button"
						onclick={() => fileInputRef?.click()}
						class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 transition-colors shadow-2xs cursor-pointer"
						title="Upload a CSV file to override the current grid"
					>
						<span>📄 Upload CSV</span>
					</button>

					<!-- Paste button -->
					<button
						type="button"
						onclick={handlePasteFromClipboard}
						class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-200 bg-white text-brand-800 text-xs font-semibold hover:bg-brand-50 transition-colors shadow-2xs cursor-pointer"
					>
						<span>📋 Paste Clipboard</span>
					</button>

					<!-- Add row button -->
					<button
						type="button"
						onclick={() => addNewRow(1)}
						class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors shadow-2xs cursor-pointer"
					>
						<span>+ Add Row</span>
					</button>

					<!-- Guide & Available Reference Toggle Button -->
					<button
						type="button"
						onclick={() => (isGuideOpen = !isGuideOpen)}
						class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-brand-300 text-brand-800 text-xs font-semibold hover:bg-brand-100/60 transition-colors shadow-2xs cursor-pointer {isGuideOpen ? 'bg-brand-100 ring-1 ring-brand-500 font-bold' : 'bg-white'}"
					>
						<span>{isGuideOpen ? '📖 Hide Guide & Reference' : '📖 Format Guide & Available Names'}</span>
					</button>
				</div>

				<!-- Right: Trip Defaults -->
				<div class="flex items-center gap-2 text-xs text-brand-700 bg-white px-3 py-1.5 rounded-xl border border-brand-200/80 shadow-2xs">
					<span class="font-bold text-brand-800 uppercase tracking-wider text-[10px]">Defaults:</span>
					<input
						type="date"
						bind:value={defaultDate}
						class="px-2 py-0.5 rounded-lg border border-brand-300 text-xs text-brand-900 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-brand-50/50"
						title="Default transaction date for new or empty rows"
					/>
					<select
						bind:value={defaultAccount}
						class="px-2 py-0.5 rounded-lg border border-brand-300 text-xs text-brand-900 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-brand-50/50"
						title="Default payment account for new or empty rows"
					>
						{#each activeAccounts as acct (acct.id)}
							<option value={acct.name}>{acct.name}</option>
						{/each}
					</select>
					<button
						type="button"
						onclick={applyDefaultsToAll}
						class="text-[11px] font-semibold text-brand-700 hover:text-brand-900 underline underline-offset-2 cursor-pointer ml-1"
						title="Fill all rows with these defaults"
					>
						Apply All
					</button>
				</div>
			</div>

			<!-- Collapsible Guide & Active Names Reference Panel -->
			{#if isGuideOpen}
				<div class="px-5 py-4 bg-brand-50/70 border-b border-brand-200/90 space-y-4 animate-in slide-in-from-top-2 duration-150 flex-shrink-0 max-h-72 overflow-y-auto">
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						<!-- Column 1: Rules & Format Instructions -->
						<div class="bg-white p-3.5 rounded-xl border border-brand-200/80 shadow-2xs space-y-2">
							<h4 class="text-xs font-bold text-brand-900 uppercase tracking-wider flex items-center gap-1.5">
								<span>📝 CSV Rules & Instructions</span>
							</h4>
							<ul class="text-xs text-brand-700 space-y-1.5 list-disc pl-4 leading-relaxed">
								<li><strong>Single Expense:</strong> 1 row per purchase. Total equals Split_Amount.</li>
								<li><strong>Multi-Split:</strong> Give rows for the same purchase the <em>same</em> <code>Tx_ID</code>. Splits must sum to the Total.</li>
								<li><strong>Excel Ready:</strong> The template contains no comment headers, so it opens cleanly in any spreadsheet editor.</li>
							</ul>
						</div>

						<!-- Column 2: Active Accounts Reference -->
						<div class="bg-white p-3.5 rounded-xl border border-brand-200/80 shadow-2xs space-y-2">
							<div class="flex items-center justify-between">
								<h4 class="text-xs font-bold text-brand-900 uppercase tracking-wider">
									Active Accounts ({activeAccounts.length})
								</h4>
								<span class="text-[10px] text-brand-500">Click to copy</span>
							</div>
							<div class="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pt-1">
								{#each activeAccounts as acct (acct.id)}
									<button
										type="button"
										onclick={() => copyToClipboard(acct.name)}
										class="px-2 py-0.5 rounded-lg bg-brand-100/70 hover:bg-brand-200 text-brand-800 text-[11px] font-mono font-medium transition-colors cursor-pointer border border-brand-200 flex items-center gap-1"
										title="Click to copy account name"
									>
										<span>{acct.name}</span>
										{#if copiedText === acct.name}
											<span class="text-emerald-700 font-bold">✓</span>
										{/if}
									</button>
								{/each}
							</div>
						</div>

						<!-- Column 3: Active Envelopes Reference -->
						<div class="bg-white p-3.5 rounded-xl border border-brand-200/80 shadow-2xs space-y-2">
							<div class="flex items-center justify-between">
								<h4 class="text-xs font-bold text-brand-900 uppercase tracking-wider">
									Active Envelopes ({activeEnvelopes.length})
								</h4>
								<span class="text-[10px] text-brand-500">Click to copy</span>
							</div>
							<div class="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pt-1">
								{#each activeEnvelopes as env (env.id)}
									<button
										type="button"
										onclick={() => copyToClipboard(env.name)}
										class="px-2 py-0.5 rounded-lg bg-brand-100/70 hover:bg-brand-200 text-brand-800 text-[11px] font-sans font-medium transition-colors cursor-pointer border border-brand-200 flex items-center gap-1"
										title="Click to copy envelope name"
									>
										<span>{env.name}</span>
										{#if copiedText === env.name}
											<span class="text-emerald-700 font-bold">✓</span>
										{/if}
									</button>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- File Override Notification -->
			{#if fileNotice}
				<div class="mx-5 mt-3 p-2.5 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-medium flex items-center justify-between animate-in fade-in duration-150">
					<div class="flex items-center gap-1.5">
						<span class="font-bold">✓</span>
						<span>{fileNotice}</span>
					</div>
					<button
						type="button"
						onclick={() => (fileNotice = null)}
						class="text-xs text-emerald-600 hover:text-emerald-900 cursor-pointer"
					>
						✕
					</button>
				</div>
			{/if}

			<!-- Drop zone banner if dragging over -->
			{#if isDraggingOver}
				<div class="mx-5 my-3 p-6 border-2 border-dashed border-brand-500 bg-brand-50 rounded-2xl text-center animate-pulse">
					<p class="text-sm font-bold text-brand-900">Drop your CSV file here to import!</p>
					<p class="text-xs text-brand-600 mt-1">This will override current rows with the contents of your file.</p>
				</div>
			{/if}

			<!-- Validation Error Summary Box -->
			{#if validationSummary.length > 0}
				<div class="mx-5 mt-3 p-3.5 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium space-y-1.5 animate-in fade-in duration-150">
					<div class="flex items-center justify-between font-bold">
						<span class="flex items-center gap-1.5">
							<span>⚠️</span>
							<span>Please fix the following {validationSummary.length} {validationSummary.length === 1 ? 'issue' : 'issues'} before saving:</span>
						</span>
						<button
							type="button"
							onclick={() => (validationSummary = [])}
							class="text-xs underline cursor-pointer hover:opacity-80"
						>
							Dismiss
						</button>
					</div>
					<ul class="list-disc pl-5 space-y-1">
						{#each validationSummary as item}
							<li>{item}</li>
						{/each}
					</ul>
				</div>
			{:else if submitError}
				<div class="mx-5 mt-3 p-3 rounded-xl bg-[#6b1d2f]/10 text-[#6b1d2f] border border-[#6b1d2f]/20 text-xs font-medium flex items-center justify-between">
					<p>⚠️ {submitError}</p>
					<button
						type="button"
						onclick={() => (submitError = null)}
						class="text-xs underline cursor-pointer hover:opacity-80"
					>
						Dismiss
					</button>
				</div>
			{/if}

			<!-- Scrollable Table Container -->
			<div class="flex-1 overflow-auto p-4 sm:p-5">
				<table class="w-full border-collapse text-left text-xs font-sans">
					<thead>
						<tr class="border-b border-brand-200 text-brand-600 font-bold uppercase tracking-wider text-[11px]">
							<th class="py-2.5 px-2 w-8 text-center">
								<input
									type="checkbox"
									checked={actionableRows.length > 0 && actionableRows.every((r) => r.selected)}
									onchange={toggleSelectAll}
									class="rounded border-brand-300 text-brand-500 focus:ring-brand-500 cursor-pointer"
									title="Select / Unselect All Actionable Rows"
								/>
							</th>
							<th class="py-2.5 px-2 w-32">Date</th>
							<th class="py-2.5 px-2 w-44">Account</th>
							<th class="py-2.5 px-2 min-w-40">Merchant</th>
							<th class="py-2.5 px-2 w-28 text-right">Total ($)</th>
							<th class="py-2.5 px-2 min-w-64">Envelope / Splits</th>
							<th class="py-2.5 px-2 min-w-36">Note</th>
							<th class="py-2.5 px-2 w-10 text-center"></th>
						</tr>
					</thead>
					<tbody class="divide-y divide-brand-100">
						{#each rows as row, rIndex (row.id)}
							{@const val = rowsValidation[rIndex]}
							{@const isMultiSplit = row.splits.length > 1}
							{@const singleSplitAmt = parseFloat(row.splits[0]?.amount || '0') || 0}
							{@const singleTotalAmt = parseFloat(row.total || '0') || 0}
							{@const hasSingleMismatch = !isMultiSplit && singleTotalAmt > 0 && Math.abs(singleTotalAmt - singleSplitAmt) >= 0.005}
							{@const isBlank = isRowBlank(row)}

							<tr
								class="hover:bg-brand-50/50 transition-colors {hasSingleMismatch ? 'bg-amber-50/90 border-l-4 border-l-amber-500' : val && !val.isValid && !isBlank ? 'bg-amber-50/30' : ''}"
							>
								<!-- Checkbox -->
								<td class="py-2 px-2 text-center align-top">
									<input
										type="checkbox"
										bind:checked={row.selected}
										class="rounded border-brand-300 text-brand-500 focus:ring-brand-500 cursor-pointer mt-1.5"
									/>
								</td>

								<!-- Date -->
								<td class="py-2 px-2 align-top">
									<input
										type="date"
										bind:value={row.date}
										class="w-full px-2 py-1 rounded-lg border text-xs font-mono {row.date ? 'border-brand-300' : 'border-[#6b1d2f] bg-[#6b1d2f]/5'} focus:ring-1 focus:ring-brand-500"
									/>
									{#if !isBlank && val && !val.isValid && val.issues.some((i) => i.toLowerCase().includes('date'))}
										<span class="text-[10px] text-[#6b1d2f] block mt-0.5 font-medium">Valid date required</span>
									{/if}
								</td>

								<!-- Account -->
								<td class="py-2 px-2 align-top">
									<select
										bind:value={row.account}
										class="w-full px-2 py-1 rounded-lg border text-xs {row.account ? 'border-brand-300' : 'border-[#6b1d2f] bg-[#6b1d2f]/5'} focus:ring-1 focus:ring-brand-500"
									>
										{#each activeAccounts as acct (acct.id)}
											<option value={acct.name}>{acct.name}</option>
										{/each}
									</select>
									{#if !isBlank && val && !val.isValid && val.issues.some((i) => i.toLowerCase().includes('account'))}
										<span class="text-[10px] text-[#6b1d2f] block mt-0.5 font-medium">Active account required</span>
									{/if}
								</td>

								<!-- Merchant -->
								<td class="py-2 px-2 align-top">
									<input
										type="text"
										placeholder="e.g. Costco, Uber, Gas"
										bind:value={row.merchant}
										class="w-full px-2.5 py-1 rounded-lg border text-xs {row.merchant.trim() ? 'border-brand-300' : 'border-[#6b1d2f] bg-[#6b1d2f]/5'} focus:ring-1 focus:ring-brand-500"
									/>
									{#if !isBlank && val && !val.isValid && val.issues.some((i) => i.toLowerCase().includes('merchant'))}
										<span class="text-[10px] text-[#6b1d2f] block mt-0.5 font-medium">Merchant required</span>
									{/if}
								</td>

								<!-- Total Amount -->
								<td class="py-2 px-2 align-top">
									<input
										type="number"
										step="0.01"
										placeholder="0.00"
										bind:value={row.total}
										oninput={() => handleTotalChange(row)}
										class="w-full px-2 py-1 rounded-lg border text-xs text-right font-mono tabular-nums {parseFloat(row.total) > 0 ? 'border-brand-300' : 'border-[#6b1d2f] bg-[#6b1d2f]/5'} focus:ring-1 focus:ring-brand-500"
									/>
									{#if !isBlank && val && !val.isValid && val.issues.some((i) => i.toLowerCase().includes('total'))}
										<span class="text-[10px] text-[#6b1d2f] block mt-0.5 font-medium">Amount &gt; $0 required</span>
									{/if}
								</td>

								<!-- Envelope / Splits Column -->
								<td class="py-2 px-2 align-top">
									{#if !isMultiSplit}
										<div class="space-y-1.5">
											<div class="flex items-center gap-1.5">
												<select
													bind:value={row.splits[0].envelope}
													class="flex-1 px-2 py-1 rounded-lg border text-xs {hasSingleMismatch ? 'border-amber-400 bg-white font-medium' : 'border-brand-300'} focus:ring-1 focus:ring-brand-500"
												>
													{#each activeEnvelopes as env (env.id)}
														<option value={env.name}>{env.name}</option>
													{/each}
												</select>
												<button
													type="button"
													onclick={() => addSplitToRow(row)}
													class="px-2 py-1 rounded-lg border border-brand-200 bg-white hover:bg-brand-50 text-brand-700 font-semibold text-[11px] whitespace-nowrap cursor-pointer transition-colors shadow-2xs"
													title="Split this purchase across multiple envelopes"
												>
													+ Split
												</button>
											</div>

											{#if !isBlank && val && !val.isValid && val.issues.some((i) => i.toLowerCase().includes('envelope'))}
												<span class="text-[10px] text-[#6b1d2f] block font-medium">Valid envelope required</span>
											{/if}

											<!-- Single-Split Discrepancy Callout & Quick Fixes -->
											{#if hasSingleMismatch}
												<div class="p-2 rounded-lg bg-amber-100/90 border border-amber-300 text-amber-900 text-[11px] space-y-1.5 animate-in fade-in duration-150">
													<div class="flex items-center justify-between font-mono font-bold">
														<span class="text-amber-950">⚠️ Amount Mismatch:</span>
														<span>Split ${singleSplitAmt.toFixed(2)} ≠ Total ${singleTotalAmt.toFixed(2)}</span>
													</div>
													<div class="flex items-center gap-1.5 pt-0.5 flex-wrap">
														<button
															type="button"
															onclick={() => syncSingleSplit(row)}
															class="px-2 py-1 rounded bg-amber-600 hover:bg-amber-700 text-white font-bold text-[10px] cursor-pointer shadow-2xs transition-colors flex items-center gap-1"
															title="Update the split amount to match the transaction total"
														>
															<span>⚡ Sync Split to ${singleTotalAmt.toFixed(2)}</span>
														</button>
														<button
															type="button"
															onclick={() => addSplitToRow(row)}
															class="px-2 py-1 rounded bg-white hover:bg-amber-50 text-amber-900 border border-amber-300 font-bold text-[10px] cursor-pointer shadow-2xs transition-colors"
															title="Add a 2nd envelope split for the remainder"
														>
															<span>+ Split Remainder (${Math.abs(val.remainingBalance).toFixed(2)})</span>
														</button>
													</div>
												</div>
											{/if}
										</div>
									{:else}
										<!-- Multi-split summary pill with expand/collapse -->
										<div class="flex items-center justify-between gap-2 bg-brand-50 border border-brand-200/80 px-2.5 py-1 rounded-lg">
											<button
												type="button"
												onclick={() => (row.isExpanded = !row.isExpanded)}
												class="flex items-center gap-1.5 font-semibold text-brand-800 text-xs cursor-pointer hover:text-brand-950"
											>
												<span>{row.splits.length} Envelopes</span>
												<span class="text-[10px] text-brand-500">{row.isExpanded ? '▲' : '▼'}</span>
											</button>

											{#if val}
												{#if Math.abs(val.remainingBalance) < 0.005}
													<span class="text-[10px] font-mono font-bold text-emerald-700 bg-emerald-100/80 px-1.5 py-0.5 rounded">
														Balanced ✓
													</span>
												{:else}
													<span class="text-[10px] font-mono font-bold text-[#6b1d2f] bg-[#6b1d2f]/10 px-1.5 py-0.5 rounded">
														{val.remainingBalance > 0 ? `-$${val.remainingBalance.toFixed(2)}` : `+$${Math.abs(val.remainingBalance).toFixed(2)}`}
													</span>
												{/if}
											{/if}
										</div>
									{/if}
								</td>

								<!-- Note -->
								<td class="py-2 px-2 align-top">
									<input
										type="text"
										placeholder="Optional memo"
										bind:value={row.note}
										class="w-full px-2 py-1 rounded-lg border border-brand-200 text-xs focus:ring-1 focus:ring-brand-500"
									/>
								</td>

								<!-- Delete Row -->
								<td class="py-2 px-2 text-center align-top">
									<button
										type="button"
										onclick={() => removeRow(rIndex)}
										class="p-1 text-brand-400 hover:text-[#6b1d2f] rounded-lg transition-colors cursor-pointer mt-0.5"
										title="Delete row"
									>
										🗑
									</button>
								</td>
							</tr>

							<!-- Expanded Split Sub-Rows -->
							{#if isMultiSplit && row.isExpanded}
								<tr class="bg-brand-50/40 border-b border-brand-100">
									<td colspan="8" class="p-3 pl-10 pr-6">
										<div class="bg-white rounded-xl border border-brand-200/90 p-3 space-y-2 shadow-2xs">
											<div class="flex items-center justify-between border-b border-brand-100 pb-1.5 text-[11px] text-brand-600 font-semibold">
												<span>Envelope Breakdown for {row.merchant || 'this purchase'}</span>
												<span>
													Allocated: <strong class="font-mono text-brand-900">${row.splits.reduce((s, x) => s + (parseFloat(x.amount) || 0), 0).toFixed(2)}</strong> of <strong class="font-mono text-brand-900">${parseFloat(row.total || '0').toFixed(2)}</strong>
												</span>
											</div>

											<div class="space-y-1.5">
												{#each row.splits as split, sIndex (split.id)}
													<div class="flex items-center gap-2">
														<span class="text-[11px] text-brand-400 font-mono w-4">#{sIndex + 1}</span>
														<select
															bind:value={split.envelope}
															class="flex-1 px-2 py-1 rounded-lg border border-brand-300 text-xs focus:ring-1 focus:ring-brand-500"
														>
															{#each activeEnvelopes as env (env.id)}
																<option value={env.name}>{env.name}</option>
															{/each}
														</select>
														<div class="relative w-28">
															<span class="absolute left-2 top-1/2 -translate-y-1/2 text-brand-400 text-xs font-mono">$</span>
															<input
																type="number"
																step="0.01"
																placeholder="0.00"
																bind:value={split.amount}
																class="w-full pl-5 pr-2 py-1 rounded-lg border border-brand-300 text-xs text-right font-mono tabular-nums focus:ring-1 focus:ring-brand-500"
															/>
														</div>

														{#if val && val.remainingBalance !== 0 && sIndex === row.splits.length - 1}
															<button
																type="button"
																onclick={() => autoBalanceSplit(row, sIndex)}
																class="px-2 py-1 rounded-lg bg-brand-100 text-brand-800 hover:bg-brand-200 text-[11px] font-semibold transition-colors cursor-pointer"
																title="Adjust this split to balance the remaining difference"
															>
																Auto-Balance
															</button>
														{/if}

														<button
															type="button"
															onclick={() => removeSplitFromRow(row, sIndex)}
															class="p-1 text-brand-400 hover:text-[#6b1d2f] text-xs cursor-pointer"
															title="Remove this split"
														>
															✕
														</button>
													</div>
												{/each}
											</div>

											<div class="flex items-center justify-between pt-1 border-t border-brand-100">
												<button
													type="button"
													onclick={() => addSplitToRow(row)}
													class="text-xs font-bold text-brand-700 hover:text-brand-900 cursor-pointer flex items-center gap-1"
												>
													<span>+ Add Another Split</span>
												</button>

												{#if val && Math.abs(val.remainingBalance) >= 0.005}
													<span class="text-xs font-mono text-[#6b1d2f] font-semibold">
														Remaining to allocate: ${val.remainingBalance.toFixed(2)}
													</span>
												{/if}
											</div>
										</div>
									</td>
								</tr>
							{/if}
						{/each}
					</tbody>
				</table>

				<!-- Empty State if rows was cleared -->
				{#if rows.length === 0}
					<div class="text-center py-12 px-4 space-y-3">
						<span class="text-3xl">📥</span>
						<h3 class="text-sm font-bold text-brand-900">No transactions in the grid</h3>
						<p class="text-xs text-brand-600 max-w-sm mx-auto">
							Drop a completed CSV file here, click "Upload CSV", or click below to start drafting manually.
						</p>
						<button
							type="button"
							onclick={() => addNewRow(3)}
							class="px-4 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs font-semibold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer"
						>
							+ Add Blank Rows
						</button>
					</div>
				{/if}
			</div>

			<!-- Footer Summary & Submit CTA -->
			<div
				class="flex flex-col sm:flex-row items-center justify-between px-5 py-4 border-t border-brand-200 bg-brand-50/60 gap-3 flex-shrink-0"
			>
				<div class="flex items-center gap-3 text-xs text-brand-700 flex-wrap">
					<span class="font-bold text-brand-900">
						{selectedCount} of {actionableRows.length} Selected
					</span>
					<span class="text-brand-300">•</span>
					<span>
						Total: <strong class="font-mono text-brand-900 font-bold">${selectedTotalSum.toFixed(2)}</strong>
					</span>
					{#if invalidCount > 0}
						<span class="text-brand-300">•</span>
						<span class="text-[#6b1d2f] font-semibold">
							⚠️ {invalidCount} {invalidCount === 1 ? 'row requires' : 'rows require'} attention
						</span>
					{/if}
				</div>

				<div class="flex items-center gap-2.5 w-full sm:w-auto justify-end">
					<button
						type="button"
						onclick={clearAllRows}
						disabled={isSubmitting}
						class="px-3.5 py-2 rounded-xl border border-brand-200 text-brand-700 hover:bg-brand-100/60 text-xs font-semibold transition-colors cursor-pointer"
					>
						Clear All
					</button>

					<button
						type="button"
						onclick={submitBatch}
						disabled={isSubmitting || selectedCount === 0}
						class="px-5 py-2 rounded-xl bg-brand-500 text-brand-50 text-xs font-bold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					>
						{#if isSubmitting}
							<span class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
							<span>Saving Transactions...</span>
						{:else}
							<span>Confirm & Save {selectedCount} Transactions</span>
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
