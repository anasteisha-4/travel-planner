import { apiClient } from '@/shared/api';
import type {
  ConvertedExpenseSummary,
  ExchangeRates,
  Expense,
  ExpenseCreate,
  ExpenseSummary,
  ExpenseUpdate,
} from '../model/types';
import {
  ConvertedExpenseSummarySchema,
  ExchangeRatesSchema,
  ExpenseSchema,
  ExpenseSummarySchema,
} from '../model/types';

export const expenseApi = {
  getExpenses: async (
    tripId: string,
    params?: { category?: string; date_from?: string; date_to?: string }
  ): Promise<Expense[]> => {
    const response = await apiClient.get(`/api/trips/${tripId}/expenses`, { params });
    return response.data.map((item: unknown) => ExpenseSchema.parse(item));
  },

  getSummary: async (tripId: string): Promise<ExpenseSummary> => {
    const response = await apiClient.get(`/api/trips/${tripId}/expenses/summary`);
    return ExpenseSummarySchema.parse(response.data);
  },

  getConvertedSummary: async (
    tripId: string,
    targetCurrency: string
  ): Promise<ConvertedExpenseSummary> => {
    const response = await apiClient.get(`/api/trips/${tripId}/expenses/converted-summary`, {
      params: { target_currency: targetCurrency },
    });
    return ConvertedExpenseSummarySchema.parse(response.data);
  },

  getExchangeRates: async (base: string): Promise<ExchangeRates> => {
    const response = await apiClient.get('/api/exchange-rates', { params: { base } });
    return ExchangeRatesSchema.parse(response.data);
  },

  createExpense: async (tripId: string, data: ExpenseCreate): Promise<Expense> => {
    const response = await apiClient.post(`/api/trips/${tripId}/expenses`, data);
    return ExpenseSchema.parse(response.data);
  },

  updateExpense: async (expenseId: string, data: ExpenseUpdate): Promise<Expense> => {
    const response = await apiClient.put(`/api/expenses/${expenseId}`, data);
    return ExpenseSchema.parse(response.data);
  },

  deleteExpense: async (expenseId: string): Promise<void> => {
    await apiClient.delete(`/api/expenses/${expenseId}`);
  },
};
