import type { Expense } from '@/entities/expense';
import type { TripDetailOutletContext } from './TripDetailPage';
import { DeleteExpenseSheet, ExpenseForm, ExpenseList, ExpenseSummary, useExpenses } from '@/features/expenses';
import { Loader2, Plus } from 'lucide-react';
import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';

export const TripExpensesTab = () => {
  const { trip } = useOutletContext<TripDetailOutletContext>();

  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | undefined>(undefined);
  const [deletingExpenseId, setDeletingExpenseId] = useState<string | null>(null);
  const [isDeletingExpense, setIsDeletingExpense] = useState(false);

  const { expenses, convertedSummary, loading, refetch, removeExpense } = useExpenses(
    trip.id,
    trip.currency,
  );

  const isReadonly = trip.status === 'completed' || trip.status === 'cancelled';

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setShowExpenseForm(true);
  };

  const handleFormClose = (open: boolean) => {
    if (!open) setEditingExpense(undefined);
    setShowExpenseForm(open);
  };

  const handleDeleteExpense = async () => {
    if (!deletingExpenseId) return;
    setIsDeletingExpense(true);
    try {
      await removeExpense(deletingExpenseId);
      setDeletingExpenseId(null);
    } finally {
      setIsDeletingExpense(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {!isReadonly && (
        <div className="flex shrink-0 justify-end px-5 pb-2 pt-3">
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-xl bg-[#2563EB] px-3 py-2 text-[13px] font-semibold text-white shadow-[0_3px_10px_rgba(37,99,235,0.3)]"
            onClick={() => {
              setEditingExpense(undefined);
              setShowExpenseForm(true);
            }}
          >
            <Plus className="h-3.5 w-3.5" />
            Добавить
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-5 pb-24 pt-2">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {convertedSummary && (
              <ExpenseSummary summary={convertedSummary} budget={trip.budget} />
            )}
            <ExpenseList
              expenses={expenses}
              onEdit={handleEditExpense}
              readonly={isReadonly}
            />
          </div>
        )}
      </div>

      <ExpenseForm
        tripId={trip.id}
        tripCurrency={trip.currency}
        open={showExpenseForm}
        onOpenChange={handleFormClose}
        existingExpense={editingExpense}
        onSuccess={refetch}
        onDeleteRequest={editingExpense ? () => setDeletingExpenseId(editingExpense.id) : undefined}
      />

      <DeleteExpenseSheet
        open={!!deletingExpenseId}
        onOpenChange={(open) => !open && setDeletingExpenseId(null)}
        onConfirm={handleDeleteExpense}
        loading={isDeletingExpense}
      />
    </div>
  );
};
