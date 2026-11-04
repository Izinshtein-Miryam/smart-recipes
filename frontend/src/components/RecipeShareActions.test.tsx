import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { RecipeShareActions } from './RecipeShareActions';

describe('RecipeShareActions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(navigator, 'share', { value: undefined, configurable: true });
  });

  it('opens the print dialog', async () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => undefined);
    render(<RecipeShareActions title="foo" />);
    await userEvent.click(screen.getByRole('button', { name: 'הדפסה' }));
    expect(print).toHaveBeenCalled();
  });

  it('shows "הקישור הועתק" after copying the link', async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    render(<RecipeShareActions title="foo" />);
    await user.click(screen.getByRole('button', { name: 'שיתוף' }));
    expect(writeText).toHaveBeenCalledWith(window.location.href);
    expect(await screen.findByRole('status')).toHaveTextContent('הקישור הועתק');
  });

  it('uses Web Share when supported, without a toast', async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', { value: share, configurable: true });
    render(<RecipeShareActions title="foo" description="bar" />);
    await userEvent.click(screen.getByRole('button', { name: 'שיתוף' }));
    expect(share).toHaveBeenCalledWith({ title: 'foo', text: 'bar', url: window.location.href });
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });
});
