import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router';

import { adminApprove, adminList, adminReject, adminUpdate } from '@/api/admin';
import { ApiError, getAdminToken, setAdminToken } from '@/api/client';
import type { Recipe, RecipeStatus } from '@/api/types';
import { KosherBadge } from '@/components/KosherBadge';
import { RecipeForm } from '@/components/RecipeForm';

const STATUSES: RecipeStatus[] = ['pending', 'approved', 'rejected'];

export function AdminQueuePage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [status, setStatus] = useState<RecipeStatus>('pending');
  const [q, setQ] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const key = ['admin-recipes', status, q];
  const list = useQuery({ queryKey: key, queryFn: () => adminList(status, q), retry: false });
  const refresh = () => void qc.invalidateQueries({ queryKey: ['admin-recipes'] });
  const approve = useMutation({ mutationFn: adminApprove, onSuccess: refresh });
  const reject = useMutation({ mutationFn: adminReject, onSuccess: refresh });
  const update = useMutation({
    mutationFn: ({ id, v }: { id: string; v: Parameters<typeof adminUpdate>[1] }) =>
      adminUpdate(id, v),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });

  if (!getAdminToken() || (list.error instanceof ApiError && list.error.status === 401)) {
    setAdminToken(null);
    return <Navigate to="/admin/login" replace />;
  }

  const btn = 'rounded-full border px-4 py-1.5 text-sm font-semibold';
  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-3xl">{t('admin.queueTitle')}</h1>
      <div className="flex flex-wrap items-end gap-4">
        <div role="tablist" aria-label={t('admin.status')} className="flex gap-2">
          {STATUSES.map((s) => (
            <button
              key={s}
              role="tab"
              aria-selected={status === s}
              onClick={() => setStatus(s)}
              className={`${btn} ${status === s ? 'bg-brand border-brand text-white' : 'border-line'}`}
            >
              {t(`admin.${s}`)}
            </button>
          ))}
        </div>
        <label className="flex flex-col text-sm font-semibold">
          {t('filters.search')}
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border-line bg-surface rounded-lg border px-3 py-1.5"
          />
        </label>
      </div>
      {list.isPending && <p className="text-muted">{t('common.loading')}</p>}
      {list.data?.length === 0 && <p className="text-muted">{t('admin.empty')}</p>}
      <ul className="flex flex-col gap-4">
        {list.data?.map((r: Recipe) => (
          <li key={r.id} className="bg-surface border-line rounded-card border p-5">
            <div className="flex flex-wrap items-center gap-3">
              <KosherBadge type={r.kashrut} />
              <h2 className="flex-1 text-xl">{r.title}</h2>
              <div className="flex flex-wrap gap-2">
                <button
                  className={`${btn} border-line`}
                  onClick={() => setEditing(editing === r.id ? null : r.id)}
                >
                  {t('admin.edit')}
                </button>
                {r.status !== 'rejected' && (
                  <button
                    className={`${btn} bg-green border-green text-white`}
                    disabled={approve.isPending}
                    onClick={() => approve.mutate(r.id)}
                  >
                    {r.status === 'approved' ? t('admin.recalc') : t('admin.approve')}
                  </button>
                )}
                {r.status !== 'rejected' && (
                  <button
                    className={`${btn} border-meat text-meat`}
                    onClick={() => {
                      if (window.confirm(t('admin.confirmReject'))) reject.mutate(r.id);
                    }}
                  >
                    {t('admin.reject')}
                  </button>
                )}
              </div>
            </div>
            <p className="text-muted mt-1 text-sm">{r.description}</p>
            {r.status === 'approved' && !r.nutrition && (
              <p className="text-meat mt-1 text-sm">{t('admin.noNutrition')}</p>
            )}
            {editing === r.id && (
              <div className="mt-4">
                <RecipeForm
                  initial={{ ...r, lang: r.lang }}
                  submitLabel={t('admin.save')}
                  busy={update.isPending}
                  error={update.isError ? t('submit.error') : null}
                  onSubmit={(v) => update.mutate({ id: r.id, v })}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
      {(approve.isError || reject.isError) && <p role="alert">{t('submit.error')}</p>}
    </section>
  );
}
