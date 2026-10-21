import { error, fail } from '@sveltejs/kit';
import { z } from 'zod';

import {
	AccountsListSchema,
	createAccountSchema,
	updateAccountSchema,
	paymentSchema,
	accountAdjustmentSchema,
	interestChargeSchema,
	interestEarnedSchema
} from '#lib/schemas/account.ts';
import { CategoriesWithEnvelopesSchema, EnvelopeSchema } from '#lib/schemas/category.ts';
import { getLocalDateString } from '#lib/utils/formatters.ts';
import { getApiBaseUrl } from '#lib/server/api.ts';
import type { PageServerLoad, Actions } from './$types';
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
		if (lower.includes('name') || lower.includes('exists') || lower.includes('rename')) {
			setError(form, 'name', detail);
		} else if (lower.includes('account')) {
			if ('account' in form.data) {
				setError(form, 'account', detail);
			} else if ('account_name' in form.data) {
				setError(form, 'account_name', detail);
			} else {
				setMessage(form, detail, { status });
			}
		} else if (lower.includes('envelope')) {
			if ('envelope_name' in form.data) {
				setError(form, 'envelope_name', detail);
			} else {
				setMessage(form, detail, { status });
			}
		} else if (
			lower.includes('insufficient') ||
			lower.includes('amount') ||
			lower.includes('greater than 0')
		) {
			if ('amount' in form.data) {
				setError(form, 'amount', detail);
			} else {
				setMessage(form, detail, { status });
			}
		} else if (lower.includes('target_balance') || lower.includes('balance')) {
			if ('target_balance' in form.data) {
				setError(form, 'target_balance', detail);
			} else {
				setMessage(form, detail, { status });
			}
		} else if (lower.includes('delete') || lower.includes('archive') || lower.includes('active')) {
			setError(form, 'is_active', detail);
		} else if (lower.includes('due_date') || lower.includes('due date')) {
			setError(form, 'due_date', detail);
		} else if (lower.includes('statement')) {
			setError(form, 'total_statement_balance', detail);
		} else if (lower.includes('interest')) {
			if ('interest_saving_balance' in form.data) {
				setError(form, 'interest_saving_balance', detail);
			} else {
				setMessage(form, detail, { status });
			}
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

export const load: PageServerLoad = async ({ fetch, url }) => {
	const apiBase = getApiBaseUrl();
	const showAll = url.searchParams.get('all') === 'true';
	const endpoint = showAll ? `${apiBase}/accounts/` : `${apiBase}/accounts/?is_active=true`;

	const [accountsRes, categoriesRes, envelopesRes] = await Promise.all([
		fetch(endpoint),
		fetch(`${apiBase}/categories/with-envelopes?is_active=true`),
		fetch(`${apiBase}/envelopes/?is_active=true`)
	]);

	if (!accountsRes.ok) {
		throw error(accountsRes.status, 'Could not fetch accounts from backend');
	}

	const rawAccounts = await accountsRes.json();
	const rawCategories = categoriesRes.ok ? await categoriesRes.json().catch(() => []) : [];
	const rawEnvelopes = envelopesRes.ok ? await envelopesRes.json().catch(() => []) : [];

	const today = getLocalDateString();

	const [
		createForm,
		updateForm,
		paymentForm,
		adjustmentForm,
		interestChargeForm,
		interestEarnedForm
	] = await Promise.all([
		superValidate(zod(createAccountSchema), { id: 'create-account-form' }),
		superValidate(zod(updateAccountSchema), { id: 'update-account-form' }),
		superValidate(zod(paymentSchema), { id: 'payment-form' }),
		superValidate(zod(accountAdjustmentSchema), {
			id: 'adjustment-form',
			defaults: {
				account_name: '',
				target_balance: '',
				note: '',
				envelope_name: '',
				logged_date: today
			}
		}),
		superValidate(zod(interestChargeSchema), {
			id: 'interest-charge-form',
			defaults: { account_name: '', amount: '', note: 'Interest Charge', logged_date: today }
		}),
		superValidate(zod(interestEarnedSchema), {
			id: 'interest-earned-form',
			defaults: { account_name: '', amount: '', note: 'Interest Earned', logged_date: today }
		})
	]);

	const accounts = AccountsListSchema.parse(rawAccounts);
	const categories = CategoriesWithEnvelopesSchema.parse(rawCategories);
	const envelopes = z.array(EnvelopeSchema).parse(rawEnvelopes);

	return {
		accounts,
		categories,
		envelopes,
		createForm,
		updateForm,
		paymentForm,
		adjustmentForm,
		interestChargeForm,
		interestEarnedForm,
		showAll
	};
};

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createAccountSchema), {
			id: 'create-account-form'
		});

		if (!form.valid) {
			return fail(400, { createForm: form });
		}

		const res = await fetch(`${getApiBaseUrl()}/accounts`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create account');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { createForm: form });
		}

		return { createForm: form };
	},

	update: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(updateAccountSchema), {
			id: 'update-account-form'
		});

		if (!form.valid) {
			return fail(400, { updateForm: form });
		}

		const res = await fetch(`${getApiBaseUrl()}/accounts/${form.data.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update account');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { updateForm: form });
		}

		return { updateForm: form };
	},

	makePayment: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(paymentSchema), {
			id: 'payment-form'
		});

		if (!form.valid) {
			return fail(400, { paymentForm: form });
		}

		const payload = {
			account: form.data.account.trim(),
			amount: parseFloat(form.data.amount).toFixed(2)
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/payments`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to make account payment');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { paymentForm: form });
		}

		return setMessage(
			form,
			`Payment of $${payload.amount} to ${payload.account} recorded successfully!`
		);
	},

	adjustBalance: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(accountAdjustmentSchema), {
			id: 'adjustment-form'
		});

		if (!form.valid) {
			return fail(400, { adjustmentForm: form });
		}

		const payload = {
			account_name: form.data.account_name.trim(),
			target_balance: parseFloat(form.data.target_balance).toFixed(2),
			note: form.data.note ? form.data.note.trim() : null,
			envelope_name: form.data.envelope_name ? form.data.envelope_name.trim() : null,
			logged_date: form.data.logged_date || null
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/account-adjustment`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to adjust account balance');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				adjustmentForm: form
			});
		}

		const result = await res.json().catch(() => null);
		const message =
			result?.message ||
			`Balance for ${payload.account_name} adjusted to $${payload.target_balance}!`;
		return setMessage(form, message);
	},

	addInterestCharge: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(interestChargeSchema), {
			id: 'interest-charge-form'
		});

		if (!form.valid) {
			return fail(400, { interestChargeForm: form });
		}

		const payload = {
			account_name: form.data.account_name.trim(),
			amount: parseFloat(form.data.amount).toFixed(2),
			note: form.data.note ? form.data.note.trim() : 'Interest Charge',
			logged_date: form.data.logged_date
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/interest-charge`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to log interest charge');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				interestChargeForm: form
			});
		}

		return setMessage(
			form,
			`Interest charge of $${payload.amount} logged for ${payload.account_name}!`
		);
	},

	addInterestEarned: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(interestEarnedSchema), {
			id: 'interest-earned-form'
		});

		if (!form.valid) {
			return fail(400, { interestEarnedForm: form });
		}

		const payload = {
			account_name: form.data.account_name.trim(),
			amount: parseFloat(form.data.amount).toFixed(2),
			note: form.data.note ? form.data.note.trim() : 'Interest Earned',
			logged_date: form.data.logged_date
		};

		const res = await fetch(`${getApiBaseUrl()}/transactions/interest-earned`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to log interest earned');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				interestEarnedForm: form
			});
		}

		return setMessage(
			form,
			`Interest of $${payload.amount} earned on ${payload.account_name} credited to Unassigned!`
		);
	},

	archiveAccount: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Account name is required' });

		const res = await fetch(`${getApiBaseUrl()}/accounts/${encodeURIComponent(name)}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				accountActionError: data?.detail || 'Failed to archive account'
			});
		}
		return { success: true, message: `Account '${name}' archived successfully.` };
	},

	activateAccount: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Account name is required' });

		const res = await fetch(`${getApiBaseUrl()}/accounts/${encodeURIComponent(name)}/activate`, {
			method: 'POST'
		});
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				accountActionError: data?.detail || 'Failed to activate account'
			});
		}
		return { success: true, message: `Account '${name}' reactivated successfully.` };
	}
};
