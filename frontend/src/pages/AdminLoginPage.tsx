import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { adminLogin } from '@/api/admin';
import { setAdminToken } from '@/api/client';

export function AdminLoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const login = useMutation({
    mutationFn: () => adminLogin(password),
    onSuccess: (r) => {
      setAdminToken(r.access_token);
      void navigate('/admin/queue');
    },
  });
  return (
    <section className="flex max-w-sm flex-col gap-4">
      <h1 className="text-3xl">{t('admin.loginTitle')}</h1>
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          login.mutate();
        }}
      >
        <label className="flex flex-col gap-1 font-semibold">
          {t('admin.password')}
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border-line bg-surface rounded-lg border px-3 py-2"
          />
        </label>
        {login.isError && <p role="alert">{t('admin.badPassword')}</p>}
        <button
          type="submit"
          disabled={login.isPending}
          className="bg-brand rounded-full px-6 py-2 font-semibold text-white"
        >
          {t('admin.login')}
        </button>
      </form>
    </section>
  );
}
