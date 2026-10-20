<script lang="ts">
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>Transactions (WIP)</title>
</svelte:head>

<div class="max-w-2xl mx-auto py-12 text-center space-y-6">
	<div
		class="w-16 h-16 mx-auto rounded-2xl bg-brand-100 text-brand-700 flex items-center justify-center text-3xl shadow-xs"
	>
		📊
	</div>

	<div class="space-y-2">
		<div
			class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-200/70 text-brand-800 text-xs font-mono font-semibold"
		>
			<span class="w-2 h-2 rounded-full bg-amber-500"></span>
			Work In Progress
		</div>
		<h1 class="text-3xl font-bold tracking-tight text-brand-900 font-sans">Transactions</h1>
		<p class="text-brand-700 text-base max-w-md mx-auto leading-relaxed">
			This route is currently a placeholder (WIP) and has not been implemented yet.
		</p>
	</div>

	<div class="pt-4 flex justify-center gap-3">
		<a
			href={resolve('/accounts')}
			class="px-4 py-2 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 transition-colors shadow-xs"
		>
			Go to Accounts Hub
		</a>
		<a
			href={resolve('/')}
			class="px-4 py-2 rounded-xl bg-white text-brand-800 border border-brand-200 text-sm font-semibold hover:bg-brand-50 transition-colors"
		>
			Back to Home
		</a>
	</div>
</div>
