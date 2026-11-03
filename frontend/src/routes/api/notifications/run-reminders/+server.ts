import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const POST: RequestHandler = async ({ fetch }) => {
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/notifications/run-reminders?force=true`, {
		method: 'POST'
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, `Failed to execute due reminders: ${text}`);
	}

	const data = await res.json();
	return json(data);
};
