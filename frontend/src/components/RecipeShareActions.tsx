import { shareLink } from '@/lib/share';
import { useToast } from '@/lib/useToast';

import { Toast } from './Toast';

interface Props {
  title: string;
  description?: string;
}

const buttonClass =
  'border-line hover:border-brand inline-flex items-center gap-2 rounded-[10px] border bg-transparent px-4 py-2';

/** Print and share buttons for the recipe page. Hidden in print. */
export function RecipeShareActions({ title, description }: Props) {
  const toast = useToast();

  async function handleShare() {
    const url = window.location.href;
    const result = await shareLink({ title, text: description, url });
    if (result === 'copied') toast.show('הקישור הועתק');
    else if (result === 'failed') toast.show(`קישור לשיתוף: ${url}`);
  }

  return (
    <div className="no-print flex flex-wrap gap-2">
      <button type="button" className={buttonClass} onClick={() => window.print()}>
        הדפסה
      </button>
      <button type="button" className={buttonClass} onClick={() => void handleShare()}>
        שיתוף
      </button>
      <Toast message={toast.message} />
    </div>
  );
}
