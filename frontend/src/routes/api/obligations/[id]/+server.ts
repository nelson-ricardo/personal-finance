import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const { id } = params;
	const body = await request.json();
	const apiBase = getApiBaseUrl();

	const res = await fetch(`${apiBase}/obligations/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to update obligation: ${text}`);
	}

	const data = await res.json();
	return json(data);
};

export const DELETE: RequestHandler = async ({ params, fetch }) => {
	const { id } = params;
	const apiBase = getApiBaseUrl();

	const res = await fetch(`${apiBase}/obligations/${id}`, {
		method: 'DELETE'
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to delete obligation: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
