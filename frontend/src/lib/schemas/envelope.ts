import { z } from 'zod';

export const createEnvelopeSchema = z.object({
	name: z.string().trim().min(1, 'Envelope name is required'),
	category_name: z.string().optional().nullable(),
	note: z.string().optional().nullable()
});
export type CreateEnvelope = z.infer<typeof createEnvelopeSchema>;

export const updateEnvelopeSchema = z.object({
	original_name: z.string(),
	name: z.string().trim().min(1, 'Envelope name is required'),
	category_name: z.string().optional().nullable(),
	note: z.string().optional().nullable()
});
export type UpdateEnvelope = z.infer<typeof updateEnvelopeSchema>;

export const transferEnvelopeSchema = z.object({
	source_envelope: z.string().trim().min(1, 'Source envelope is required'),
	destination_envelope: z.string().trim().min(1, 'Destination envelope is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 25.00)')
		.refine((val) => parseFloat(val) > 0, 'Amount must be greater than 0'),
	note: z.string().optional().nullable()
});
export type TransferEnvelope = z.infer<typeof transferEnvelopeSchema>;

export const assignEnvelopeSchema = z.object({
	envelope_name: z.string().trim().min(1, 'Target envelope is required'),
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 50.00)')
		.refine((val) => parseFloat(val) > 0, 'Amount must be greater than 0'),
	note: z.string().optional().nullable()
});
export type AssignEnvelope = z.infer<typeof assignEnvelopeSchema>;

export const addIncomeSchema = z.object({
	amount: z
		.string()
		.regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount (e.g. 1500.00)')
		.refine((val) => parseFloat(val) > 0, 'Amount must be greater than 0'),
	source: z.string().trim().min(1, 'Income source is required (e.g. Paycheck)'),
	note: z.string().optional().nullable()
});
export type AddIncome = z.infer<typeof addIncomeSchema>;
