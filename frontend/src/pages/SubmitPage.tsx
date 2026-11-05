import { useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { submitRecipe } from '@/api/admin';
import { ApiError } from '@/api/client';
import { RecipeForm } from '@/components/RecipeForm';
import { EMPTY_RECIPE as EMPTY } from '@/lib/recipeForm';

export function SubmitPage() {
  const { t, i18n } = useTranslation();
  const submit = useMutation({
    mutationFn: ({
      v,
      image,
    }: Parameters<typeof submitRecipe>[0] extends infer B ? { v: B; image: File | null } : never) =>
      submitRecipe(v, image),
  });
  const error = submit.error
    ? submit.error instanceof ApiError && submit.error.status === 429
      ? t('submit.limit')
      : submit.error instanceof ApiError && submit.error.status === 413
        ? t('submit.imageTooLarge')
        : submit.error instanceof ApiError && submit.error.status === 415
          ? t('submit.imageType')
          : t('submit.error')
    : null;

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-4xl">{t('submit.title')}</h1>
      {submit.isSuccess ? (
        <p role="status" className="bg-dairy-soft text-dairy rounded-lg p-4 font-semibold">
          {t('submit.pending')}
        </p>
      ) : (
        <RecipeForm
          withImage
          initial={{ ...EMPTY, lang: i18n.language === 'en' ? 'en' : 'he' }}
          submitLabel={t('submit.send')}
          busy={submit.isPending}
          error={error}
          onSubmit={(v, image) => submit.mutate({ v, image })}
        />
      )}
    </section>
  );
}
