/**
 * Formats a monetary amount into standard US currency format ($X,XXX.XX)
 */
export function formatCurrency(val: string | number | null | undefined): string {
	if (val === null || val === undefined || val === '') return '$0.00';
	const num = typeof val === 'string' ? parseFloat(val) : val;
	if (isNaN(num)) return '$0.00';
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		minimumFractionDigits: 2
	}).format(num);
}

/**
 * Returns ordinal day representation (e.g. 1st, 2nd, 3rd, 19th)
 */
export function getOrdinalSuffix(day: number | null | undefined): string {
	if (!day) return '';
	const j = day % 10;
	const k = day % 100;
	if (j === 1 && k !== 11) return `${day}st`;
	if (j === 2 && k !== 12) return `${day}nd`;
	if (j === 3 && k !== 13) return `${day}rd`;
	return `${day}th`;
}
