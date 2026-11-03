import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const GET: RequestHandler = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/obligations/`);

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to load obligations: ${text}`);
	}

	const data = await res.json();
	return json(data);
};

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json();
	const apiBase = getApiBaseUrl();

	const res = await fetch(`${apiBase}/obligations/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to create obligation: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
