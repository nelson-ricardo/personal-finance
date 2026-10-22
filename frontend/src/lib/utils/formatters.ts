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

/**
 * Returns a date formatted as YYYY-MM-DD using local time instead of UTC,
 * preventing off-by-one / next-day timezone shifts caused by .toISOString().
 */
export function getLocalDateString(d: Date = new Date()): string {
	const year = d.getFullYear();
	const month = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

/**
 * Formats an ISO date string (YYYY-MM-DD) into a human readable format (e.g. Oct 21, 2026)
 */
export function formatDate(isoStr: string | null | undefined): string {
	if (!isoStr) return '—';
	try {
		const parts = isoStr.split('-');
		if (parts.length === 3) {
			const d = new Date(
				parseInt(parts[0], 10),
				parseInt(parts[1], 10) - 1,
				parseInt(parts[2], 10)
			);
			return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
		}
		return isoStr;
	} catch {
		return isoStr;
	}
}
