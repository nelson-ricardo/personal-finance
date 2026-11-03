import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const POST: RequestHandler = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/obligations/sync-accounts`, {
		method: 'POST'
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to sync obligations from accounts: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
