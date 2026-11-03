<script lang="ts">
	import type { PageProps } from './$types';
	import Modal from '#lib/components/Modal.svelte';
	import NotificationSettingsModal from '#lib/components/NotificationSettingsModal.svelte';
	import { invalidateAll } from '$app/navigation';

	let { data }: PageProps = $props();

	// Calendar Navigation State
	const now = new Date();
	let currentYear = $state(now.getFullYear());
	let currentMonth = $state(now.getMonth()); // 0-indexed (0 = Jan, 10 = Nov)
	let selectedDay = $state<number | null>(null);

	// Notification modal toggle
	let showNotificationModal = $state(false);

	// Create/Edit Obligation Modal State
	let showEditModal = $state(false);
	let editingId = $state<number | null>(null);
	let formName = $state('');
	let formDueDay = $state<number>(1);
	let formAmount = $state<string>('');
	let formNote = $state('');
	let formAccountId = $state<number | null>(null);
	let formLoading = $state(false);
	let formError = $state<string | null>(null);

	// Account Sync State
	let syncingAccounts = $state(false);
	let syncMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	const monthNames = [
		'January',
		'February',
		'March',
		'April',
		'May',
		'June',
		'July',
		'August',
		'September',
		'October',
		'November',
		'December'
	];

	// Derived calendar metrics
	let daysInMonth = $derived(new Date(currentYear, currentMonth + 1, 0).getDate());
	let firstDayWeekday = $derived(new Date(currentYear, currentMonth, 1).getDay()); // 0 = Sun

	// Map obligations by due_day
	let obligationsByDay = $derived.by(() => {
		const map = new Map<number, typeof data.obligations>();
		for (const obl of data.obligations) {
			if (!obl.is_active) continue;
			const list = map.get(obl.due_day) || [];
			list.push(obl);
			map.set(obl.due_day, list);
		}
		return map;
	});

	// Totals
	let totalAmount = $derived(
		data.obligations.reduce((sum, o) => sum + (o.is_active ? Number(o.amount) : 0), 0)
	);
	let totalPaid = $derived(
		data.obligations.reduce(
			(sum, o) => sum + (o.is_active && o.is_paid_this_month ? Number(o.amount) : 0),
			0
		)
	);
	let totalRemaining = $derived(Math.max(0, totalAmount - totalPaid));
	let paidCount = $derived(data.obligations.filter((o) => o.is_active && o.is_paid_this_month).length);
	let totalCount = $derived(data.obligations.filter((o) => o.is_active).length);

	// Filtered obligations for table
	let displayedObligations = $derived.by(() => {
		if (selectedDay === null) return data.obligations;
		return data.obligations.filter((o) => o.due_day === selectedDay);
	});

	function prevMonth() {
		if (currentMonth === 0) {
			currentMonth = 11;
			currentYear -= 1;
		} else {
			currentMonth -= 1;
		}
	}

	function nextMonth() {
		if (currentMonth === 11) {
			currentMonth = 0;
			currentYear += 1;
		} else {
			currentMonth += 1;
		}
	}

	function resetToToday() {
		currentYear = now.getFullYear();
		currentMonth = now.getMonth();
		selectedDay = now.getDate();
	}

	function openCreateModal(defaultDay?: number) {
		editingId = null;
		formName = '';
		formDueDay = defaultDay || (selectedDay ? selectedDay : 1);
		formAmount = '';
		formNote = '';
		formAccountId = null;
		formError = null;
		showEditModal = true;
	}

	function openEditModal(obl: (typeof data.obligations)[0]) {
		editingId = obl.id;
		formName = obl.name;
		formDueDay = obl.due_day;
		formAmount = obl.amount.toString();
		formNote = obl.note || '';
		formAccountId = obl.account_id;
		formError = null;
		showEditModal = true;
	}

	function handleAccountSelectChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		const val = target.value;
		if (!val) {
			formAccountId = null;
			return;
		}
		const accId = Number(val);
		formAccountId = accId;

		const acc = data.allAccounts.find((a) => a.id === accId);
		if (acc) {
			if (!formName || formName === '') formName = acc.name;
			if (acc.due_date) formDueDay = acc.due_date;
			if (acc.monthly_payment && acc.monthly_payment > 0) formAmount = acc.monthly_payment.toString();
			if (!formNote || formNote.startsWith('Monthly payment')) {
				formNote = `Monthly payment for ${acc.name}`;
			}
		}
	}

	async function handleSaveObligation() {
		formLoading = true;
		formError = null;

		const parsedAmount = parseFloat(formAmount);
		if (isNaN(parsedAmount) || parsedAmount <= 0) {
			formError = 'Please enter a valid amount greater than $0.';
			formLoading = false;
			return;
		}

		if (!formName.trim()) {
			formError = 'Please enter an obligation name.';
			formLoading = false;
			return;
		}

		try {
			const payload = {
				name: formName.trim(),
				due_day: Number(formDueDay),
				amount: parsedAmount,
				note: formNote.trim() ? formNote.trim() : null,
				account_id: formAccountId
			};

			let res: Response;
			if (editingId) {
				res = await fetch(`/api/obligations/${editingId}`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
			} else {
				res = await fetch('/api/obligations', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
			}

			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || 'Failed to save obligation');
			}

			showEditModal = false;
			await invalidateAll();
		} catch (err: unknown) {
			formError = err instanceof Error ? err.message : String(err);
		} finally {
			formLoading = false;
		}
	}

	async function handleDeleteObligation(id: number, name: string) {
		if (!confirm(`Are you sure you want to delete "${name}"?`)) return;

		try {
			const res = await fetch(`/api/obligations/${id}`, { method: 'DELETE' });
			if (!res.ok) throw new Error('Failed to delete obligation');
			await invalidateAll();
		} catch (err) {
			alert(err instanceof Error ? err.message : String(err));
		}
	}

	async function handleTogglePaid(id: number, currentPaid: boolean) {
		try {
			const res = await fetch(`/api/obligations/${id}/pay`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ paid: !currentPaid })
			});
			if (!res.ok) throw new Error('Failed to update paid status');
			await invalidateAll();
		} catch (err) {
			alert(err instanceof Error ? err.message : String(err));
		}
	}

	async function handleSyncAccounts() {
		syncingAccounts = true;
		syncMessage = null;
		try {
			const res = await fetch('/api/obligations/sync-accounts', { method: 'POST' });
			if (!res.ok) throw new Error('Account sync failed');
			const result = await res.json();
			syncMessage = {
				type: 'success',
				text: `Synced: ${result.obligations_created} created, ${result.obligations_updated} updated from ${result.accounts_scanned} credit card & loan account(s).`
			};
			await invalidateAll();
		} catch (err) {
			syncMessage = {
				type: 'error',
				text: err instanceof Error ? err.message : String(err)
			};
		} finally {
			syncingAccounts = false;
		}
	}
