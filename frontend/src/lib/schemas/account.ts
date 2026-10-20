import { z } from 'zod';

export const AccountTypeSchema = z.enum(['loan', 'credit_card']);
export type AccountType = z.infer<typeof AccountTypeSchema>;

export const AccountSchema = z.object({
	id: z.number(),
	name: z.string(),
	account_type: z.enum(['cash', 'loan', 'credit_card']),
	current_balance: z.string(),
	total_statement_balance: z.string().nullable().optional(),
	interest_saving_balance: z.string().nullable().optional(),
	is_active: z.boolean(),
	due_date: z.number().int().min(1).max(31).nullable().optional(),
	monthly_payment: z.string().nullable().optional(),
	envelope_id: z.number().nullable().optional()
});

export const createAccountSchema = z.object({
	name: z.string().trim().min(1, 'Account name is required'),
	account_type: AccountTypeSchema,
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
