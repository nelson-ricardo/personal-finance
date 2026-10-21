import { fail } from '@sveltejs/kit';
import { superValidate, setMessage } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import {
	CheckpointsListSchema,
	createCheckpointSchema,
	type CheckpointSummary
} from '#lib/schemas/checkpoint.ts';
import { getApiBaseUrl } from '#lib/server/api.ts';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/dev/checkpoints`).catch(() => null);

	let checkpoints: CheckpointSummary[] = [];
	if (res && res.ok) {
		const raw = await res.json().catch(() => []);
		checkpoints = CheckpointsListSchema.parse(raw);
	}

	const form = await superValidate(zod(createCheckpointSchema), { id: 'create-checkpoint-form' });

	return {
		checkpoints,
		form
	};
};

export const actions: Actions = {
	create: async ({ request, fetch }) => {
		const form = await superValidate(request, zod(createCheckpointSchema), {
			id: 'create-checkpoint-form'
		});

		if (!form.valid) {
			return fail(400, { form });
		}

		const payload = {
			name: form.data.name.trim() ? form.data.name.trim() : undefined
		};

		const res = await fetch(`${getApiBaseUrl()}/dev/checkpoints`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});

		if (!res.ok) {
			const err = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				form,
				errorMessage: err?.detail || 'Failed to create database checkpoint'
			});
		}

		const created = await res.json();
		return setMessage(form, `Snapshot '${created.name}' created and saved on server!`);
	},

	restore: async ({ request, fetch }) => {
		const formData = await request.formData();
		const id = formData.get('id') as string;

		if (!id) {
			return fail(400, { errorMessage: 'Checkpoint ID is required' });
		}

		const res = await fetch(
			`${getApiBaseUrl()}/dev/checkpoints/${encodeURIComponent(id)}/restore`,
			{
				method: 'POST'
			}
		);

		if (!res.ok) {
			const err = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				errorMessage: err?.detail || 'Failed to restore database from checkpoint'
			});
		}

		const result = await res.json();
		return {
			success: true,
			message: result.message || `Database state successfully restored from checkpoint '${id}'!`
		};
	},

	delete: async ({ request, fetch }) => {
		const formData = await request.formData();
		const id = formData.get('id') as string;

		if (!id) {
			return fail(400, { errorMessage: 'Checkpoint ID is required' });
		}

		const res = await fetch(`${getApiBaseUrl()}/dev/checkpoints/${encodeURIComponent(id)}`, {
			method: 'DELETE'
		});

		if (!res.ok) {
			const err = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				errorMessage: err?.detail || 'Failed to delete checkpoint'
			});
		}

		return {
			success: true,
			message: `Checkpoint '${id}' removed from server.`
		};
	},

	resetToSeed: async ({ fetch }) => {
		const res = await fetch(`${getApiBaseUrl()}/dev/reset`, {
			method: 'POST'
		});

		if (!res.ok) {
			const err = await res.json().catch(() => null);
			return fail(res.status >= 400 && res.status < 600 ? res.status : 400, {
				errorMessage: err?.detail || 'Failed to reset database to seed state'
			});
		}

		return {
			success: true,
			message: 'Database successfully reset to the initial template seed state!'
		};
	}
};