</script>

<svelte:head>
	<title>Obligations & Due Dates — Homeledger</title>
</svelte:head>

<div class="space-y-6 sm:space-y-8 animate-in fade-in duration-200">
	<!-- Page Header & Action Bar -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<div>
			<div class="flex items-center gap-2">
				<h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-brand-950 font-serif">
					Obligations & Due Dates
				</h1>
				<button
					type="button"
					onclick={() => (showNotificationModal = true)}
					class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-brand-100 hover:bg-brand-200 text-brand-800 transition-colors cursor-pointer"
					title="Configure daily push notification timing"
				>
					<span>🔔</span>
					<span class="hidden sm:inline">
						{data.notificationSettings?.is_enabled
							? `Daily at ${data.notificationSettings.reminder_time}`
							: 'Alerts Off'}
					</span>
				</button>
			</div>
			<p class="text-xs sm:text-sm text-brand-600 mt-1">
				Track and plan obligations due by day of the month with automated push notifications.
			</p>
		</div>

		<!-- Action Buttons -->
		<div class="flex items-center gap-2">
			<button
				type="button"
				onclick={handleSyncAccounts}
				disabled={syncingAccounts}
				class="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-brand-200 bg-white hover:bg-brand-50 text-brand-800 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
				title="Scan Credit Cards and Loans with due dates and auto-populate obligations"
			>
				<span class={syncingAccounts ? 'animate-spin' : ''}>🔄</span>
				<span>{syncingAccounts ? 'Syncing...' : 'Sync Accounts'}</span>
			</button>

			<button
				type="button"
				onclick={() => openCreateModal()}
				class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 text-white transition-colors shadow-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
			>
				<span>+</span>
				<span>Add Obligation</span>
			</button>
		</div>
	</div>

	<!-- Sync Feedback Banner -->
	{#if syncMessage}
		<div
			class="p-3 rounded-xl text-xs flex items-center justify-between {syncMessage.type === 'success'
				? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
				: 'bg-rose-50 text-rose-900 border border-rose-200'}"
		>
			<span class="font-medium">{syncMessage.text}</span>
			<button
				type="button"
				onclick={() => (syncMessage = null)}
				class="text-brand-500 hover:text-brand-800 font-bold ml-2 cursor-pointer"
			>
				✕
			</button>
		</div>
	{/if}

	<!-- Overview Metrics -->
	<div class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
		<!-- Total Commitments -->
		<div class="p-4 rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-1">
			<span class="text-xs font-medium text-brand-600">Total Monthly Commitments</span>
			<div class="text-2xl font-bold font-mono text-brand-950">
				${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
			</div>
			<div class="text-[11px] text-brand-500">{totalCount} active obligation(s)</div>
		</div>

		<!-- Remaining Due -->
		<div class="p-4 rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-1">
			<span class="text-xs font-medium text-amber-700">Remaining to Pay</span>
			<div class="text-2xl font-bold font-mono text-amber-900">
				${totalRemaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
			</div>
			<div class="text-[11px] text-amber-700">{totalCount - paidCount} pending this month</div>
		</div>

		<!-- Paid So Far -->
		<div class="p-4 rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-1">
			<span class="text-xs font-medium text-emerald-700">Paid for {monthNames[currentMonth]}</span>
			<div class="text-2xl font-bold font-mono text-emerald-900">
				${totalPaid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
			</div>
			<div class="text-[11px] text-emerald-700">{paidCount} of {totalCount} satisfied</div>
		</div>
	</div>

	<!-- Monthly Calendar Widget -->
	<div class="bg-white rounded-2xl border border-brand-200/80 shadow-2xs overflow-hidden">
		<!-- Calendar Navigation Bar -->
		<div class="p-4 sm:p-5 border-b border-brand-100 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<h2 class="text-base sm:text-lg font-bold text-brand-950 font-serif">
					{monthNames[currentMonth]} {currentYear}
				</h2>
				{#if selectedDay !== null}
					<button
						type="button"
						onclick={() => (selectedDay = null)}
						class="text-[11px] font-medium text-brand-600 bg-brand-100 hover:bg-brand-200 px-2 py-0.5 rounded-full transition-colors cursor-pointer"
					>
						Day {selectedDay} selected (Clear)
					</button>
				{/if}
			</div>

			<div class="flex items-center gap-1.5">
				<button
					type="button"
					onclick={prevMonth}
					class="p-1.5 rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer"
					aria-label="Previous Month"
				>
					◀
				</button>
				<button
					type="button"
					onclick={resetToToday}
					class="px-2.5 py-1 text-xs font-medium rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer"
				>
					Today
				</button>
				<button
					type="button"
					onclick={nextMonth}
					class="p-1.5 rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer"
					aria-label="Next Month"
				>
					▶
				</button>
			</div>
		</div>

		<!-- Weekday Headers -->
		<div class="grid grid-cols-7 border-b border-brand-100 bg-brand-50/50 text-center text-[11px] font-semibold text-brand-600 py-2">
			<div>Sun</div>
			<div>Mon</div>
			<div>Tue</div>
			<div>Wed</div>
			<div>Thu</div>
			<div>Fri</div>
			<div>Sat</div>
		</div>

		<!-- Calendar Day Grid -->
		<div class="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-brand-100 border-b border-brand-100">
			<!-- Padding cells for offset of 1st day -->
			{#each Array(firstDayWeekday) as _}
				<div class="min-h-[72px] sm:min-h-[92px] bg-brand-50/30 p-1.5 sm:p-2"></div>
			{/each}

			<!-- Days of current month -->
			{#each Array(daysInMonth) as _, i}
				{@const dayNumber = i + 1}
				{@const dayObls = obligationsByDay.get(dayNumber) || []}
				{@const isToday =
					now.getFullYear() === currentYear &&
					now.getMonth() === currentMonth &&
					now.getDate() === dayNumber}
				{@const isSelected = selectedDay === dayNumber}

				<div
					onclick={() => (selectedDay = selectedDay === dayNumber ? null : dayNumber)}
					role="button"
					tabindex="0"
					onkeydown={(e) => {
						if (e.key === 'Enter') selectedDay = selectedDay === dayNumber ? null : dayNumber;
					}}
					class="min-h-[72px] sm:min-h-[92px] p-1.5 sm:p-2 transition-all cursor-pointer select-none flex flex-col justify-between {isSelected
						? 'bg-brand-100/90 ring-2 ring-brand-500 ring-inset'
						: isToday
							? 'bg-brand-50/80 font-bold'
							: 'hover:bg-brand-50/60 bg-white'}"
				>
					<!-- Day Number Header -->
					<div class="flex items-center justify-between">
						<span
							class="text-xs font-semibold rounded-full w-5 h-5 flex items-center justify-center {isToday
								? 'bg-brand-500 text-white shadow-2xs'
								: 'text-brand-800'}"
						>
							{dayNumber}
						</span>

						{#if dayObls.length > 0}
							<span class="text-[10px] font-mono text-brand-500 hidden sm:inline">
								${dayObls
									.reduce((s, o) => s + Number(o.amount), 0)
									.toLocaleString('en-US', { maximumFractionDigits: 0 })}
							</span>
						{/if}
					</div>

					<!-- Obligations Pills Inside Day Cell -->
					<div class="space-y-1 mt-1 overflow-hidden">
						{#each dayObls as obl}
							<div
								class="text-[9px] sm:text-[10px] truncate px-1.5 py-0.5 rounded font-medium border flex items-center justify-between {obl.is_paid_this_month
									? 'bg-emerald-50 text-emerald-800 border-emerald-200 line-through opacity-80'
									: obl.is_overdue
										? 'bg-rose-50 text-rose-900 border-rose-300 font-bold'
										: obl.days_until_due <= 3 && obl.days_until_due >= 0
											? 'bg-amber-50 text-amber-900 border-amber-300 font-semibold'
											: 'bg-brand-100 text-brand-900 border-brand-200'}"
								title="{obl.name} (${obl.amount}) - {obl.note || 'Due on ' + dayNumber}"
							>
								<span class="truncate">{obl.name}</span>
								<span class="ml-1 font-mono font-bold shrink-0">
									${Number(obl.amount).toLocaleString('en-US', { maximumFractionDigits: 0 })}
								</span>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<!-- 4-Column Obligations Table (as requested: Name, Due Date, Amount, Note) -->
	<div class="bg-white rounded-2xl border border-brand-200/80 shadow-2xs overflow-hidden space-y-0">
		<div class="p-4 sm:p-5 border-b border-brand-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
			<div>
				<h3 class="text-base font-bold text-brand-950 font-serif">
					{selectedDay !== null ? `Obligations Due on Day ${selectedDay}` : 'All Obligations'}
				</h3>
				<p class="text-xs text-brand-500">
					{displayedObligations.length} commitment(s) listed.
				</p>
			</div>

			{#if selectedDay !== null}
				<button
					type="button"
					onclick={() => openCreateModal(selectedDay || undefined)}
					class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-900 cursor-pointer"
				>
					<span>+ Add Obligation for Day {selectedDay}</span>
				</button>
			{/if}
		</div>

		{#if displayedObligations.length === 0}
			<div class="p-8 text-center text-brand-500 text-xs">
				<p class="font-medium text-sm text-brand-800 mb-1">No obligations found.</p>
				<p>Tap "Add Obligation" or "Sync Accounts" above to track bills and debt payments.</p>
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-left border-collapse text-xs">
					<thead>
						<tr class="border-b border-brand-100 bg-brand-50/60 text-brand-700 font-semibold uppercase tracking-wider text-[10px]">
							<th class="py-3 px-4">Name</th>
							<th class="py-3 px-4">Due Date</th>
							<th class="py-3 px-4 text-right">Amount</th>
							<th class="py-3 px-4">Note</th>
							<th class="py-3 px-4 text-center">Status / Paid</th>
							<th class="py-3 px-4 text-right">Actions</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-brand-100 text-brand-800">
						{#each displayedObligations as obl (obl.id)}
							<tr class="hover:bg-brand-50/50 transition-colors {obl.is_paid_this_month ? 'opacity-70 bg-brand-50/20' : ''}">
								<!-- 1. Name Column -->
								<td class="py-3 px-4">
									<div class="font-semibold text-brand-950 flex items-center gap-1.5">
										{#if obl.account_id}
											<span class="text-xs" title="Linked to {obl.account_name}">
												{obl.account_type === 'loan' ? '🚗' : '💳'}
											</span>
										{:else}
											<span class="text-xs">📄</span>
										{/if}
										<span class={obl.is_paid_this_month ? 'line-through text-brand-600' : ''}>
											{obl.name}
										</span>
									</div>
									{#if obl.account_name}
										<span class="text-[10px] text-brand-500 font-medium">
											Linked: {obl.account_name}
										</span>
									{/if}
								</td>

								<!-- 2. Due Date Column -->
								<td class="py-3 px-4">
									<div class="font-mono font-medium">
										Day {obl.due_day} of month
									</div>
									<div class="text-[10px]">
										{#if obl.is_paid_this_month}
											<span class="text-emerald-700 font-semibold">✓ Paid for {monthNames[currentMonth]}</span>
										{:else if obl.is_overdue}
											<span class="text-rose-700 font-bold">⚠️ Past due</span>
										{:else if obl.days_until_due === 0}
											<span class="text-rose-700 font-bold">⚡ Due Today</span>
										{:else if obl.days_until_due === 1}
											<span class="text-amber-700 font-semibold">Due tomorrow</span>
										{:else}
											<span class="text-brand-500">In {obl.days_until_due} days</span>
										{/if}
									</div>
								</td>

								<!-- 3. Amount Column -->
								<td class="py-3 px-4 text-right font-mono font-bold text-sm text-brand-950">
									${Number(obl.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
								</td>

								<!-- 4. Note Column -->
								<td class="py-3 px-4 text-brand-600 max-w-xs">
									<span class="italic">
										{obl.note || '—'}
									</span>
								</td>

								<!-- Paid Toggle Status -->
								<td class="py-3 px-4 text-center">
									<button
										type="button"
										onclick={() => handleTogglePaid(obl.id, obl.is_paid_this_month)}
										class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer border {obl.is_paid_this_month
											? 'bg-emerald-100 text-emerald-800 border-emerald-300 hover:bg-emerald-200'
											: 'bg-brand-100 text-brand-700 border-brand-200 hover:bg-brand-200'}"
									>
										<span>{obl.is_paid_this_month ? '✓ Paid' : 'Mark Paid'}</span>
									</button>
								</td>

								<!-- Actions Column -->
								<td class="py-3 px-4 text-right space-x-1.5">
									<button
										type="button"
										onclick={() => openEditModal(obl)}
										class="p-1 text-brand-600 hover:text-brand-950 rounded hover:bg-brand-100 transition-colors cursor-pointer"
										title="Edit Obligation"
									>
										✏️
									</button>
									<button
										type="button"
										onclick={() => handleDeleteObligation(obl.id, obl.name)}
										class="p-1 text-rose-600 hover:text-rose-800 rounded hover:bg-rose-50 transition-colors cursor-pointer"
										title="Delete Obligation"
									>
										🗑️
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>

<!-- Create / Edit Obligation Modal -->
<Modal
	open={showEditModal}
	onclose={() => (showEditModal = false)}
	title={editingId ? 'Edit Obligation' : 'Add New Obligation'}
	description="Configure obligation name, due day, amount, and notes."
>
	<form
		onsubmit={(e) => {
			e.preventDefault();
			handleSaveObligation();
		}}
		class="space-y-4"
	>
		<!-- Error Banner -->
		{#if formError}
			<div class="p-3 rounded-xl text-xs bg-rose-50 text-rose-900 border border-rose-200">
				{formError}
			</div>
		{/if}

		<!-- Account Link Option (Credit Card / Loan) -->
		<div>
			<label for="link-account" class="block text-xs font-semibold text-brand-800 mb-1">
				Link to Credit Card or Loan (Optional)
			</label>
			<select
				id="link-account"
				value={formAccountId || ''}
				onchange={handleAccountSelectChange}
				class="w-full text-xs px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
			>
				<option value="">— Standalone Bill (Rent, Phone, Utilities, etc.) —</option>
				{#each data.debtAccounts as acc}
					<option value={acc.id}>
						{acc.name} ({acc.account_type === 'credit_card' ? 'Credit Card' : 'Loan'})
						{acc.due_date ? `— Due ${acc.due_date}th` : ''}
						{acc.monthly_payment ? `— $${acc.monthly_payment}/mo` : ''}
					</option>
				{/each}
			</select>
			<p class="text-[11px] text-brand-500 mt-1">
				Selecting an account auto-fills name, due date, amount, and note.
			</p>
		</div>

		<!-- Column 1: Name -->
		<div>
			<label for="obl-name" class="block text-xs font-semibold text-brand-800 mb-1">
				1. Obligation Name *
			</label>
			<input
				id="obl-name"
				type="text"
				bind:value={formName}
				placeholder="e.g. Rent, Verizon Wireless, Chase Sapphire"
				required
				class="w-full text-xs px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
			/>
		</div>

		<div class="grid grid-cols-2 gap-3">
			<!-- Column 2: Due Day of Month -->
			<div>
				<label for="obl-due-day" class="block text-xs font-semibold text-brand-800 mb-1">
					2. Due Day (1–31) *
				</label>
				<input
					id="obl-due-day"
					type="number"
					min="1"
					max="31"
					bind:value={formDueDay}
					required
					class="w-full text-xs font-mono px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
				/>
			</div>

			<!-- Column 3: Amount -->
			<div>
				<label for="obl-amount" class="block text-xs font-semibold text-brand-800 mb-1">
					3. Amount ($) *
				</label>
				<input
					id="obl-amount"
					type="number"
					step="0.01"
					min="0.01"
					bind:value={formAmount}
					placeholder="0.00"
					required
					class="w-full text-xs font-mono px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
				/>
			</div>
		</div>

		<!-- Column 4: Note -->
		<div>
			<label for="obl-note" class="block text-xs font-semibold text-brand-800 mb-1">
				4. Note
			</label>
			<input
				id="obl-note"
				type="text"
				bind:value={formNote}
				placeholder="e.g. Monthly payment for Chase Sapphire"
				class="w-full text-xs px-3 py-2 rounded-xl border border-brand-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
			/>
		</div>

		<div class="pt-3 flex items-center justify-end gap-2 border-t border-brand-100">
			<button
				type="button"
				onclick={() => (showEditModal = false)}
				class="px-4 py-2 rounded-xl text-xs font-semibold text-brand-700 hover:bg-brand-100 transition-colors cursor-pointer"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={formLoading}
				class="px-5 py-2 rounded-xl text-xs font-semibold bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer"
			>
				{formLoading ? 'Saving...' : editingId ? 'Update Obligation' : 'Create Obligation'}
			</button>
		</div>
	</form>
</Modal>

<!-- Notification Reminder Settings Modal -->
<NotificationSettingsModal
	open={showNotificationModal}
	onclose={() => (showNotificationModal = false)}
/>
