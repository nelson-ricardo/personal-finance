<script lang="ts">
	import { APP_CONFIG } from '#lib/config.ts';
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>Dashboard Scaffolding — [{APP_CONFIG.name}]</title>
</svelte:head>

<div class="space-y-8">
	<!-- Dashboard Scaffolding Header Banner -->
	<div
		class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-700 text-brand-50 p-6 sm:p-8 shadow-sm"
	>
		<div class="relative z-10 max-w-3xl space-y-3">
			<div
				class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-700/70 border border-brand-400/30 text-xs font-mono text-brand-100"
			>
				<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
				Homepage Blueprint Scaffolding
			</div>
			<h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-sans">
				Welcome to [{APP_CONFIG.name}]
			</h1>
			<p class="text-brand-100 text-base sm:text-lg leading-relaxed max-w-2xl">
				This homepage is currently staged as an executive dashboard wireframe. The backend and
				frontend are actively hooked up on the <a
					href={resolve('/accounts')}
					class="underline font-semibold hover:text-white transition-colors">Accounts route</a
				>.
			</p>
			<div class="pt-2 flex flex-wrap gap-3">
				<a
					href={resolve('/accounts')}
					class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-brand-900 font-semibold text-sm hover:bg-brand-50 transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
				>
					<span>Open Accounts Hub</span>
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M14 5l7 7m0 0l-7 7m7-7H3"
						/>
					</svg>
				</a>
				<span
					class="inline-flex items-center px-3.5 py-2 rounded-xl bg-brand-800/60 text-brand-200 text-xs font-mono border border-brand-700"
				>
					Route Status: /accounts Connected
				</span>
			</div>
		</div>

		<!-- Decorative Background Geometric Motif -->
		<div
			class="absolute -right-12 -bottom-16 w-80 h-80 rounded-full bg-brand-400/10 pointer-events-none blur-2xl"
		></div>
		<div class="absolute right-12 top-6 opacity-10 pointer-events-none hidden sm:block">
			<svg class="w-48 h-48" viewBox="0 0 100 100" fill="currentColor">
				<path d="M10 90 L50 15 L90 90 Z" />
			</svg>
		</div>
	</div>

	<!-- Scaffolding Metrics Grid (Wireframe Blueprint) -->
	<div>
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-xs font-mono uppercase tracking-wider text-brand-700 font-semibold">
				Dashboard Metrics Blueprint (Scaffolding)
			</h2>
			<span class="text-xs font-mono text-brand-600">Pending Homepage Implementation</span>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
			<!-- Metric 1 -->
			<div
				class="bg-white rounded-xl border border-dashed border-brand-300/80 p-5 shadow-2xs space-y-2"
			>
				<div class="flex items-center justify-between text-xs text-brand-600 font-medium">
					<span>Total Net Liquid</span>
					<span class="font-mono text-[10px] bg-brand-100 px-1.5 py-0.5 rounded text-brand-700"
						>STUB</span
					>
				</div>
				<div class="text-2xl font-mono font-bold text-brand-900 tabular-nums">$—,—.--</div>
				<p class="text-xs text-brand-500 font-sans">
					Will calculate aggregate cash vs liability balance from /accounts.
				</p>
			</div>

			<!-- Metric 2 -->
			<div
				class="bg-white rounded-xl border border-dashed border-brand-300/80 p-5 shadow-2xs space-y-2"
			>
				<div class="flex items-center justify-between text-xs text-brand-600 font-medium">
					<span>Monthly Cash Flow</span>
					<span class="font-mono text-[10px] bg-brand-100 px-1.5 py-0.5 rounded text-brand-700"
						>STUB</span
					>
				</div>
				<div class="text-2xl font-mono font-bold text-brand-900 tabular-nums">+$—,—.--</div>
				<p class="text-xs text-brand-500 font-sans">Planned income minus envelope distributions.</p>
			</div>

			<!-- Metric 3 -->
			<div
				class="bg-white rounded-xl border border-dashed border-brand-300/80 p-5 shadow-2xs space-y-2"
			>
				<div class="flex items-center justify-between text-xs text-brand-600 font-medium">
					<span>Envelopes Allocated</span>
					<span class="font-mono text-[10px] bg-brand-100 px-1.5 py-0.5 rounded text-brand-700"
						>WIP</span
					>
				</div>
				<div class="text-2xl font-mono font-bold text-brand-900 tabular-nums">$—,—.--</div>
				<p class="text-xs text-brand-500 font-sans">
					Will pull envelope balances once the Envelopes route is built.
				</p>
			</div>

			<!-- Metric 4 -->
			<div
				class="bg-white rounded-xl border border-dashed border-brand-300/80 p-5 shadow-2xs space-y-2"
			>
				<div class="flex items-center justify-between text-xs text-brand-600 font-medium">
					<span>Next Due Obligation</span>
					<span class="font-mono text-[10px] bg-brand-100 px-1.5 py-0.5 rounded text-brand-700"
						>STUB</span
					>
				</div>
				<div class="text-2xl font-mono font-bold text-brand-900 tabular-nums">Day — of Month</div>
				<p class="text-xs text-brand-500 font-sans">Next upcoming credit card or loan due date.</p>
			</div>
		</div>
	</div>

	<!-- Navigation Scaffolding Cards -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
		<!-- Accounts Card (Active & Functional) -->
		<a
			href={resolve('/accounts')}
			class="group bg-white rounded-2xl border-2 border-brand-500 p-6 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between"
		>
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span
						class="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center font-bold text-lg"
					>
						💳
					</span>
					<span
						class="inline-flex items-center gap-1 text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800"
					>
						<span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
						Active & Connected
					</span>
				</div>
				<h3 class="text-xl font-bold text-brand-900 group-hover:text-brand-600 transition-colors">
					Accounts Hub
				</h3>
				<p class="text-sm text-brand-700 leading-relaxed">
					View and manage cash accounts, credit cards, statement balances, interest saving balances,
					and payment due schedules.
				</p>
			</div>
			<div
				class="mt-6 pt-4 border-t border-brand-100 flex items-center justify-between text-sm font-semibold text-brand-600 group-hover:translate-x-1 transition-transform"
			>
				<span>Manage Accounts</span>
				<span>→</span>
			</div>
		</a>

		<!-- Envelopes Card (WIP) -->
		<div
			class="bg-white/70 rounded-2xl border border-brand-200 p-6 shadow-2xs flex flex-col justify-between opacity-85"
		>
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span
						class="w-10 h-10 rounded-xl bg-brand-100/60 text-brand-700 flex items-center justify-center font-bold text-lg"
					>
						✉️
					</span>
					<span
						class="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-brand-200/60 text-brand-800"
					>
						WIP
					</span>
				</div>
				<h3 class="text-xl font-bold text-brand-900">Envelopes System</h3>
				<p class="text-sm text-brand-600 leading-relaxed">
					Discrete spending buckets for groceries, bills, discretionary funds, and savings sinking
					funds.
				</p>
			</div>
			<div class="mt-6 pt-4 border-t border-brand-100 text-xs font-mono text-brand-500">
				Scaffolding ready for future implementation
			</div>
		</div>

		<!-- Transactions Card (WIP) -->
		<div
			class="bg-white/70 rounded-2xl border border-brand-200 p-6 shadow-2xs flex flex-col justify-between opacity-85"
		>
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span
						class="w-10 h-10 rounded-xl bg-brand-100/60 text-brand-700 flex items-center justify-center font-bold text-lg"
					>
						📊
					</span>
					<span
						class="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-brand-200/60 text-brand-800"
					>
						WIP
					</span>
				</div>
				<h3 class="text-xl font-bold text-brand-900">Transactions Ledger</h3>
				<p class="text-sm text-brand-600 leading-relaxed">
					Detailed chronological transaction ledger, payee categorization, and envelope allocations.
				</p>
			</div>
			<div class="mt-6 pt-4 border-t border-brand-100 text-xs font-mono text-brand-500">
				Scaffolding ready for future implementation
			</div>
		</div>
	</div>
</div>
