import { z } from 'zod';

export const ExpenseCategoryEnum = z.enum([
  'food',
  'transport',
  'housing',
  'entertainment',
  'shopping',
  'other',
]);

export type ExpenseCategory = z.infer<typeof ExpenseCategoryEnum>;

export const CATEGORY_META: Record<ExpenseCategory, { label: string }> = {
  food: { label: 'Еда' },
  transport: { label: 'Транспорт' },
  housing: { label: 'Жильё' },
  entertainment: { label: 'Развлечения' },
  shopping: { label: 'Покупки' },
  other: { label: 'Другое' },
};

export const ExpenseSchema = z.object({
  id: z.string(),
  trip_id: z.string(),
  user_id: z.string(),
  amount: z.union([z.string(), z.number()]).transform(String),
  currency: z.string(),
  category: ExpenseCategoryEnum,
  description: z.string().nullable(),
  expense_date: z.string().nullable(),
  is_one_time: z.boolean().default(false),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

export type Expense = z.infer<typeof ExpenseSchema>;

export const ExpenseCreateSchema = z.object({
  amount: z.string().min(1),
  currency: z.string().min(1),
  category: ExpenseCategoryEnum,
  description: z.string().nullable().optional(),
  expense_date: z.string().nullable().optional(),
  is_one_time: z.boolean().optional(),
});

export type ExpenseCreate = z.infer<typeof ExpenseCreateSchema>;

export const ExpenseUpdateSchema = ExpenseCreateSchema.partial();
export type ExpenseUpdate = z.infer<typeof ExpenseUpdateSchema>;

export const ExpenseSummarySchema = z.object({
  total: z.union([z.string(), z.number()]).transform(String),
  by_category: z.record(z.string(), z.union([z.string(), z.number()]).transform(String)),
});

export type ExpenseSummary = z.infer<typeof ExpenseSummarySchema>;

export const ConvertedExpenseSummarySchema = z.object({
  total: z.union([z.string(), z.number()]).transform(String),
  planning_total: z.union([z.string(), z.number()]).transform(String).default('0'),
  in_trip_total: z.union([z.string(), z.number()]).transform(String).default('0'),
  by_category: z.record(z.string(), z.union([z.string(), z.number()]).transform(String)),
  target_currency: z.string(),
  original_currencies: z.array(z.string()),
  has_conversion_errors: z.boolean(),
});

export type ConvertedExpenseSummary = z.infer<typeof ConvertedExpenseSummarySchema>;

export const ExchangeRatesSchema = z.object({
  base: z.string(),
  rates: z.record(z.string(), z.number()),
});

export type ExchangeRates = z.infer<typeof ExchangeRatesSchema>;
