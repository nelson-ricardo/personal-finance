<script lang="ts">
	let {
		onadd
	}: {
		onadd: () => void;
	} = $props();
</script>

<div
	class="bg-white rounded-2xl border border-dashed border-brand-300 p-8 sm:p-12 text-center space-y-4"
>
	<div
		class="w-12 h-12 sm:w-14 sm:h-14 mx-auto rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center text-xl sm:text-2xl"
	>
		💳
	</div>
	<div class="space-y-1 max-w-sm mx-auto">
		<h3 class="text-base sm:text-lg font-bold text-brand-900">No accounts hooked up yet</h3>
		<p class="text-xs sm:text-sm text-brand-600">
			Add your checking, savings, credit cards, or loan accounts to start practicing active fiscal
			stewardship.
		</p>
	</div>
	<button
		type="button"
		onclick={onadd}
		class="w-full sm:w-auto px-4 py-2 rounded-xl bg-brand-500 text-brand-50 text-sm font-semibold hover:bg-brand-600 transition-colors shadow-xs cursor-pointer"
	>
		Add First Account
	</button>
</div>
