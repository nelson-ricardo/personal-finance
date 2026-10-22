import { fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { AccountsListSchema } from '#lib/schemas/account.ts';
import { CategoriesWithEnvelopesSchema } from '#lib/schemas/category.ts';
import {
	TransactionItemSchema,
	quickAddSchema,
	type TransactionItem
} from '#lib/schemas/transaction.ts';
import { transferEnvelopeSchema } from '#lib/schemas/envelope.ts';
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
import { z } from 'zod';

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
		setMessage(form, detail, { status });
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

export const load: PageServerLoad = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();

	const [acctsRes, catsRes, txRes] = await Promise.all([
		fetch(`${apiBase}/accounts/?is_active=true`),
		fetch(`${apiBase}/categories/with-envelopes?is_active=true`),
		fetch(`${apiBase}/transactions/`)
	]);

	const rawAccounts = acctsRes.ok ? await acctsRes.json().catch(() => []) : [];
	const rawCategories = catsRes.ok ? await catsRes.json().catch(() => []) : [];
	const rawTransactions = txRes.ok ? await txRes.json().catch(() => []) : [];

	const accounts = AccountsListSchema.parse(rawAccounts);
	const categories = CategoriesWithEnvelopesSchema.parse(rawCategories);
	const transactionsList = z
		.array(TransactionItemSchema)
		.parse(rawTransactions)
		.filter((tx) => tx.merchant !== 'Market Adjustment');

	// Sort transactions descending by date & ID, slice to top 6
	const recentTransactions: TransactionItem[] = [...transactionsList]
		.sort((a, b) => {
			const dCompare = b.logged_date.localeCompare(a.logged_date);
			return dCompare !== 0 ? dCompare : b.id - a.id;
		})
		.slice(0, 6);

	const today = getLocalDateString();
	const quickAddForm = await superValidate(zod(quickAddSchema), {
		id: 'home-quick-add-form',
		defaults: {
			logged_date: today,
			merchant: '',
			payment_method_name: '',
			envelope_name: '',
			amount: '',
			note: ''
		}
	});

	const transferForm = await superValidate(zod(transferEnvelopeSchema), {
		id: 'home-transfer-form'
	});

	return {
		accounts,
		categories,
		recentTransactions,
		quickAddForm,
		transferForm
	};
};

export const actions: Actions = {
	quickAdd: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(quickAddSchema));
		if (!form.valid) {
			return fail(400, { quickAddForm: form });
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
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				quickAddForm: form
			});
		}

		return setMessage(form, 'Transaction added!');
	},

	transfer: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(transferEnvelopeSchema));
		if (!form.valid) return fail(400, { transferForm: form });

		const res = await fetch(`${getApiBaseUrl()}/envelopes/transfer`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to transfer funds');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				transferForm: form
			});
		}

		return setMessage(form, 'Transfer completed!');
	}
};
