import { error, fail } from '@sveltejs/kit';

import {
	AccountsListSchema,
	createAccountSchema,
	updateAccountSchema
} from '#lib/schemas/account.ts';
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
		} else if (lower.includes('delete') || lower.includes('archive') || lower.includes('active')) {
			setError(form, 'is_active', detail);
		} else if (lower.includes('due_date') || lower.includes('due date')) {
			setError(form, 'due_date', detail);
		} else if (lower.includes('statement')) {
			setError(form, 'total_statement_balance', detail);
		} else if (lower.includes('interest')) {
			setError(form, 'interest_saving_balance', detail);
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
	const showAll = url.searchParams.get('all') === 'true';
	const endpoint = showAll
		? 'http://127.0.0.1:8000/accounts/'
		: 'http://127.0.0.1:8000/accounts/?is_active=true';

	const res = await fetch(endpoint);

	if (!res.ok) {
		throw error(res.status, 'Could not fetch accounts from backend');
	}

	const raw = await res.json();

	const createForm = await superValidate(zod(createAccountSchema), {
		id: 'create-account-form'
	});

	const updateForm = await superValidate(zod(updateAccountSchema), {
		id: 'update-account-form'
	});

	const accounts = AccountsListSchema.parse(raw);

	return { accounts, createForm, updateForm, showAll };
};

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createAccountSchema), {
			id: 'create-account-form'
		});

		if (!form.valid) {
			return fail(400, { createForm: form });
		}

		const res = await fetch('http://127.0.0.1:8000/accounts', {
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

		const res = await fetch(`http://127.0.0.1:8000/accounts/${form.data.id}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});

		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update account');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, { updateForm: form });
		}

		return { updateForm: form };
	}
};
