<script lang="ts">
	import Modal from './Modal.svelte';
	import {
		isPushSupported,
		getNotificationPermission,
		getExistingSubscription,
		subscribeToPush,
		unsubscribeFromPush,
		triggerTestPush
	} from '#lib/services/push-notifications.ts';

	let {
		open = false,
		onclose
	}: {
		open: boolean;
		onclose?: () => void;
	} = $props();

	let supported = $state(false);
	let permission = $state<NotificationPermission | 'unsupported'>('default');
	let isSubscribed = $state(false);
	let loading = $state(false);
	let feedbackMessage = $state<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

	// Refresh device push status when opening modal
	$effect(() => {
		if (open) {
			checkStatus();
		} else {
			feedbackMessage = null;
		}
	});

	async function checkStatus() {
		supported = isPushSupported();
		permission = getNotificationPermission();
		if (supported) {
			try {
				const sub = await getExistingSubscription();
				isSubscribed = !!sub;
			} catch {
				isSubscribed = false;
			}
		}
	}

	async function handleSubscribe() {
		loading = true;
		feedbackMessage = null;
		const result = await subscribeToPush();
		loading = false;

		if (result.success) {
			feedbackMessage = {
				type: 'success',
				text: 'Successfully subscribed! Tap "Send Test Notification" below to test your phone.'
			};
			await checkStatus();
		} else {
			feedbackMessage = {
				type: 'error',
				text: result.error || 'Failed to enable notifications.'
			};
			await checkStatus();
		}
	}

	async function handleUnsubscribe() {
		loading = true;
		feedbackMessage = null;
		const result = await unsubscribeFromPush();
		loading = false;

		if (result.success) {
			feedbackMessage = {
				type: 'info',
				text: 'Notifications disabled for this device.'
			};
			await checkStatus();
		} else {
			feedbackMessage = {
				type: 'error',
				text: result.error || 'Failed to disable notifications.'
			};
		}
	}

	async function handleTestNotification() {
		loading = true;
		feedbackMessage = null;
		const result = await triggerTestPush();
		loading = false;

		if (result.success && result.data?.sent > 0) {
			feedbackMessage = {
				type: 'success',
				text: 'Test push delivered! Check your notification center or lock screen.'
			};
		} else if (result.success && result.data?.total_subscriptions === 0) {
			feedbackMessage = {
				type: 'error',
				text: 'No device subscription found. Tap "Enable Notifications" first.'
			};
		} else if (result.success && result.data?.failed > 0) {
			feedbackMessage = {
				type: 'error',
				text: `Push delivery failed (${result.data.failed} failed). The push token may need re-enabling.`
			};
		} else {
			feedbackMessage = {
				type: 'error',
				text: result.error || 'Failed to send test push.'
			};
		}
	}
</script>

<Modal
	{open}
	{onclose}
	title="Due Date & Obligation Notifications"
	description="Receive native alerts on your phone before credit cards, loans, and bills are due."
>
	<div class="space-y-4">
		<!-- Device Status Overview -->
		<div class="p-3.5 rounded-xl bg-brand-50 border border-brand-200/80 space-y-2 text-xs">
			<div class="flex items-center justify-between">
				<span class="text-brand-700 font-medium">Browser / Device Support:</span>
				{#if supported}
					<span class="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
						<span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Supported
					</span>
				{:else}
					<span class="inline-flex items-center gap-1 font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
						<span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span> Not Detected
					</span>
				{/if}
			</div>

			<div class="flex items-center justify-between">
				<span class="text-brand-700 font-medium">OS Permission:</span>
				<span
					class="font-mono uppercase font-bold text-[10px] px-1.5 py-0.5 rounded {permission === 'granted'
						? 'bg-emerald-100 text-emerald-800'
						: permission === 'denied'
							? 'bg-rose-100 text-rose-800'
							: 'bg-brand-200 text-brand-800'}"
				>
					{permission}
				</span>
			</div>

			<div class="flex items-center justify-between">
				<span class="text-brand-700 font-medium">Active Subscription:</span>
				{#if isSubscribed}
					<span class="inline-flex items-center gap-1 font-semibold text-emerald-700">
						Active & Registered
					</span>
				{:else}
					<span class="text-brand-500 font-medium">Not Subscribed</span>
				{/if}
			</div>
		</div>

		<!-- Feedback Message Alert -->
		{#if feedbackMessage}
			<div
				class="p-3 rounded-xl text-xs flex items-start gap-2.5 {feedbackMessage.type === 'success'
					? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
					: feedbackMessage.type === 'error'
						? 'bg-rose-50 text-rose-900 border border-rose-200'
						: 'bg-brand-100/70 text-brand-900 border border-brand-200'}"
			>
				<span class="text-sm shrink-0">
					{feedbackMessage.type === 'success' ? '✅' : feedbackMessage.type === 'error' ? '⚠️' : 'ℹ️'}
				</span>
				<span class="leading-relaxed font-medium">{feedbackMessage.text}</span>
			</div>
		{/if}

		<!-- Action Controls -->
		<div class="space-y-2 pt-1">
			{#if !isSubscribed}
				<button
					type="button"
					onclick={handleSubscribe}
					disabled={loading || !supported}
					class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 transition-colors shadow-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
				>
					{#if loading}
						<span class="animate-spin text-sm">⏳</span> Requesting...
					{:else}
						<span>🔔</span> Enable Notifications on this Phone
					{/if}
				</button>
			{:else}
				<button
					type="button"
					onclick={handleTestNotification}
					disabled={loading}
					class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
				>
					{#if loading}
						<span class="animate-spin text-sm">⏳</span> Sending...
					{:else}
						<span>📲</span> Send Test Notification
					{/if}
				</button>

				<button
					type="button"
					onclick={handleUnsubscribe}
					disabled={loading}
					class="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-600 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
				>
					Turn off notifications for this device
				</button>
			{/if}
		</div>

		<!-- Helpful Tip for iOS / Tailscale -->
		<p class="text-[11px] text-brand-500 leading-normal border-t border-brand-100 pt-3">
			💡 <strong>Tip for iPhone users</strong>: Web push works when launched from your Home Screen
			icon over HTTPS (Tailscale). Notifications will appear in your iOS Notification Center and Lock
			Screen just like an App Store app.
		</p>
	</div>
</Modal>
