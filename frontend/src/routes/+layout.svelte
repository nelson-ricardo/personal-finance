<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import type { LayoutProps } from './$types';
	import '@fontsource-variable/jetbrains-mono';
	import '@fontsource-variable/plus-jakarta-sans';
	import Logo from '#lib/components/Logo.svelte';
	import { APP_CONFIG } from '#lib/config.ts';
	import { page } from '$app/state';
	import { browser } from '$app/env';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';

	interface BeforeInstallPromptEvent extends Event {
		prompt: () => Promise<void>;
		userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
	}

	let { children }: LayoutProps = $props();

	let isOnline = $state(true);
	let installPromptEvent = $state<BeforeInstallPromptEvent | null>(null);

	onMount(() => {
		if (browser) {
			isOnline = navigator.onLine;

			// Register service worker for PWA support
			if ('serviceWorker' in navigator) {
				navigator.serviceWorker
					.register('/service-worker.js')
					.catch((err) => console.info('Service Worker registration skipped or failed:', err));
			}

			// Capture PWA install prompt
			window.addEventListener('beforeinstallprompt', (e) => {
				e.preventDefault();
				installPromptEvent = e as BeforeInstallPromptEvent;
			});

			window.addEventListener('appinstalled', () => {
				installPromptEvent = null;
			});
		}
	});

	async function triggerInstall() {
		if (!installPromptEvent) return;
		await installPromptEvent.prompt();
		const choice = await installPromptEvent.userChoice;
		if (choice.outcome === 'accepted') {
			installPromptEvent = null;
		}
	}

	const navLinks = [
		{ href: resolve('/'), label: 'Home', isWip: false, icon: 'home' },
		{ href: resolve('/accounts'), label: 'Accounts', isWip: false, icon: 'wallet' },
		{ href: resolve('/envelopes'), label: 'Envelopes', isWip: false, icon: 'envelope' },
		{ href: resolve('/transactions'), label: 'Transactions', isWip: false, icon: 'receipt' }
	] as const;
</script>

<svelte:window ononline={() => (isOnline = true)} onoffline={() => (isOnline = false)} />

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={favicon} />
	<title>{APP_CONFIG.name} — Personal Budgeting</title>
</svelte:head>

<div
	class="min-h-screen flex flex-col bg-brand-50 text-brand-900 font-sans antialiased selection:bg-brand-200 selection:text-brand-900"
>
	<!-- Top App Header (Apple macOS-inspired frosted bar) -->
	<header
		class="sticky top-0 z-40 bg-white/85 backdrop-blur-xl border-b border-brand-200/60 shadow-2xs transition-all"
	>
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between h-14 sm:h-16">
				<!-- Brand Logo -->
				<a
					href={resolve('/')}
					class="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-xl p-1 transition-opacity hover:opacity-90 flex-shrink-0"
				>
					<Logo size="md" showText={true} />
				</a>

				<!-- Desktop Navigation Links (Pill-style HIG segment) -->
				<nav
					class="hidden md:flex items-center gap-1.5 p-1 bg-brand-100/60 rounded-xl border border-brand-200/50"
				>
					{#each navLinks as link (link.href)}
						{@const isActive =
							page.url.pathname === link.href ||
							(link.href !== '/' && page.url.pathname.startsWith(link.href))}
						<a
							href={link.href}
							class="relative px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-tight transition-all duration-150 inline-flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 {isActive
								? 'bg-brand-500 text-white shadow-xs'
								: 'text-brand-700 hover:text-brand-950 hover:bg-white/70'}"
						>
							<span>{link.label}</span>
							{#if link.isWip}
								<span
									class="text-[9px] uppercase font-mono font-bold tracking-wider px-1 py-0.2 rounded {isActive
										? 'bg-brand-700/80 text-brand-100'
										: 'bg-brand-200 text-brand-800'}"
								>
									WIP
								</span>
							{/if}
						</a>
					{/each}
				</nav>

				<!-- Header Utility Actions -->
				<div class="flex items-center gap-2">
					<!-- Checkpoint Dev Pill (Accessible across all views & PWA) -->
					<a
						href={resolve('/dev/checkpoint')}
						class="inline-flex items-center gap-1.5 px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full text-xs font-semibold bg-brand-100/70 hover:bg-brand-200/80 text-brand-800 border border-brand-200/70 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 shadow-2xs"
						title="Manage Database Checkpoints"
					>
						<span class="text-xs">💾</span>
						<span class="hidden sm:inline">Checkpoints</span>
						<span
							class="text-[9px] font-mono px-1 py-0.2 rounded bg-brand-300/40 text-brand-800 font-bold uppercase tracking-wider"
							>DEV</span
						>
					</a>

					<!-- Install PWA Button (when prompted) -->
					{#if installPromptEvent}
						<button
							onclick={triggerInstall}
							class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full bg-brand-500 text-white hover:bg-brand-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 shadow-2xs cursor-pointer"
						>
							<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
								/>
							</svg>
							<span class="hidden sm:inline">Install App</span>
							<span class="sm:hidden">Install</span>
						</button>
					{/if}
				</div>
			</div>
		</div>

		<!-- Offline Status Banner -->
		{#if !isOnline}
			<div
				class="bg-[#6b1d2f] text-white text-xs font-mono font-medium py-1 px-4 text-center tracking-wide"
			>
				[Offline Mode] Cached assets active.
			</div>
		{/if}
	</header>

	<!-- Main Page Content with padding bottom for mobile bottom nav -->
	<main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 sm:py-8 pb-28 md:pb-8">
		{@render children()}
	</main>

	<!-- Mobile Bottom Navigation Bar (Apple iOS-style Frosted Glass Tab Bar) -->
	<nav
		class="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/85 backdrop-blur-xl border-t border-brand-200/70 px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] flex items-center justify-around shadow-[0_-4px_16px_rgba(0,0,0,0.04)]"
		aria-label="Mobile Navigation"
	>
		{#each navLinks as link (link.href)}
			{@const isActive =
				page.url.pathname === link.href ||
				(link.href !== '/' && page.url.pathname.startsWith(link.href))}
			<a
				href={link.href}
				class="flex flex-col items-center justify-center flex-1 min-h-[44px] py-1 rounded-xl text-center transition-all min-w-0 {isActive
					? 'text-brand-600 font-bold'
					: 'text-brand-400 hover:text-brand-700 font-medium'}"
			>
				<!-- Icon -->
				<div class="relative flex items-center justify-center">
					{#if link.icon === 'home'}
						<svg
							class="w-5 h-5 {isActive ? 'stroke-[2.5]' : 'stroke-2'}"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
							/>
						</svg>
					{:else if link.icon === 'wallet'}
						<svg
							class="w-5 h-5 {isActive ? 'stroke-[2.5]' : 'stroke-2'}"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
							/>
						</svg>
					{:else if link.icon === 'envelope'}
						<svg
							class="w-5 h-5 {isActive ? 'stroke-[2.5]' : 'stroke-2'}"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
							/>
						</svg>
					{:else}
						<svg
							class="w-5 h-5 {isActive ? 'stroke-[2.5]' : 'stroke-2'}"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
					{/if}

					{#if link.isWip}
						<span class="absolute -top-1 -right-2 w-1.5 h-1.5 rounded-full bg-amber-500"></span>
					{/if}
				</div>

				<span class="text-[10px] tracking-tight mt-1 truncate max-w-full">
					{link.label}
				</span>
			</a>
		{/each}
	</nav>
</div>
