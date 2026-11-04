import { shareLink } from './share';

const data = { title: 'foo', url: 'http://localhost/recipe/bar' };

function stubNavigator(props: Partial<Pick<Navigator, 'share' | 'clipboard'>>) {
  for (const [key, value] of Object.entries({ share: undefined, clipboard: undefined, ...props })) {
    Object.defineProperty(navigator, key, { value, configurable: true });
  }
}

describe('shareLink', () => {
  afterEach(() => stubNavigator({}));

  it('uses the Web Share API when available', async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ share });
    await expect(shareLink(data)).resolves.toBe('shared');
    expect(share).toHaveBeenCalledWith(data);
  });

  it('does not copy when the user cancels the share sheet', async () => {
    const writeText = vi.fn();
    stubNavigator({
      share: vi.fn().mockRejectedValue(new DOMException('cancel', 'AbortError')),
      clipboard: { writeText } as unknown as Clipboard,
    });
    await expect(shareLink(data)).resolves.toBe('cancelled');
    expect(writeText).not.toHaveBeenCalled();
  });

  it('copies the link when Web Share is not supported', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ clipboard: { writeText } as unknown as Clipboard });
    await expect(shareLink(data)).resolves.toBe('copied');
    expect(writeText).toHaveBeenCalledWith(data.url);
  });

  it('copies the link when Web Share fails', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubNavigator({
      share: vi.fn().mockRejectedValue(new DOMException('denied', 'NotAllowedError')),
      clipboard: { writeText } as unknown as Clipboard,
    });
    await expect(shareLink(data)).resolves.toBe('copied');
  });

  it('reports failure when nothing is available', async () => {
    await expect(shareLink(data)).resolves.toBe('failed');
  });
});
