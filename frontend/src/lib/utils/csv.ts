/**
 * Utilities for CSV Template generation, CSV/TSV parsing, and batch transaction formatting.
 */

export interface BatchSplit {
	id: string;
	envelope: string;
	amount: string;
}

export interface BatchRow {
	id: string;
	selected: boolean;
	date: string;
	account: string;
	merchant: string;
	total: string;
	note: string;
	splits: BatchSplit[];
	isExpanded?: boolean;
}

export interface ParseResult {
	rows: BatchRow[];
	errors: string[];
}

/**
 * Generates a ready-to-fill CSV template populated with the user's active accounts and envelopes.
 */
export function generateCsvTemplate(
	accountNames: string[],
	envelopeNames: string[]
): string {
	const sampleAccount = accountNames[0] || 'Checking';
	const sampleEnv1 = envelopeNames[0] || 'Groceries';
	const sampleEnv2 = envelopeNames[1] || 'Household';
	const sampleEnv3 = envelopeNames[2] || 'Gas & Fuel';

	const lines = [
		`Tx_ID,Date,Account,Merchant,Total,Envelope,Split_Amount,Note`,
		`1,2026-10-24,"${sampleAccount}","Costco Wholesale",150.00,"${sampleEnv1}",100.00,"Weekend trip groceries"`,
		`1,2026-10-24,"${sampleAccount}","Costco Wholesale",150.00,"${sampleEnv2}",50.00,"Toiletries and supplies"`,
		`2,2026-10-25,"${sampleAccount}","Shell Gas",45.00,"${sampleEnv3}",45.00,"Highway fuel"`,
		`3,2026-10-25,"${sampleAccount}","Mario's Bistro",82.50,"${sampleEnv1}",82.50,"Dinner with team"`
	];

	return lines.join('\r\n');
}

/**
 * Triggers a browser download of the CSV template file.
 */
export function downloadCsvTemplate(
	accountNames: string[],
	envelopeNames: string[],
	filename = 'homeledger_batch_template.csv'
) {
	const content = generateCsvTemplate(accountNames, envelopeNames);
	const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.setAttribute('href', url);
	link.setAttribute('download', filename);
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	URL.revokeObjectURL(url);
}

/**
 * Splits CSV/TSV text into an array of rows and tokens, respecting quotes.
 */
function tokenizeCsv(text: string): string[][] {
	const lines: string[][] = [];
	let currentRow: string[] = [];
	let currentToken = '';
	let inQuotes = false;

	const cleanText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

	for (let i = 0; i < cleanText.length; i++) {
		const char = cleanText[i];
		const nextChar = cleanText[i + 1];

		if (char === '"') {
			if (inQuotes && nextChar === '"') {
				currentToken += '"';
				i++; // Skip escaped quote
			} else {
				inQuotes = !inQuotes;
			}
		} else if (!inQuotes && (char === ',' || char === '\t')) {
			currentRow.push(currentToken.trim());
			currentToken = '';
		} else if (!inQuotes && char === '\n') {
			currentRow.push(currentToken.trim());
			currentToken = '';
			// Only push non-empty rows or comments
			if (currentRow.some((c) => c.length > 0)) {
				lines.push(currentRow);
			}
			currentRow = [];
		} else {
			currentToken += char;
		}
	}

	if (currentToken.length > 0 || currentRow.length > 0) {
		currentRow.push(currentToken.trim());
		if (currentRow.some((c) => c.length > 0)) {
			lines.push(currentRow);
		}
	}

	return lines;
}

/**
 * Converts various date formats (e.g. MM/DD/YYYY, YYYY/MM/DD, M/D/YY, Excel timestamps)
 * into standard ISO YYYY-MM-DD required by HTML5 date inputs.
 */
