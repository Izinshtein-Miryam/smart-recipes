import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { chatStream } from '@/api/ai';
import type { AdaptedRecipe } from '@/api/types';

interface Message {
  role: 'user' | 'assistant';
  text: string;
}

/** Side dialog. A new instance (open) always starts a fresh conversation. */
export function ChatPanel({
  recipeId,
  onClose,
  onAdapted,
  onScaled,
}: {
  recipeId: string;
  onClose: () => void;
  onAdapted: (r: AdaptedRecipe) => void;
  onScaled: (servings: number) => void;
}) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const previousId = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const inputEl = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputEl.current?.focus();
    return () => abort.current?.abort();
  }, []);

  // Esc closes; Tab cycles inside the dialog (focus trap).
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key !== 'Tab' || !dialog.current) return;
      const items = dialog.current.querySelectorAll<HTMLElement>('button, input');
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput('');
    setError(false);
    setBusy(true);
    setMessages((m) => [...m, { role: 'user', text: message }, { role: 'assistant', text: '' }]);
    abort.current = new AbortController();
    try {
      for await (const ev of chatStream(
        { recipe_id: recipeId, message, previous_response_id: previousId.current },
        abort.current.signal,
      )) {
        if (ev.event === 'text_delta') {
          setMessages((m) =>
            m.map((x, i) => (i === m.length - 1 ? { ...x, text: x.text + ev.data.text } : x)),
          );
        } else if (ev.event === 'recipe_adapted') onAdapted(ev.data);
        else if (ev.event === 'recipe_scaled') onScaled(ev.data.servings);
        else if (ev.event === 'done') previousId.current = ev.data.response_id;
        else if (ev.event === 'error') setError(true);
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      ref={dialog}
      role="dialog"
      aria-modal="true"
      aria-label={t('chat.title')}
      className="bg-surface border-line shadow-lift fixed inset-y-0 end-0 z-30 flex w-full max-w-md flex-col border-s print:hidden"
    >
      <header className="border-line flex items-center justify-between border-b p-4">
        <h2 className="text-xl">{t('chat.title')}</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={t('common.close')}
          className="px-2 text-2xl"
        >
          ×
        </button>
      </header>
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
        {messages.length === 0 && <p className="text-muted">{t('chat.hint')}</p>}
        {messages.map((m, i) => (
          <p
            key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2 whitespace-pre-wrap ${
              m.role === 'user' ? 'bg-brand self-end text-white' : 'bg-parve-soft self-start'
            }`}
          >
            {m.text || (busy && i === messages.length - 1 ? '…' : '')}
          </p>
        ))}
        {error && <p role="alert">{t('common.aiUnavailable')}</p>}
      </div>
      <form onSubmit={(e) => void send(e)} className="border-line flex gap-2 border-t p-4">
        <input
          ref={inputEl}
          value={input}
          maxLength={500}
          onChange={(e) => setInput(e.target.value)}
          aria-label={t('chat.placeholder')}
          placeholder={t('chat.placeholder')}
          className="border-line min-w-0 flex-1 rounded-lg border px-3 py-2"
        />
        <button
          type="submit"
          disabled={busy}
          className="bg-brand rounded-lg px-4 text-white disabled:opacity-50"
        >
          {t('chat.send')}
        </button>
      </form>
    </div>
  );
}
