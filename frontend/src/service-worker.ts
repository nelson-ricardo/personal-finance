/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

import { assets, immutable } from '$app/manifest';
import { version } from '$app/env';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE = `cache-${version}`;

const ASSETS = [...immutable.map((asset) => asset.path), ...assets.map((asset) => asset.path)];

sw.addEventListener('install', (event) => {
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);
	}

	event.waitUntil(addFilesToCache());
});

sw.addEventListener('activate', (event) => {
	async function deleteOldCaches() {
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
	}

	event.waitUntil(deleteOldCaches());
});

sw.addEventListener('fetch', (event) => {
	if (event.request.method !== 'GET') return;

	async function respond() {
		const url = new URL(event.request.url);
		const cache = await caches.open(CACHE);

		// Assets and immutable files can always be served from cache
		if (ASSETS.includes(url.pathname)) {
			const response = await cache.match(url.pathname);
			if (response) return response;
		}

		// Network-first for dynamic navigation/data, fallback to cache
		try {
			const response = await fetch(event.request);

			if (!(response instanceof Response)) {
				throw new Error('invalid response from fetch');
			}

			if (response.status === 200) {
				cache.put(event.request, response.clone());
			}

			return response;
		} catch (err) {
			const response = await cache.match(event.request);
			if (response) return response;

			throw err;
		}
	}

	event.respondWith(respond());
});

// Push notification received in background
sw.addEventListener('push', (event) => {
	let payload = {
		title: 'Homeledger Reminder',
		body: 'You have an upcoming obligation.',
		url: '/'
	};

	if (event.data) {
		try {
			payload = event.data.json();
		} catch {
			payload.body = event.data.text();
		}
	}

	const options: NotificationOptions = {
		body: payload.body,
		icon: '/pwa-192x192.png',
		badge: '/pwa-192x192.png',
		data: { url: payload.url || '/' },
		tag: 'homeledger-notification',
		renotify: true
	};

	event.waitUntil(sw.registration.showNotification(payload.title || 'Homeledger', options));
});

// User taps on notification banner
sw.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const targetUrl = event.notification.data?.url || '/';

	event.waitUntil(
		sw.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
			for (const client of clients) {
				if (client.url.includes(targetUrl) && 'focus' in client) {
					return client.focus();
				}
			}
			if (sw.clients.openWindow) {
				return sw.clients.openWindow(targetUrl);
			}
		})
	);
});

