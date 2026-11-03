import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json().catch(() => null);
	if (!body || !Array.isArray(body) || body.length === 0) {
		throw error(400, 'Invalid payload: expected a non-empty array of transactions');
	}

	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/transactions/bulk`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		const errData = await res.json().catch(() => null);
		const detail = errData?.detail || 'Failed to process batch transactions';
		throw error(res.status >= 400 && res.status < 600 ? res.status : 400, detail);
	}

	const data = await res.json();
	return json(data, { status: 201 });
};
