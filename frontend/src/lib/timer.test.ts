import { formatClock, timerSeconds } from './timer';

describe('timer helpers', () => {
  it.each([
    ['Lorem 10 דקות ipsum', 600],
    ['Cook for 5 minutes', 300],
    ['foo bar baz', null],
  ])('timerSeconds(%s)', (text, expected) => {
    expect(timerSeconds(text)).toBe(expected);
  });

  it('formats mm:ss', () => {
    expect(formatClock(75)).toBe('01:15');
  });
});
