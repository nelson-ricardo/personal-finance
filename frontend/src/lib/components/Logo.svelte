<script lang="ts">
	import { APP_CONFIG } from '#lib/config.ts';

	interface Props {
		size?: 'sm' | 'md' | 'lg';
		showText?: boolean;
		showTagline?: boolean;
	}

	let { size = 'md', showText = true, showTagline = false }: Props = $props();

	const iconDimensions = $derived.by(() => {
		switch (size) {
			case 'sm':
				return 'w-7 h-7';
			case 'lg':
				return 'w-11 h-11';
			default:
				return 'w-8 h-8 sm:w-9 sm:h-9';
		}
	});

	const titleSize = $derived.by(() => {
		switch (size) {
			case 'sm':
				return 'text-sm sm:text-base';
			case 'lg':
				return 'text-xl sm:text-2xl';
			default:
				return 'text-base sm:text-lg';
		}
	});
</script>

<div class="inline-flex items-center gap-2 sm:gap-3 select-none">
	<!-- Fintech Three-Pillars Emblem -->
	<div class="{iconDimensions} shrink-0 shadow-xs rounded-xl overflow-hidden">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 120 120"
			fill="none"
			class="w-full h-full"
			role="img"
			aria-label="Fintech Three Pillars Emblem"
		>
			<defs>
				<linearGradient id="fintechGlow" x1="0%" y1="0%" x2="100%" y2="100%">
					<stop offset="0%" stop-color="#14463F" />
					<stop offset="100%" stop-color="#0E3530" />
				</linearGradient>
				<linearGradient id="pillarCenter" x1="0%" y1="0%" x2="0%" y2="100%">
					<stop offset="0%" stop-color="#FFFFFF" />
					<stop offset="100%" stop-color="#D5DFDC" />
				</linearGradient>
				<linearGradient id="pillarAccent" x1="0%" y1="0%" x2="0%" y2="100%">
					<stop offset="0%" stop-color="#A4BCB7" />
					<stop offset="100%" stop-color="#5E837D" />
				</linearGradient>
			</defs>

			<!-- Modern Squircle Base in Phthalo Green #0E3530 -->
			<rect x="6" y="6" width="108" height="108" rx="30" fill="url(#fintechGlow)" />
			<rect x="7" y="7" width="106" height="106" rx="29" stroke="#1F534C" stroke-width="2" />

			<!-- Dynamic Baseline Arc (Momentum / Stewardship) -->
			<path
				d="M 28 84 C 44 86 76 86 92 84"
				stroke="#2A645C"
				stroke-width="3"
				stroke-linecap="round"
			/>

			<!-- Three Pillars of Fiscal Stewardship (Fintech Rounded Bars) -->
			<!-- Left Pillar: Emergency Reserves / Foundation -->
			<rect x="33" y="46" width="13" height="34" rx="6.5" fill="url(#pillarAccent)" />

			<!-- Center Pillar: Active Budgeting & Cash Stewardship (Tallest Core) -->
			<rect x="53.5" y="30" width="13" height="50" rx="6.5" fill="url(#pillarCenter)" />

			<!-- Right Pillar: Debt Elimination & Compound Growth -->
			<rect x="74" y="38" width="13" height="42" rx="6.5" fill="url(#pillarAccent)" />

			<!-- Forward Momentum Spark atop Pillar 3 -->
			<circle cx="80.5" cy="27" r="3.5" fill="#C3CDCB" />
		</svg>
	</div>

	{#if showText}
		<div class="flex flex-col min-w-0">
			<div class="flex items-center gap-1.5 flex-wrap">
				<span
					class="font-sans font-extrabold {titleSize} tracking-tight text-brand-900 leading-none truncate"
				>
					[{APP_CONFIG.name}]
				</span>
				<span
					class="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-brand-100 text-brand-700 tracking-wider uppercase shrink-0"
					title="Placeholder name. Replace with your brand name in src/lib/config.ts"
				>
					Name Here
				</span>
			</div>
			{#if showTagline}
				<span class="text-xs text-brand-700 font-medium tracking-tight mt-0.5 truncate">
					{APP_CONFIG.tagline}
				</span>
			{/if}
		</div>
	{/if}
</div>
