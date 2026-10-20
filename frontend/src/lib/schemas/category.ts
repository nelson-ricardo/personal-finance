import { z } from 'zod';

export const EnvelopeSchema = z.object({
	id: z.number().optional().nullable(),
	name: z.string(),
	note: z.string().nullable().optional(),
	is_active: z.boolean().default(true),
	system_role: z.string().nullable().optional(),
	category_id: z.number().nullable().optional(),
	category_name: z.string().nullable().optional(),
	balance: z.string().default('0.00')
});
export type Envelope = z.infer<typeof EnvelopeSchema>;

export const EnvelopeCategoryWithEnvelopesSchema = z.object({
	id: z.number().nullable().optional(),
	name: z.string(),
	order_index: z.number().default(0),
	is_active: z.boolean().default(true),
	total_balance: z.string().default('0.00'),
	envelopes: z.array(EnvelopeSchema).default([])
});
export type EnvelopeCategoryWithEnvelopes = z.infer<typeof EnvelopeCategoryWithEnvelopesSchema>;

export const CategoriesWithEnvelopesSchema = z.array(EnvelopeCategoryWithEnvelopesSchema);

export const createCategorySchema = z.object({
	name: z.string().trim().min(1, 'Category name is required'),
	order_index: z.coerce.number().int().default(0)
});
export type CreateCategory = z.infer<typeof createCategorySchema>;

export const updateCategorySchema = z.object({
	original_name: z.string(),
	name: z.string().trim().min(1, 'Category name is required'),
	order_index: z.coerce.number().int().default(0)
});
export type UpdateCategory = z.infer<typeof updateCategorySchema>;
