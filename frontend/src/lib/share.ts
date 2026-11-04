export type ShareResult = 'shared' | 'copied' | 'cancelled' | 'failed';

export interface ShareData {
  title: string;
  text?: string;
  url: string;
}

/**
 * Share a link with the Web Share API; fall back to copying it to the clipboard
 * when the API is missing or fails.
 */
export async function shareLink(data: ShareData): Promise<ShareResult> {
  if (typeof navigator.share === 'function') {
    try {
      await navigator.share(data);
      return 'shared';
    } catch (err) {
      // The user closed the share sheet - not an error, and no fallback needed.
      if (err instanceof DOMException && err.name === 'AbortError') return 'cancelled';
    }
  }

  try {
    if (!navigator.clipboard) return 'failed';
    await navigator.clipboard.writeText(data.url);
    return 'copied';
  } catch {
    return 'failed';
  }
}
