import type { Envelope, EnvelopeCategoryWithEnvelopes } from '#lib/schemas/category.ts';

export function isCreditCardPaymentEnvelope(e: Envelope): boolean {
	return (
		e.system_role === 'CREDIT_CARD_PAYMENT' ||
		e.name === 'Credit Card Payment' ||
		e.name.startsWith('Credit Card Payment')
	);
}

export function isInternalSystemEnvelope(e: Envelope): boolean {
	return (
		e.name === 'Unassigned' ||
		e.system_role === 'UNASSIGNED' ||
		e.name === 'Account Adjustment' ||
		e.system_role === 'ACCOUNT_ADJUSTMENT'
	);
}

/**
 * Normalizes categories for display across the application so that:
 * 1. "Credit Card Payment" envelopes (which may be stored in "System" or regular categories in prod)
 *    are hoisted into a dedicated "Credit Card Payments" category.
 * 2. Purely internal system envelopes ("Unassigned", "Account Adjustment") are filtered out of budgeting categories.
 * 3. Empty internal categories (like "System" when it only contains Unassigned/Account Adjustment) are hidden.
 */
export function getUserVisibleCategories(
	categories: EnvelopeCategoryWithEnvelopes[]
): EnvelopeCategoryWithEnvelopes[] {
	const allEnvelopes = categories.flatMap((c) => c.envelopes);
	const ccEnvelopes = allEnvelopes.filter(isCreditCardPaymentEnvelope);

	const result: EnvelopeCategoryWithEnvelopes[] = [];

	// 1. If any credit card payment envelopes exist, create a dedicated prominent group
	if (ccEnvelopes.length > 0) {
		const totalBalance = ccEnvelopes.reduce((sum, e) => sum + (parseFloat(e.balance) || 0), 0);
		result.push({
			id: null,
			name: 'Credit Card Payments',
			order_index: -1,
			is_active: true,
			total_balance: totalBalance.toFixed(2),
			envelopes: ccEnvelopes
		});
	}

	// 2. Add regular categories, filtering out internal system envelopes and hoisted CC envelopes
	for (const cat of categories) {
		const regularEnvelopes = cat.envelopes.filter(
			(e) => !isInternalSystemEnvelope(e) && !isCreditCardPaymentEnvelope(e)
		);

		if (cat.name === 'System') {
			if (regularEnvelopes.length > 0) {
				result.push({
					...cat,
					envelopes: regularEnvelopes
				});
			}
		} else {
			result.push({
				...cat,
				envelopes: regularEnvelopes
			});
		}
	}

	return result;
}
