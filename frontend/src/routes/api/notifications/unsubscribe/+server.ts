import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const DELETE: RequestHandler = async ({ url, fetch }) => {
	const endpoint = url.searchParams.get('endpoint');
	if (!endpoint) {
		throw error(400, 'Missing endpoint query parameter');
	}

	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/notifications/unsubscribe?endpoint=${encodeURIComponent(endpoint)}`, {
		method: 'DELETE'
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to unsubscribe device: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
