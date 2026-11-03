import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const { id } = params;
	const body = await request.json();
	const apiBase = getApiBaseUrl();

	const res = await fetch(`${apiBase}/obligations/${id}/pay`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to update paid status: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
