import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const GET: RequestHandler = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/notifications/vapid-public-key`);

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to retrieve VAPID public key: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
