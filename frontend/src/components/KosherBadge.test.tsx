import { render, screen } from '@testing-library/react';

import { KosherBadge } from './KosherBadge';

describe('KosherBadge', () => {
  it.each([
    ['meat', 'בשרי'],
    ['dairy', 'חלבי'],
    ['parve', 'פרווה'],
  ] as const)('renders %s label', (type, label) => {
    render(<KosherBadge type={type} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
