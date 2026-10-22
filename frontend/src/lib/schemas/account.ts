import { z } from 'zod';

export const AccountTypeSchema = z.enum(['loan', 'credit_card', 'investment']);
export type AccountType = z.infer<typeof AccountTypeSchema>;

export const AccountSchema = z.object({
	id: z.number(),
	name: z.string(),
	account_type: z.enum(['cash', 'loan', 'credit_card', 'investment']),
	current_balance: z.string(),
	total_statement_balance: z.string().nullable().optional(),
	interest_saving_balance: z.string().nullable().optional(),
	is_active: z.boolean(),
	due_date: z.number().int().min(1).max(31).nullable().optional(),
	monthly_payment: z.string().nullable().optional(),
	envelope_id: z.number().nullable().optional(),
	envelope_name: z.string().nullable().optional(),
	envelope_balance: z
		.union([z.string(), z.number()])
		.transform((val) => String(val))
		.nullable()
		.optional()
});

export const createAccountSchema = z.object({
	name: z.string().trim().min(1, 'Account name is required'),
	account_type: AccountTypeSchema,
	category_name: z.string().trim().optional(),
	current_balance: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid balance')
		.optional(),
	monthly_payment: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount')
		.optional(),
	due_date: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z.coerce
			.number()
			.int()
			.min(1, 'Due date must be between 1 and 31')
			.max(31, 'Due date must be between 1 and 31')
			.optional()
	)
});

export const updateAccountSchema = z.object({
	id: z.coerce.number(),
	name: z.string().trim().min(1, 'Account name is required'),
	account_type: AccountTypeSchema.optional(),
	is_active: z.coerce.boolean().optional(),
	total_statement_balance: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z
			.string()
			.regex(/^\d+(\.\d{1,2})?$/, 'Invalid balance')
			.optional()
	),
	interest_saving_balance: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z
			.string()
			.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount')
			.optional()
	),
	monthly_payment: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z
			.string()
			.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount')
			.optional()
	),
	due_date: z.preprocess(
		(val) => (val === '' || val === null || val === undefined ? undefined : val),
		z.coerce
			.number()
			.int()
			.min(1, 'Due date must be between 1 and 31')
			.max(31, 'Due date must be between 1 and 31')
			.optional()
	)
});

export const AccountsListSchema = z.array(AccountSchema);

export type Account = z.infer<typeof AccountSchema>;
export type AccountsList = z.infer<typeof AccountsListSchema>;

// Account Operations Schemas (Debt Payment, Balance Adjustment, Interest Charge, Interest Earned)

export const paymentSchema = z.object({
	account: z.string().trim().min(1, 'Target account is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 50.00)')
		.refine((val) => parseFloat(val) > 0, 'Payment amount must be greater than 0'),
	envelope_name: z.string().optional().nullable()
});
export type PaymentForm = z.infer<typeof paymentSchema>;

export const accountAdjustmentSchema = z.object({
	account_name: z.string().trim().min(1, 'Account is required'),
	target_balance: z
		.string()
		.regex(/^-?\d+(\.\d{1,2})?$/, 'Invalid target balance (e.g. 1250.00 or -50.00)'),
	note: z.string().optional().nullable(),
	envelope_name: z.string().optional().nullable(),
	logged_date: z.string().optional().nullable()
});
export type AccountAdjustmentForm = z.infer<typeof accountAdjustmentSchema>;

export const interestChargeSchema = z.object({
	account_name: z.string().trim().min(1, 'Debt account is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 15.25)')
		.refine((val) => parseFloat(val) > 0, 'Interest charge must be greater than 0'),
	note: z.string().optional().nullable(),
	logged_date: z.string().min(1, 'Date is required')
});
export type InterestChargeForm = z.infer<typeof interestChargeSchema>;

export const interestEarnedSchema = z.object({
	account_name: z.string().trim().min(1, 'Cash account is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 12.50)')
		.refine((val) => parseFloat(val) > 0, 'Interest earned must be greater than 0'),
	note: z.string().optional().nullable(),
	logged_date: z.string().min(1, 'Date is required')
});
export type InterestEarnedForm = z.infer<typeof interestEarnedSchema>;
