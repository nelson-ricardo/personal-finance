import { error, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import {
	createExpenseSchema,
	createFinancedSchema,
	quickAddSchema,
	updateTransactionSchema,
	updateFinancedSchema,
	deleteTransactionSchema,
	bulkReconcileSchema,
	type TransactionItem
} from '#lib/schemas/transaction.ts';
import { AccountsListSchema } from '#lib/schemas/account.ts';
import { CategoriesWithEnvelopesSchema } from '#lib/schemas/category.ts';
import { getLocalDateString } from '#lib/utils/formatters.ts';
import { getApiBaseUrl } from '#lib/server/api.ts';
import {
	setError,
	setMessage,
	superValidate,
	type ErrorStatus,
	type SuperValidated
} from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';

async function handleApiError(
	form: SuperValidated<Record<string, unknown>>,
	res: Response,
	fallbackMessage: string
) {
	const status: ErrorStatus =
		res.status >= 400 && res.status < 600 ? (res.status as ErrorStatus) : 400;
	const errData = await res.json().catch(() => null);
	const detail = errData?.detail;

	if (typeof detail === 'string') {
		const lower = detail.toLowerCase();
		if (lower.includes('merchant')) {
			setError(form, 'merchant', detail);
		} else if (lower.includes('account') || lower.includes('payment_method')) {
			setError(form, 'payment_method_name', detail);
		} else if (lower.includes('amount')) {
			setError(form, 'amount', detail);
		} else if (lower.includes('term')) {
			setError(form, 'term', detail);
		} else {
			setMessage(form, detail, { status });
		}
	} else if (Array.isArray(detail)) {
		for (const err of detail) {
			const field = err.loc?.[err.loc.length - 1];
			if (field && typeof field === 'string' && field in form.data) {
				setError(form, field, err.msg);
			} else {
				setMessage(form, err.msg || 'Validation error', { status: 400 });
			}
		}
	} else {
		setMessage(form, fallbackMessage, { status });
	}
}

function getDefaultDateRange(): { dateFrom: string; dateTo: string } {
	const now = new Date();
	const year = now.getFullYear();
	const month = String(now.getMonth() + 1).padStart(2, '0');
	const dateFrom = `${year}-${month}-01`;
	const dateTo = getLocalDateString(now);
	return { dateFrom, dateTo };
}

export const load: PageServerLoad = async ({ fetch, url }) => {
	const allTime = url.searchParams.get('all_time') === 'true';
	const defaults = getDefaultDateRange();

	const dateFromParam = url.searchParams.get('date_from');
	const dateToParam = url.searchParams.get('date_to');

	let date_from: string | null = null;
	let date_to: string | null = null;

	if (!allTime) {
		date_from = dateFromParam !== null ? dateFromParam : defaults.dateFrom;
		date_to = dateToParam !== null ? dateToParam : defaults.dateTo;
	}

	const account = url.searchParams.get('account') || null;
	const envelope = url.searchParams.get('envelope') || null;
	const transaction_type = url.searchParams.get('transaction_type') || null;
	const include_reversed = url.searchParams.get('include_reversed') === 'true';
	const searchQuery = url.searchParams.get('q') || '';

	// Build API URL for fetching transactions
	const apiBase = getApiBaseUrl();
	const apiUrl = new URL(`${apiBase}/transactions/`);
	if (date_from) apiUrl.searchParams.set('date_from', date_from);
	if (date_to) apiUrl.searchParams.set('date_to', date_to);
	if (account) apiUrl.searchParams.set('account', account);
	if (envelope) apiUrl.searchParams.set('envelope', envelope);
	if (transaction_type) apiUrl.searchParams.append('transaction_type', transaction_type);
	if (include_reversed) apiUrl.searchParams.set('include_reversed', 'true');

	const [txRes, acctsRes, envsRes] = await Promise.all([
		fetch(apiUrl.toString()),
		fetch(`${apiBase}/accounts/?account_type=cash&account_type=credit_card`),
		fetch(`${apiBase}/categories/with-envelopes?all=true`)
	]);

	if (!txRes.ok) {
		throw error(txRes.status, 'Failed to fetch transactions from backend');
	}
	if (!acctsRes.ok) {
		throw error(acctsRes.status, 'Failed to fetch accounts from backend');
	}
	if (!envsRes.ok) {
		throw error(envsRes.status, 'Failed to fetch envelopes from backend');
	}

	const [rawTransactions, rawAccounts, rawCategories] = await Promise.all([
		txRes.json(),
		acctsRes.json(),
		envsRes.json()
	]);

	const accounts = AccountsListSchema.parse(rawAccounts);
	const categories = CategoriesWithEnvelopesSchema.parse(rawCategories);
	const transactions = (rawTransactions as TransactionItem[]).filter(
		(tx) => tx.merchant !== 'Market Adjustment'
	);

	// Initialize superforms for all operations
	const todayStr = getLocalDateString();

	const [
		quickAddForm,
		expenseForm,
		financedForm,
		updateForm,
		updateFinancedForm,
		deleteForm,
		bulkReconcileForm
	] = await Promise.all([
		superValidate(zod(quickAddSchema), {
			id: 'quick-add',
			defaults: {
				logged_date: todayStr,
				merchant: '',
				payment_method_name:
					accounts.find((a) => a.account_type === 'cash')?.name || accounts[0]?.name || '',
				envelope_name: '',
				amount: '',
				note: ''
			}
		}),
		superValidate(zod(createExpenseSchema), {
			id: 'create-expense',
			defaults: {
				logged_date: todayStr,
				posted_date: '',
				merchant: '',
				payment_method_name: accounts[0]?.name || '',
				note: '',
				is_reconciled: false,
				total_amount: '',
				splits_json: '[]'
			}
		}),
		superValidate(zod(createFinancedSchema), {
			id: 'create-financed',
			defaults: {
				logged_date: todayStr,
				posted_date: '',
				merchant: '',
				payment_method_name:
					accounts.find((a) => a.account_type === 'credit_card')?.name || accounts[0]?.name || '',
				amount: '',
				term: 12,
				envelope_name: '',
				note: '',
				is_reconciled: false
			}
		}),
		superValidate(zod(updateTransactionSchema), { id: 'update-transaction' }),
		superValidate(zod(updateFinancedSchema), { id: 'update-financed' }),
		superValidate(zod(deleteTransactionSchema), { id: 'delete-transaction' }),
		superValidate(zod(bulkReconcileSchema), { id: 'bulk-reconcile' })
	]);

	return {
		transactions,
		accounts,
		categories,
		filters: {
			date_from,
			date_to,
			allTime,
			account,
			envelope,
			transaction_type,
			include_reversed,
			searchQuery
		},
		quickAddForm,
		expenseForm,
		financedForm,
		updateForm,
		updateFinancedForm,
		deleteForm,
		bulkReconcileForm
	};
};

export const actions: Actions = {
	quickAdd: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(quickAddSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const numAmount = parseFloat(form.data.amount);
		const formattedAmount = `-${Math.abs(numAmount).toFixed(2)}`;

		const payload = {
			merchant: form.data.merchant.trim(),
			logged_date: form.data.logged_date,
			posted_date: null,
			payment_method_name: form.data.payment_method_name,
			transaction_type: 'EXPENSE',
			note: form.data.note ? form.data.note.trim() : null,
			is_reconciled: false,
			splits: [
				{
					envelope_name: form.data.envelope_name,
					amount: formattedAmount
				}
			]
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/regular`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create transaction');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Transaction added successfully!');
	},

	createExpense: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createExpenseSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		let parsedSplits: Array<{ envelope_name: string; amount: string }>;
		try {
			parsedSplits = JSON.parse(form.data.splits_json);
			if (!Array.isArray(parsedSplits) || parsedSplits.length === 0) {
				setError(form, 'splits_json', 'At least one envelope split is required');
				return fail(400, { form });
			}
		} catch {
			setError(form, 'splits_json', 'Invalid split allocations data');
			return fail(400, { form });
		}

		// Ensure all split amounts are formatted as negative strings for expense deductions,
		// and exclude any internal balancing entries like "Credit Card Payment" which the backend automatically manages.
		const splits = parsedSplits
			.filter(
				(s) =>
					s.envelope_name !== 'Credit Card Payment' &&
					!s.envelope_name.startsWith('Credit Card Payment')
			)
			.map((s) => ({
				envelope_name: s.envelope_name,
				amount: `-${Math.abs(parseFloat(s.amount)).toFixed(2)}`
			}));

		const payload = {
			merchant: form.data.merchant.trim(),
			logged_date: form.data.logged_date,
			posted_date: form.data.posted_date || null,
			payment_method_name: form.data.payment_method_name,
			transaction_type: 'EXPENSE',
			note: form.data.note ? form.data.note.trim() : null,
			is_reconciled: form.data.is_reconciled,
			splits
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/regular`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create expense');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Expense created successfully!');
	},

	createFinanced: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createFinancedSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const payload = {
			merchant: form.data.merchant.trim(),
			logged_date: form.data.logged_date,
			posted_date: form.data.posted_date || null,
			payment_method_name: form.data.payment_method_name,
			amount: parseFloat(form.data.amount).toFixed(2),
			term: form.data.term,
			envelope_name: form.data.envelope_name ? form.data.envelope_name.trim() : null,
			note: form.data.note ? form.data.note.trim() : null,
			is_reconciled: form.data.is_reconciled
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/financed`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create financed transaction');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Financed purchase created successfully!');
	},

	updateRegular: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(updateTransactionSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const isReconciled = form.data.was_reconciled;
		const updatePayload: Record<string, unknown> = {
			merchant: form.data.merchant.trim(),
			logged_date: form.data.logged_date,
			posted_date: form.data.posted_date || null,
			note: form.data.note ? form.data.note.trim() : null,
			is_reconciled: form.data.is_reconciled
		};

		// Accounting rule: Reconciled transactions only permit metadata updates.
		// Splits and payment account cannot be sent/modified.
		if (!isReconciled) {
			if (form.data.payment_method_name) {
				updatePayload.payment_method_name = form.data.payment_method_name;
			}

			if (form.data.splits_json && form.data.splits_json.trim()) {
				try {
					const rawSplits: Array<{ envelope_name: string; amount: string }> = JSON.parse(
						form.data.splits_json
					);
					// Exclude internal CC balancing entries so the backend can recalculate balancing correctly
					const cleaned = rawSplits
						.filter(
							(s) =>
								s.envelope_name !== 'Credit Card Payment' &&
								!s.envelope_name.startsWith('Credit Card Payment')
						)
						.map((s) => ({
							envelope_name: s.envelope_name,
							amount: `-${Math.abs(parseFloat(s.amount)).toFixed(2)}`
						}));
					if (cleaned.length > 0) {
						updatePayload.splits = cleaned;
					}
				} catch {
					setError(form, 'splits_json', 'Invalid split allocations JSON');
					return fail(400, { form });
				}
			}
		}

		const res = await fetch(`${getApiBaseUrl()}/transactions/regular/${form.data.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(updatePayload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update transaction');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Transaction updated successfully!');
	},

	updateFinanced: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(updateFinancedSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const isReconciled = form.data.was_reconciled;
		const updatePayload: Record<string, unknown> = {
			merchant: form.data.merchant.trim(),
			logged_date: form.data.logged_date,
			posted_date: form.data.posted_date || null,
			note: form.data.note ? form.data.note.trim() : null,
			is_reconciled: form.data.is_reconciled
		};

		// Accounting rule: Reconciled financed transactions only permit metadata updates.
		if (!isReconciled) {
			if (form.data.payment_method_name) {
				updatePayload.payment_method_name = form.data.payment_method_name;
			}
			if (form.data.amount) {
				updatePayload.amount = parseFloat(form.data.amount).toFixed(2);
				// Backend contract: Term must be provided whenever modifying the financed amount
				updatePayload.term = form.data.term || 12;
			} else if (form.data.term) {
				updatePayload.term = form.data.term;
			}
			if (form.data.envelope_name) {
				updatePayload.envelope_name = form.data.envelope_name.trim();
			}
		}

		const res = await fetch(`${getApiBaseUrl()}/transactions/financed/${form.data.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(updatePayload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update financed transaction');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Financed transaction updated successfully!');
	},

	deleteTransaction: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(deleteTransactionSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const res = await fetch(`${getApiBaseUrl()}/transactions/${form.data.id}`, {
			method: 'DELETE'
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to delete transaction');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { form });
		}

		return setMessage(form, 'Transaction reversed and envelope funds restored.');
	},

	bulkReconcile: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(bulkReconcileSchema));
		if (!form.valid) {
			return fail(400, { form });
		}

		const ids = form.data.transaction_ids
			.split(',')
			.map((id) => parseInt(id.trim(), 10))
			.filter((id) => !isNaN(id));

		if (ids.length === 0) {
			setError(form, 'transaction_ids', 'No valid transactions selected');
			return fail(400, { form });
		}

		// Reconcile each transaction (tries regular patch first, falls back to financed patch if needed)
		let successCount = 0;
		for (const id of ids) {
			const payload = { is_reconciled: form.data.is_reconciled };
			let res = await fetch(`${getApiBaseUrl()}/transactions/regular/${id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				res = await fetch(`${getApiBaseUrl()}/transactions/financed/${id}`, {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(payload)
				});
			}
			if (res.ok) successCount++;
		}

		const label = form.data.is_reconciled ? 'reconciled' : 'unreconciled';
		return setMessage(form, `${successCount} transaction(s) marked as ${label}.`);
	}
};
