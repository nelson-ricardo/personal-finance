/**
 * Client-side utility service for Web Push Notifications.
 */

function urlBase64ToUint8Array(base64String: string): Uint8Array {
	const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
	const rawData = window.atob(base64);
	const outputArray = new Uint8Array(rawData.length);

	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i);
	}
	return outputArray;
}

export function isPushSupported(): boolean {
	return (
		typeof window !== 'undefined' &&
		'serviceWorker' in navigator &&
		'PushManager' in window &&
		'Notification' in window
	);
}

export function getNotificationPermission(): NotificationPermission | 'unsupported' {
	if (!isPushSupported()) return 'unsupported';
	return Notification.permission;
}

export async function getExistingSubscription(): Promise<PushSubscription | null> {
	if (!isPushSupported()) return null;
	const registration = await navigator.serviceWorker.ready;
	return await registration.pushManager.getSubscription();
}

export async function subscribeToPush(): Promise<{ success: boolean; error?: string }> {
	if (!isPushSupported()) {
		return { success: false, error: 'Push notifications are not supported in this browser/PWA.' };
	}

	try {
		// 1. Request user permission
		const permission = await Notification.requestPermission();
		if (permission !== 'granted') {
			return {
				success: false,
				error: permission === 'denied' ? 'Permission was denied by the user.' : 'Permission was dismissed.'
			};
		}

		// 2. Fetch VAPID public key from server
		const keyRes = await fetch('/api/notifications/vapid-public-key');
		if (!keyRes.ok) {
			const text = await keyRes.text();
			throw new Error(`Failed to fetch VAPID key: ${text}`);
		}
		const { public_key } = await keyRes.json();
		const applicationServerKey = urlBase64ToUint8Array(public_key);

		// 3. Register with browser PushManager
		const registration = await navigator.serviceWorker.ready;
		let subscription = await registration.pushManager.getSubscription();
		if (!subscription) {
			subscription = await registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: applicationServerKey as BufferSource
			});
		}

		// 4. Save to backend database
		const subJson = subscription.toJSON();
		const saveRes = await fetch('/api/notifications/subscribe', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				endpoint: subJson.endpoint,
				keys: {
					p256dh: subJson.keys?.p256dh,
					auth: subJson.keys?.auth
				},
				user_agent: navigator.userAgent
			})
		});

		if (!saveRes.ok) {
			const errText = await saveRes.text();
			throw new Error(`Failed to register subscription on server: ${errText}`);
		}

		return { success: true };
	} catch (err: unknown) {
		const message = err instanceof Error ? err.message : String(err);
		return { success: false, error: message };
	}
}

export async function unsubscribeFromPush(): Promise<{ success: boolean; error?: string }> {
	if (!isPushSupported()) return { success: true };

	try {
		const registration = await navigator.serviceWorker.ready;
		const subscription = await registration.pushManager.getSubscription();

		if (subscription) {
			const endpoint = subscription.endpoint;
			await subscription.unsubscribe();

			await fetch(`/api/notifications/unsubscribe?endpoint=${encodeURIComponent(endpoint)}`, {
				method: 'DELETE'
			});
		}

		return { success: true };
	} catch (err: unknown) {
		const message = err instanceof Error ? err.message : String(err);
		return { success: false, error: message };
	}
}

export async function triggerTestPush(): Promise<{ success: boolean; data?: any; error?: string }> {
	try {
		const res = await fetch('/api/notifications/test', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				title: '🔔 Homeledger Test',
				body: 'Push notifications are working! Your phone will alert you for upcoming due dates.',
				url: '/'
			})
		});

		if (!res.ok) {
			const text = await res.text();
			throw new Error(`Test push failed: ${text}`);
		}

		const data = await res.json();
		return { success: true, data };
	} catch (err: unknown) {
		const message = err instanceof Error ? err.message : String(err);
		return { success: false, error: message };
	}
}
