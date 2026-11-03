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

	// Filtered obligations for display
	let displayedObligations = $derived.by(() => {
		if (selectedDay === null) return data.obligations;
		return data.obligations.filter((o) => o.due_day === selectedDay);
	});

	// Selected day's specific obligations
	let selectedDayObligations = $derived.by(() => {
		if (selectedDay === null) return [];
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

<div class="space-y-4 sm:space-y-6 animate-in fade-in duration-200">
	<!-- Page Header & Action Bar -->
	<div class="flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<h1 class="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-brand-950 font-serif truncate">
						Obligations & Due Dates
					</h1>
					<button
						type="button"
						onclick={() => (showNotificationModal = true)}
						class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-100 hover:bg-brand-200 text-brand-800 transition-colors cursor-pointer shrink-0"
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
				<p class="text-[11px] sm:text-xs text-brand-600 mt-0.5 truncate">
					Track upcoming bills, loans, and credit card payments.
				</p>
			</div>

			<!-- Mobile & Desktop Top Action Buttons -->
			<div class="flex items-center gap-1.5 shrink-0">
				<button
					type="button"
					onclick={handleSyncAccounts}
					disabled={syncingAccounts}
					class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-xl border border-brand-200 bg-white hover:bg-brand-50 text-brand-800 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
					title="Scan Credit Cards and Loans with due dates and auto-populate obligations"
				>
					<span class={syncingAccounts ? 'animate-spin' : ''}>🔄</span>
					<span class="hidden sm:inline">{syncingAccounts ? 'Syncing...' : 'Sync Accounts'}</span>
				</button>

				<button
					type="button"
					onclick={() => openCreateModal()}
					class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-xl bg-brand-500 hover:bg-brand-600 text-white transition-colors shadow-xs cursor-pointer"
				>
					<span>+</span>
					<span class="hidden sm:inline">Add Obligation</span>
					<span class="sm:hidden">Add</span>
				</button>
			</div>
		</div>
	</div>

	<!-- Sync Feedback Banner -->
	{#if syncMessage}
		<div
			class="p-2.5 rounded-xl text-xs flex items-center justify-between {syncMessage.type === 'success'
				? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
				: 'bg-rose-50 text-rose-900 border border-rose-200'}"
		>
			<span class="font-medium text-[11px] sm:text-xs leading-tight">{syncMessage.text}</span>
			<button
				type="button"
				onclick={() => (syncMessage = null)}
				class="text-brand-500 hover:text-brand-800 font-bold ml-2 cursor-pointer p-1"
			>
				✕
			</button>
		</div>
	{/if}

	<!-- Overview Metrics (Optimized for Mobile: 3 columns, clean compact typography) -->
	<div class="grid grid-cols-3 gap-2 sm:gap-4">
		<!-- Total Commitments -->
		<div class="p-2.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-0.5">
			<span class="text-[10px] sm:text-xs font-medium text-brand-600 block truncate">Total Monthly</span>
			<div class="text-sm sm:text-2xl font-bold font-mono text-brand-950 truncate">
				${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
			</div>
			<div class="text-[9px] sm:text-[11px] text-brand-500 truncate">{totalCount} bills</div>
		</div>

		<!-- Remaining Due -->
		<div class="p-2.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-0.5">
			<span class="text-[10px] sm:text-xs font-medium text-amber-700 block truncate">Remaining</span>
			<div class="text-sm sm:text-2xl font-bold font-mono text-amber-900 truncate">
				${totalRemaining.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
			</div>
			<div class="text-[9px] sm:text-[11px] text-amber-700 truncate">{totalCount - paidCount} pending</div>
		</div>

		<!-- Paid So Far -->
		<div class="p-2.5 sm:p-4 rounded-xl sm:rounded-2xl bg-white border border-brand-200/80 shadow-2xs space-y-0.5">
			<span class="text-[10px] sm:text-xs font-medium text-emerald-700 block truncate">Paid</span>
			<div class="text-sm sm:text-2xl font-bold font-mono text-emerald-900 truncate">
				${totalPaid.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
			</div>
			<div class="text-[9px] sm:text-[11px] text-emerald-700 truncate">{paidCount} done</div>
		</div>
	</div>

	<!-- Monthly Calendar Widget -->
	<div class="bg-white rounded-2xl border border-brand-200/80 shadow-2xs overflow-hidden">
		<!-- Calendar Navigation Bar -->
		<div class="p-3 sm:p-4 border-b border-brand-100 flex items-center justify-between">
			<div class="flex items-center gap-2 min-w-0">
				<h2 class="text-sm sm:text-base font-bold text-brand-950 font-serif truncate">
					{monthNames[currentMonth]} {currentYear}
				</h2>
				{#if selectedDay !== null}
					<button
						type="button"
						onclick={() => (selectedDay = null)}
						class="text-[10px] font-medium text-brand-700 bg-brand-100 hover:bg-brand-200 px-2 py-0.5 rounded-full transition-colors cursor-pointer shrink-0"
					>
						Day {selectedDay} (Clear)
					</button>
				{/if}
			</div>

			<div class="flex items-center gap-1 shrink-0">
				<button
					type="button"
					onclick={prevMonth}
					class="p-1 sm:p-1.5 rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer text-xs"
					aria-label="Previous Month"
				>
					◀
				</button>
				<button
					type="button"
					onclick={resetToToday}
					class="px-2 py-1 text-[11px] font-medium rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer"
				>
					Today
				</button>
				<button
					type="button"
					onclick={nextMonth}
					class="p-1 sm:p-1.5 rounded-lg border border-brand-200 hover:bg-brand-50 text-brand-700 transition-colors cursor-pointer text-xs"
					aria-label="Next Month"
				>
					▶
				</button>
			</div>
		</div>

		<!-- Weekday Headers -->
		<div class="grid grid-cols-7 border-b border-brand-100 bg-brand-50/50 text-center text-[10px] sm:text-[11px] font-semibold text-brand-600 py-1.5">
			<div>Su</div>
			<div>Mo</div>
			<div>Tu</div>
			<div>We</div>
			<div>Th</div>
			<div>Fr</div>
			<div>Sa</div>
		</div>

		<!-- Calendar Day Grid -->
		<div class="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-brand-100 border-b border-brand-100">
			<!-- Padding cells for offset of 1st day -->
			{#each Array(firstDayWeekday) as _}
				<div class="min-h-[46px] sm:min-h-[84px] bg-brand-50/20"></div>
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
					class="min-h-[46px] sm:min-h-[84px] p-1 sm:p-2 transition-all cursor-pointer select-none flex flex-col justify-between {isSelected
						? 'bg-brand-100 ring-2 ring-brand-500 ring-inset'
						: isToday
							? 'bg-brand-50/80 font-bold'
							: 'hover:bg-brand-50/60 bg-white'}"
				>
					<!-- Day Number Header -->
					<div class="flex items-center justify-between w-full">
						<span
							class="text-[11px] sm:text-xs font-semibold rounded-full w-4 h-4 sm:w-5 sm:h-5 flex items-center justify-center {isToday
								? 'bg-brand-500 text-white shadow-2xs'
								: 'text-brand-800'}"
						>
							{dayNumber}
						</span>

						<!-- Desktop Day Total -->
						{#if dayObls.length > 0}
							<span class="text-[10px] font-mono text-brand-500 hidden sm:inline">
								${dayObls
									.reduce((s, o) => s + Number(o.amount), 0)
									.toLocaleString('en-US', { maximumFractionDigits: 0 })}
							</span>
						{/if}
					</div>

					<!-- Mobile Indicator: Clean colored dots (prevents squeezing!) -->
					<div class="sm:hidden flex items-center justify-center gap-0.5 mt-1">
						{#each dayObls.slice(0, 3) as obl}
							<span
								class="w-1.5 h-1.5 rounded-full {obl.is_paid_this_month
									? 'bg-emerald-500'
									: obl.is_overdue
										? 'bg-rose-500'
										: obl.days_until_due <= 3 && obl.days_until_due >= 0
											? 'bg-amber-500'
											: 'bg-brand-400'}"
								title="{obl.name} (${obl.amount})"
							></span>
						{/each}
						{#if dayObls.length > 3}
							<span class="text-[8px] text-brand-600 font-bold leading-none">+</span>
						{/if}
					</div>

					<!-- Desktop Obligations Pills (visible on sm: and up) -->
					<div class="hidden sm:block space-y-1 mt-1 overflow-hidden">
						{#each dayObls as obl}
							<div
								class="text-[9px] sm:text-[10px] truncate px-1.5 py-0.5 rounded font-medium border flex items-center justify-between {obl.is_paid_this_month
									? 'bg-emerald-50 text-emerald-800 border-emerald-200 line-through opacity-80'
									: obl.is_overdue
										? 'bg-rose-50 text-rose-900 border-rose-300 font-bold'
										: obl.days_until_due <= 3 && obl.days_until_due >= 0
											? 'bg-amber-50 text-amber-900 border-amber-300 font-semibold'
											: 'bg-brand-100 text-brand-900 border-brand-200'}"
								title="{obl.name} (${obl.amount}) - {obl.note || 'Due on day ' + dayNumber}"
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

		<!-- Mobile Selected Day Quick Strip -->
		{#if selectedDay !== null && selectedDayObligations.length > 0}
			<div class="sm:hidden p-3 bg-brand-50/70 border-t border-brand-100 space-y-2">
				<div class="flex items-center justify-between text-xs font-semibold text-brand-900">
					<span>Day {selectedDay} Obligations ({selectedDayObligations.length}):</span>
					<button
						type="button"
						onclick={() => openCreateModal(selectedDay || undefined)}
						class="text-[11px] text-brand-600 font-bold cursor-pointer"
					>
						+ Add For Day {selectedDay}
					</button>
				</div>
				<div class="space-y-1.5">
					{#each selectedDayObligations as obl}
						<div class="p-2 rounded-xl bg-white border border-brand-200/80 flex items-center justify-between text-xs shadow-2xs">
							<div class="min-w-0 pr-2">
								<div class="font-semibold text-brand-900 truncate {obl.is_paid_this_month ? 'line-through text-brand-500' : ''}">
									{obl.name}
								</div>
								<div class="text-[10px] text-brand-500 truncate">
									{obl.note || 'No notes'}
								</div>
							</div>
							<div class="flex items-center gap-2 shrink-0">
								<span class="font-mono font-bold text-brand-950">
									${Number(obl.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
								</span>
								<button
									type="button"
									onclick={() => handleTogglePaid(obl.id, obl.is_paid_this_month)}
									class="px-2 py-0.5 rounded-full text-[10px] font-semibold border {obl.is_paid_this_month
										? 'bg-emerald-100 text-emerald-800 border-emerald-300'
										: 'bg-brand-100 text-brand-700 border-brand-200'}"
								>
									{obl.is_paid_this_month ? '✓ Paid' : 'Pay'}
								</button>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- 4-Column Obligations Section -->
	<div class="bg-white rounded-2xl border border-brand-200/80 shadow-2xs overflow-hidden">
		<div class="p-3.5 sm:p-5 border-b border-brand-100 flex items-center justify-between">
			<div>
				<h3 class="text-sm sm:text-base font-bold text-brand-950 font-serif">
					{selectedDay !== null ? `Obligations Due on Day ${selectedDay}` : 'All Obligations'}
				</h3>
				<p class="text-[11px] sm:text-xs text-brand-500">
					{displayedObligations.length} commitment(s) • 4 Columns: Name, Due Date, Amount, Note
				</p>
			</div>

			{#if selectedDay !== null}
				<button
					type="button"
					onclick={() => openCreateModal(selectedDay || undefined)}
					class="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-900 cursor-pointer"
				>
					<span>+ Add for Day {selectedDay}</span>
				</button>
			{/if}
		</div>

		{#if displayedObligations.length === 0}
			<div class="p-8 text-center text-brand-500 text-xs">
				<p class="font-medium text-sm text-brand-800 mb-1">No obligations found.</p>
				<p>Tap "Add Obligation" or "Sync Accounts" to track bills and debt payments.</p>
			</div>
		{:else}
			<!-- MOBILE VIEW: Apple-Style Cards (Zero horizontal scroll or squeezing) -->
			<div class="md:hidden divide-y divide-brand-100">
				{#each displayedObligations as obl (obl.id)}
					<div class="p-3.5 space-y-2 hover:bg-brand-50/40 transition-colors {obl.is_paid_this_month ? 'opacity-70 bg-brand-50/20' : ''}">
						<!-- Card Row 1: Name, Icon, and Amount -->
						<div class="flex items-start justify-between gap-2">
							<div class="min-w-0">
								<div class="font-bold text-brand-950 text-sm flex items-center gap-1.5 truncate">
									<span>{obl.account_type === 'loan' ? '🚗' : obl.account_type === 'credit_card' ? '💳' : '📄'}</span>
									<span class={obl.is_paid_this_month ? 'line-through text-brand-600' : ''}>{obl.name}</span>
								</div>
								{#if obl.account_name}
									<span class="text-[10px] text-brand-500 font-medium block">
										Linked Account: {obl.account_name}
									</span>
								{/if}
							</div>

							<!-- Amount -->
							<div class="font-mono font-bold text-base text-brand-950 shrink-0">
								${Number(obl.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
							</div>
						</div>

						<!-- Card Row 2: Due Date & Note -->
						<div class="flex flex-col gap-1 text-xs bg-brand-50/60 p-2 rounded-xl border border-brand-100">
							<div class="flex items-center justify-between">
								<span class="font-medium text-brand-700">Due: <strong>Day {obl.due_day}</strong> of month</span>
								{#if obl.is_paid_this_month}
									<span class="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
										✓ Paid for {monthNames[currentMonth]}
									</span>
								{:else if obl.is_overdue}
									<span class="text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
										⚠️ Overdue
									</span>
								{:else if obl.days_until_due === 0}
									<span class="text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
										⚡ Due Today
									</span>
								{:else if obl.days_until_due <= 3}
									<span class="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
										Due in {obl.days_until_due}d
									</span>
								{:else}
									<span class="text-[10px] text-brand-500">In {obl.days_until_due} days</span>
								{/if}
							</div>

							{#if obl.note}
								<div class="text-[11px] text-brand-600 italic border-t border-brand-200/50 pt-1 mt-0.5">
									{obl.note}
								</div>
							{/if}
						</div>

						<!-- Card Row 3: Action Buttons (Touch Friendly 40px+ heights) -->
						<div class="flex items-center justify-between pt-1">
							<button
								type="button"
								onclick={() => handleTogglePaid(obl.id, obl.is_paid_this_month)}
								class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border {obl.is_paid_this_month
									? 'bg-emerald-100 text-emerald-800 border-emerald-300 hover:bg-emerald-200'
									: 'bg-brand-500 text-white border-transparent hover:bg-brand-600 shadow-2xs'}"
							>
								<span>{obl.is_paid_this_month ? '✓ Paid' : 'Mark as Paid'}</span>
							</button>

							<div class="flex items-center gap-2">
								<button
									type="button"
									onclick={() => openEditModal(obl)}
									class="px-2.5 py-1.5 text-xs font-medium text-brand-700 rounded-lg hover:bg-brand-100 border border-brand-200 transition-colors cursor-pointer"
								>
									✏️ Edit
								</button>
								<button
									type="button"
									onclick={() => handleDeleteObligation(obl.id, obl.name)}
									class="px-2.5 py-1.5 text-xs font-medium text-rose-700 rounded-lg hover:bg-rose-50 border border-rose-200 transition-colors cursor-pointer"
								>
									🗑️
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>

			<!-- DESKTOP VIEW: Full 4-Column Table -->
			<div class="hidden md:block overflow-x-auto">
				<table class="w-full text-left border-collapse text-xs">
					<thead>
						<tr class="border-b border-brand-100 bg-brand-50/60 text-brand-700 font-semibold uppercase tracking-wider text-[10px]">
							<th class="py-3 px-4">1. Name</th>
							<th class="py-3 px-4">2. Due Date</th>
							<th class="py-3 px-4 text-right">3. Amount</th>
							<th class="py-3 px-4">4. Note</th>
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
										<span>{obl.account_type === 'loan' ? '🚗' : obl.account_type === 'credit_card' ? '💳' : '📄'}</span>
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

								<!-- Status / Paid Toggle -->
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
