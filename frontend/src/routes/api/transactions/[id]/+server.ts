import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getApiBaseUrl } from '#lib/server/api.ts';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const { id } = params;
	const apiBase = getApiBaseUrl();
	const res = await fetch(`${apiBase}/transactions/${id}`);

	if (!res.ok) {
		throw error(res.status, 'Transaction not found or error loading transaction detail');
	}

	const data = await res.json();
	return json(data);
};
