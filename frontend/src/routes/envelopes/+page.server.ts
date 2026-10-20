import { error, fail } from '@sveltejs/kit';
import {
	CategoriesWithEnvelopesSchema,
	createCategorySchema,
	updateCategorySchema
} from '#lib/schemas/category.ts';
import {
	createEnvelopeSchema,
	updateEnvelopeSchema,
	transferEnvelopeSchema,
	assignEnvelopeSchema,
	addIncomeSchema
} from '#lib/schemas/envelope.ts';
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
		} else if (lower.includes('amount') || lower.includes('balance') || lower.includes('funds')) {
			setError(form, 'amount', detail);
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
		? 'http://127.0.0.1:8000/categories/with-envelopes'
		: 'http://127.0.0.1:8000/categories/with-envelopes?is_active=true';

	const res = await fetch(endpoint);
	if (!res.ok) {
		throw error(res.status, 'Could not fetch envelope categories from backend');
	}

	const raw = await res.json();
	const categories = CategoriesWithEnvelopesSchema.parse(raw);

	const createCategoryForm = await superValidate(zod(createCategorySchema), {
		id: 'create-category-form'
	});
	const updateCategoryForm = await superValidate(zod(updateCategorySchema), {
		id: 'update-category-form'
	});
	const createEnvelopeForm = await superValidate(zod(createEnvelopeSchema), {
		id: 'create-envelope-form'
	});
	const updateEnvelopeForm = await superValidate(zod(updateEnvelopeSchema), {
		id: 'update-envelope-form'
	});
	const transferForm = await superValidate(zod(transferEnvelopeSchema), {
		id: 'transfer-envelope-form'
	});
	const assignForm = await superValidate(zod(assignEnvelopeSchema), {
		id: 'assign-envelope-form'
	});
	const incomeForm = await superValidate(zod(addIncomeSchema), {
		id: 'income-envelope-form'
	});

	return {
		categories,
		showAll,
		createCategoryForm,
		updateCategoryForm,
		createEnvelopeForm,
		updateEnvelopeForm,
		transferForm,
		assignForm,
		incomeForm
	};
};

export const actions: Actions = {
	createCategory: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createCategorySchema), {
			id: 'create-category-form'
		});
		if (!form.valid) return fail(400, { createCategoryForm: form });

		const res = await fetch('http://127.0.0.1:8000/categories/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create category');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				createCategoryForm: form
			});
		}
		return { createCategoryForm: form };
	},

	updateCategory: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(updateCategorySchema), {
			id: 'update-category-form'
		});
		if (!form.valid) return fail(400, { updateCategoryForm: form });

		const res = await fetch(
			`http://127.0.0.1:8000/categories/${encodeURIComponent(form.data.original_name)}`,
			{
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: form.data.name,
					order_index: form.data.order_index
				})
			}
		);
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update category');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				updateCategoryForm: form
			});
		}
		return { updateCategoryForm: form };
	},

	deleteCategory: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Category name is required' });

		const res = await fetch(`http://127.0.0.1:8000/categories/${encodeURIComponent(name)}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				categoryError: data?.detail || 'Failed to delete category'
			});
		}
		return { success: true };
	},

	createEnvelope: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createEnvelopeSchema), {
			id: 'create-envelope-form'
		});
		if (!form.valid) return fail(400, { createEnvelopeForm: form });

		const res = await fetch('http://127.0.0.1:8000/envelopes/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(form.data)
		});
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to create envelope');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				createEnvelopeForm: form
			});
		}
		return { createEnvelopeForm: form };
	},

	updateEnvelope: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(updateEnvelopeSchema), {
			id: 'update-envelope-form'
		});
		if (!form.valid) return fail(400, { updateEnvelopeForm: form });

		const res = await fetch(
			`http://127.0.0.1:8000/envelopes/${encodeURIComponent(form.data.original_name)}`,
			{
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: form.data.name,
					category_name: form.data.category_name,
					note: form.data.note
				})
			}
		);
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to update envelope');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				updateEnvelopeForm: form
			});
		}
		return { updateEnvelopeForm: form };
	},

	deactivateEnvelope: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Envelope name is required' });

		const res = await fetch(
			`http://127.0.0.1:8000/envelopes/${encodeURIComponent(name)}/deactivate`,
			{
				method: 'POST'
			}
		);
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				envelopeActionError: data?.detail || 'Failed to deactivate envelope'
			});
		}
		return { success: true };
	},

	activateEnvelope: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Envelope name is required' });

		const res = await fetch(
			`http://127.0.0.1:8000/envelopes/${encodeURIComponent(name)}/activate`,
			{
				method: 'POST'
			}
		);
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				envelopeActionError: data?.detail || 'Failed to activate envelope'
			});
		}
		return { success: true };
	},

	deleteEnvelope: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = formData.get('name') as string;
		if (!name) return fail(400, { message: 'Envelope name is required' });

		const res = await fetch(`http://127.0.0.1:8000/envelopes/${encodeURIComponent(name)}`, {
			method: 'DELETE'
		});
		if (!res.ok) {
			const data = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				envelopeActionError: data?.detail || 'Failed to delete envelope'
			});
		}
		return { success: true };
	},

	transfer: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(transferEnvelopeSchema), {
			id: 'transfer-envelope-form'
		});
		if (!form.valid) return fail(400, { transferForm: form });

		const res = await fetch('http://127.0.0.1:8000/envelopes/transfer', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				source_envelope: form.data.source_envelope,
				destination_envelope: form.data.destination_envelope,
				amount: form.data.amount,
				note: form.data.note
			})
		});
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to transfer funds');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				transferForm: form
			});
		}
		return { transferForm: form };
	},

	assign: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(assignEnvelopeSchema), {
			id: 'assign-envelope-form'
		});
		if (!form.valid) return fail(400, { assignForm: form });

		const res = await fetch('http://127.0.0.1:8000/envelopes/assign', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				envelope_name: form.data.envelope_name,
				amount: form.data.amount,
				note: form.data.note
			})
		});
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to assign funds');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				assignForm: form
			});
		}
		return { assignForm: form };
	},

	addIncome: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(addIncomeSchema), {
			id: 'income-envelope-form'
		});
		if (!form.valid) return fail(400, { incomeForm: form });

		const res = await fetch('http://127.0.0.1:8000/envelopes/income', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				amount: form.data.amount,
				source: form.data.source,
				note: form.data.note
			})
		});
		if (!res.ok) {
			await handleApiError(form, res, 'Failed to record income');
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				incomeForm: form
			});
		}
		return { incomeForm: form };
	}
};
