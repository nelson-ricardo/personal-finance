import { z } from 'zod';

export const TransactionTypeSchema = z.enum([
	'INCOME',
	'EXPENSE',
	'TRANSFER',
	'FINANCED',
	'REVERSAL',
	'INTEREST_CHARGE',
	'INTEREST_EARNED'
]);
export type TransactionType = z.infer<typeof TransactionTypeSchema>;

export const EnvelopeSplitSchema = z.object({
	id: z.number().optional(),
	envelope_id: z.number().optional(),
	envelope_name: z.string().min(1, 'Envelope is required'),
	amount: z
		.string()
		.regex(/^-?\d+(\.\d{1,2})?$/, 'Invalid amount')
		.refine((val) => Math.abs(parseFloat(val)) > 0, 'Split amount cannot be zero')
});
export type EnvelopeSplit = z.infer<typeof EnvelopeSplitSchema>;

export const TransactionItemSchema = z.object({
	id: z.number(),
	merchant: z.string(),
	logged_date: z.string(),
	posted_date: z.string().nullable().optional(),
	note: z.string().nullable().optional(),
	is_reconciled: z.boolean().default(false),
	payment_method_id: z.number(),
	payment_method_name: z.string(),
	destination_account_id: z.number().nullable().optional(),
	destination_account_name: z.string().nullable().optional(),
	transaction_type: TransactionTypeSchema,
	total: z.union([z.string(), z.number()]),
	splits: z.array(EnvelopeSplitSchema).optional()
});
export type TransactionItem = z.infer<typeof TransactionItemSchema>;

export const TransactionDetailSchema = TransactionItemSchema.extend({
	splits: z.array(EnvelopeSplitSchema)
});
export type TransactionDetail = z.infer<typeof TransactionDetailSchema>;

// Quick-Add row schema (single split expense)
export const quickAddSchema = z.object({
	logged_date: z.string().min(1, 'Date is required'),
	merchant: z.string().trim().min(1, 'Merchant / Payee is required'),
	payment_method_name: z.string().min(1, 'Account is required'),
	envelope_name: z.string().min(1, 'Envelope is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 24.50)')
		.refine((val) => parseFloat(val) > 0, 'Amount must be greater than 0'),
	note: z.string().optional().nullable()
});
export type QuickAddForm = z.infer<typeof quickAddSchema>;

// Unified Expense creation schema (supports 1 or more splits)
export const createExpenseSchema = z.object({
	logged_date: z.string().min(1, 'Date is required'),
	posted_date: z.string().optional().nullable(),
	merchant: z.string().trim().min(1, 'Merchant is required'),
	payment_method_name: z.string().min(1, 'Account is required'),
	note: z.string().optional().nullable(),
	is_reconciled: z.boolean().default(false),
	total_amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid total amount')
		.refine((val) => parseFloat(val) > 0, 'Total must be greater than 0'),
	splits_json: z.string().min(1, 'At least one split is required')
});
export type CreateExpenseForm = z.infer<typeof createExpenseSchema>;

// Financed transaction creation schema
export const createFinancedSchema = z.object({
	logged_date: z.string().min(1, 'Date is required'),
	posted_date: z.string().optional().nullable(),
	merchant: z.string().trim().min(1, 'Merchant is required'),
	payment_method_name: z.string().min(1, 'Credit Card account is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid principal amount')
		.refine((val) => parseFloat(val) > 0, 'Amount must be greater than 0'),
	term: z.coerce
		.number()
		.int()
		.min(1, 'Term must be at least 1 month')
		.max(120, 'Term cannot exceed 120 months'),
	envelope_name: z.string().optional().nullable(),
	note: z.string().optional().nullable(),
	is_reconciled: z.boolean().default(false)
});
export type CreateFinancedForm = z.infer<typeof createFinancedSchema>;

// Update regular transaction schema
export const updateTransactionSchema = z.object({
	id: z.coerce.number(),
	logged_date: z.string().min(1, 'Date is required'),
	posted_date: z.string().optional().nullable(),
	merchant: z.string().trim().min(1, 'Merchant is required'),
	payment_method_name: z.string().optional().nullable(),
	note: z.string().optional().nullable(),
	is_reconciled: z.coerce.boolean().default(false),
	was_reconciled: z.coerce.boolean().default(false),
	splits_json: z.string().optional().nullable()
});
export type UpdateTransactionForm = z.infer<typeof updateTransactionSchema>;

// Update financed transaction schema
export const updateFinancedSchema = z.object({
	id: z.coerce.number(),
	merchant: z.string().trim().min(1, 'Merchant is required'),
	logged_date: z.string().min(1, 'Date is required'),
	posted_date: z.string().optional().nullable(),
	payment_method_name: z.string().optional().nullable(),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount')
		.optional()
		.nullable(),
	term: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z.coerce.number().int().min(1).max(120).optional()
	),
	envelope_name: z.string().optional().nullable(),
	note: z.string().optional().nullable(),
	is_reconciled: z.coerce.boolean().default(false),
	was_reconciled: z.coerce.boolean().default(false)
});
export type UpdateFinancedForm = z.infer<typeof updateFinancedSchema>;

// Bulk reconcile schema
export const bulkReconcileSchema = z.object({
	transaction_ids: z.string().min(1, 'At least one transaction must be selected'),
	is_reconciled: z.coerce.boolean()
});
export type BulkReconcileForm = z.infer<typeof bulkReconcileSchema>;

// Delete / Reverse transaction schema
export const deleteTransactionSchema = z.object({
	id: z.coerce.number()
});
export type DeleteTransactionForm = z.infer<typeof deleteTransactionSchema>;
