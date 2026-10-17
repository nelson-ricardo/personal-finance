<script lang="ts">
	import './layout.css';
	import favicon from '#lib/assets/favicon.svg';
	import type { LayoutProps } from './$types';
	import '@fontsource-variable/jetbrains-mono';
	import '@fontsource-variable/plus-jakarta-sans'

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<main>
	<nav>
		<a href="/accounts">Accounts</a>
		<a href="/envelopes">Envelopes</a>
		<a href="/transactions">Transactions</a>
	</nav>
	{@render children()}
</main>