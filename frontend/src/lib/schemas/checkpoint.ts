import { z } from 'zod';

export const CheckpointStatsSchema = z.object({
	accounts_count: z.number().default(0),
	categories_count: z.number().default(0),
	envelopes_count: z.number().default(0),
	transactions_count: z.number().default(0),
	total_cash: z
		.union([z.string(), z.number()])
		.transform((val) => String(val))
		.default('0.00'),
	total_debt: z
		.union([z.string(), z.number()])
		.transform((val) => String(val))
		.default('0.00')
});
export type CheckpointStats = z.infer<typeof CheckpointStatsSchema>;

export const CheckpointSummarySchema = z.object({
	id: z.string(),
	name: z.string(),
	filename: z.string(),
	created_at: z.string(),
	size_bytes: z.number().default(0),
	stats: CheckpointStatsSchema
});
export type CheckpointSummary = z.infer<typeof CheckpointSummarySchema>;

export const CheckpointsListSchema = z.array(CheckpointSummarySchema);

export const createCheckpointSchema = z.object({
	name: z.string().trim().max(100, 'Name must be 100 characters or fewer').optional().default('')
});
export type CreateCheckpoint = z.infer<typeof createCheckpointSchema>;