export function normalizeDateToISO(raw: string): string {
	if (!raw) return '';
	const trimmed = raw.trim();

	// Case 1: Already YYYY-MM-DD
	if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
		return trimmed;
	}

	// Case 2: YYYY/MM/DD or YYYY.MM.DD
	const ymdMatch = trimmed.match(/^(\d{4})[\/\.](\d{1,2})[\/\.](\d{1,2})/);
	if (ymdMatch) {
		const [, y, m, d] = ymdMatch;
		return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
	}

	// Case 3: MM/DD/YYYY or M/D/YYYY (with optional timestamp)
	const mdyMatch = trimmed.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})(?:\s+.*)?$/);
	if (mdyMatch) {
		const [, m, d, y] = mdyMatch;
		const numM = parseInt(m, 10);
		const numD = parseInt(d, 10);
		// If m > 12 and d <= 12, assume DD/MM/YYYY
		if (numM > 12 && numD <= 12) {
			return `${y}-${d.padStart(2, '0')}-${m.padStart(2, '0')}`;
		}
		return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
	}

	// Case 4: MM/DD/YY (2-digit year)
	const shortYearMatch = trimmed.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})(?:\s+.*)?$/);
	if (shortYearMatch) {
		const [, m, d, yy] = shortYearMatch;
		const fullYear = parseInt(yy, 10) < 50 ? `20${yy}` : `19${yy}`;
		return `${fullYear}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
	}

	// Case 5: Standard Date parse (e.g. 'Oct 24, 2026', '24 Oct 2026')
	const parsed = new Date(trimmed);
	if (!isNaN(parsed.getTime())) {
		const y = parsed.getFullYear();
		const m = String(parsed.getMonth() + 1).padStart(2, '0');
		const d = String(parsed.getDate()).padStart(2, '0');
		return `${y}-${m}-${d}`;
	}

	return trimmed;
}

/**
 * Fuzzy or case-insensitive matching for envelope names.
 */
export function findMatchingEnvelope(name: string, envelopes: string[]): string {
	if (!name || envelopes.length === 0) return '';
	const clean = name.trim().toLowerCase();

	// Exact match (case insensitive)
	const exact = envelopes.find((e) => e.toLowerCase() === clean);
	if (exact) return exact;

	// Contains match
	const contains = envelopes.find(
		(e) => e.toLowerCase().includes(clean) || clean.includes(e.toLowerCase())
	);
	if (contains) return contains;

	return name.trim();
}

/**
 * Fuzzy or case-insensitive matching for account names.
 */
export function findMatchingAccount(name: string, accounts: string[]): string {
	if (!name || accounts.length === 0) return '';
	const clean = name.trim().toLowerCase();

	const exact = accounts.find((a) => a.toLowerCase() === clean);
	if (exact) return exact;

	const contains = accounts.find(
		(a) => a.toLowerCase().includes(clean) || clean.includes(a.toLowerCase())
	);
	if (contains) return contains;

	return accounts[0] || name.trim();
}

/**
 * Parses a CSV string and constructs an array of BatchRows with splits grouped by Tx_ID.
 */
export function parseBatchCsv(
	csvText: string,
	validAccounts: string[],
	validEnvelopes: string[]
): ParseResult {
	const rawRows = tokenizeCsv(csvText);
	const errors: string[] = [];
	const rows: BatchRow[] = [];

	if (rawRows.length === 0) {
		return { rows: [], errors: ['Uploaded file is empty.'] };
	}

	// Filter out comment lines
	const nonCommentRows = rawRows.filter(
		(r) => r.length > 0 && !r[0].startsWith('#') && !r[0].startsWith('//')
	);

	if (nonCommentRows.length === 0) {
		return { rows: [], errors: ['No data rows found in CSV.'] };
	}

	// Identify Header row
	const headerRow = nonCommentRows[0].map((h) =>
		h.toLowerCase().replace(/[^a-z0-9]/g, '')
	);

	const colIndex = {
		tx_id: headerRow.findIndex((h) => h === 'txid' || h === 'id' || h === 'txgroup' || h.includes('txid')),
		date: headerRow.findIndex((h) => h === 'date' || h === 'loggeddate' || h === 'txdate' || h.includes('date')),
		account: headerRow.findIndex(
			(h) => h === 'account' || h === 'paymentmethod' || h === 'accountname' || h.includes('account') || h.includes('payment')
		),
		merchant: headerRow.findIndex(
			(h) => h === 'merchant' || h === 'payee' || h === 'description' || h.includes('merchant') || h.includes('payee') || h.includes('desc')
		),
		total: headerRow.findIndex((h) => h === 'total' || h === 'totalamount' || h.includes('total')),
		envelope: headerRow.findIndex(
			(h) => h === 'envelope' || h === 'category' || h.includes('envelope') || h.includes('category')
		),
		split_amount: headerRow.findIndex((h) => h === 'splitamount' || h === 'split' || h.includes('split')),
		note: headerRow.findIndex((h) => h === 'note' || h === 'memo' || h === 'notes' || h.includes('note') || h.includes('memo'))
	};

	// Fallback for total and split_amount if column is simply 'amount'
	if (colIndex.total === -1) {
		colIndex.total = headerRow.findIndex((h) => h === 'amount' || h.includes('amount'));
	}
	if (colIndex.split_amount === -1) {
		colIndex.split_amount = headerRow.findIndex((h) => h === 'amount' || h.includes('amount'));
	}

	// If missing crucial headers
	if (colIndex.merchant === -1 && colIndex.split_amount === -1 && colIndex.total === -1) {
		return {
			rows: [],
			errors: ['Could not detect column headers. Make sure headers like Date, Account, Merchant, Envelope, and Amount exist.']
		};
	}

	const dataRows = nonCommentRows.slice(1);
	const groupedMap = new Map<string, BatchRow>();
	let autoIdCounter = 1;
	let lastGroupKey = '';

	for (let i = 0; i < dataRows.length; i++) {
		const row = dataRows[i];
		const getVal = (idx: number) => (idx >= 0 && idx < row.length ? row[idx].trim() : '');

		const rawTxId = colIndex.tx_id >= 0 ? getVal(colIndex.tx_id) : '';
		const rawDate = colIndex.date >= 0 ? getVal(colIndex.date) : '';
		const rawAccount = colIndex.account >= 0 ? getVal(colIndex.account) : '';
		const rawMerchant = colIndex.merchant >= 0 ? getVal(colIndex.merchant) : '';
		const rawTotal = colIndex.total >= 0 ? getVal(colIndex.total) : '';
		const rawEnvelope = colIndex.envelope >= 0 ? getVal(colIndex.envelope) : '';
		const rawSplitAmount = colIndex.split_amount >= 0 ? getVal(colIndex.split_amount) : '';
		const rawNote = colIndex.note >= 0 ? getVal(colIndex.note) : '';

		// If entire row is blank, skip
		if (!rawDate && !rawMerchant && !rawSplitAmount && !rawEnvelope) {
			continue;
		}

		// Grouping key: either explicit rawTxId, or create unique group
		let groupKey = rawTxId ? `tx_group_${rawTxId}` : '';
		if (!groupKey) {
			// If date and merchant are blank, inherit from previous row if available
			if (!rawMerchant && !rawDate && rows.length > 0 && lastGroupKey) {
				groupKey = lastGroupKey;
			} else {
				groupKey = `tx_auto_${autoIdCounter++}_${Date.now()}`;
			}
		}
		lastGroupKey = groupKey;

		const normalizedDate = normalizeDateToISO(rawDate);
		const matchedAccount = findMatchingAccount(rawAccount, validAccounts);
		const matchedEnvelope = findMatchingEnvelope(rawEnvelope, validEnvelopes);
		const cleanAmount = rawSplitAmount ? rawSplitAmount.replace(/[^0-9.-]/g, '') : (rawTotal ? rawTotal.replace(/[^0-9.-]/g, '') : '');

		if (groupedMap.has(groupKey)) {
			// Add split to existing row
			const existing = groupedMap.get(groupKey)!;
			existing.splits.push({
				id: crypto.randomUUID(),
				envelope: matchedEnvelope,
				amount: cleanAmount
			});
			if (!existing.merchant && rawMerchant) existing.merchant = rawMerchant;
			if (!existing.date && normalizedDate) existing.date = normalizedDate;
			if (!existing.note && rawNote) existing.note = rawNote;
			if (!existing.account && matchedAccount) existing.account = matchedAccount;
			if (!existing.total && rawTotal) existing.total = rawTotal.replace(/[^0-9.-]/g, '');
		} else {
			const newRow: BatchRow = {
				id: crypto.randomUUID(),
				selected: true,
				date: normalizedDate || new Date().toISOString().slice(0, 10),
				account: matchedAccount || validAccounts[0] || '',
				merchant: rawMerchant,
				total: rawTotal ? rawTotal.replace(/[^0-9.-]/g, '') : cleanAmount,
				note: rawNote,
				splits: [
					{
						id: crypto.randomUUID(),
						envelope: matchedEnvelope || validEnvelopes[0] || '',
						amount: cleanAmount
					}
				],
				isExpanded: false
			};
			groupedMap.set(groupKey, newRow);
			rows.push(newRow);
		}
	}

	// Validate and adjust total if total was empty on split rows
	for (const r of rows) {
		const splitsSum = r.splits.reduce((acc, s) => acc + (parseFloat(s.amount) || 0), 0);
		if (!r.total || parseFloat(r.total) === 0) {
			r.total = splitsSum > 0 ? splitsSum.toFixed(2) : '';
		}
		// If single split, ensure split amount matches total if either was set
		if (r.splits.length === 1) {
			if (!r.splits[0].amount && r.total) {
				r.splits[0].amount = r.total;
			} else if (!r.total && r.splits[0].amount) {
				r.total = r.splits[0].amount;
			}
		}
		if (r.splits.length > 1) {
			r.isExpanded = true;
		}
	}

	return { rows, errors };
}

/**
 * Checks a BatchRow for completeness and balance.
 */
export function getRowValidation(
	row: BatchRow,
	validAccounts: string[],
	validEnvelopes: string[]
): { isValid: boolean; issues: string[]; remainingBalance: number } {
	const issues: string[] = [];

	if (!row.merchant.trim()) {
		issues.push('Merchant name is required.');
	}

	if (!row.date || isNaN(Date.parse(row.date))) {
		issues.push('Valid date (YYYY-MM-DD) is required.');
	}

	const trimmedAccount = row.account.trim().toLowerCase();
	if (
		!trimmedAccount ||
		(validAccounts.length > 0 &&
			!validAccounts.some((a) => a.trim().toLowerCase() === trimmedAccount))
	) {
		issues.push(`Unknown account "${row.account}".`);
	}

	const totalNum = parseFloat(row.total || '0') || 0;
	if (totalNum <= 0) {
		issues.push('Total amount must be greater than zero.');
	}

	let splitsSum = 0;
	for (let i = 0; i < row.splits.length; i++) {
		const s = row.splits[i];
		const amt = parseFloat(s.amount || '0') || 0;
		if (amt <= 0) {
			issues.push(`Split #${i + 1} must have a positive amount.`);
		}
		const trimmedEnv = s.envelope.trim().toLowerCase();
		if (
			!trimmedEnv ||
			(validEnvelopes.length > 0 &&
				!validEnvelopes.some((e) => e.trim().toLowerCase() === trimmedEnv))
		) {
			issues.push(`Split #${i + 1} specifies unknown envelope "${s.envelope}".`);
		}
		splitsSum += amt;
	}

	const remainingBalance = Math.round((totalNum - splitsSum) * 100) / 100;
	if (Math.abs(remainingBalance) >= 0.01) {
		issues.push(
			`Splits sum ($${splitsSum.toFixed(2)}) does not match Total ($${totalNum.toFixed(2)}).`
		);
	}

	return {
		isValid: issues.length === 0,
		issues,
		remainingBalance
	};
}
