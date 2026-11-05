import { useState } from 'react';
import { useTranslation } from 'react-i18next';

/** Free-text tags: Enter or comma adds, the chip button removes. */
export function TagInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string[];
  onChange: (tags: string[]) => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState('');

  const add = () => {
    const tag = draft.trim();
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setDraft('');
  };

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault();
              add();
            }
          }}
          className="border-line bg-surface min-w-0 flex-1 rounded-lg border px-3 py-2"
        />
        <button type="button" onClick={add} className="bg-brand rounded-lg px-4 text-white">
          {t('common.add')}
        </button>
      </div>
      <ul className="flex flex-wrap gap-2" aria-label={label}>
        {value.map((tag) => (
          <li key={tag} className="bg-parve-soft flex items-center gap-1 rounded-full px-3 py-1">
            {tag}
            <button
              type="button"
              aria-label={`${t('common.remove')} ${tag}`}
              onClick={() => onChange(value.filter((v) => v !== tag))}
              className="text-muted hover:text-brand px-1"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
