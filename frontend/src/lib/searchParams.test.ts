import { describe, expect, it } from 'vitest';

import { hasActiveFilters, parseFilters, toApiParams, toUrlParams } from './searchParams';

describe('searchParams', () => {
  it('parses valid filters from the URL', () => {
    const f = parseFilters(
      new URLSearchParams(
        'q=foo&kosher_type=dairy&dish_type=main&difficulty=easy&max_minutes=30&diet=vegan&diet=gluten_free&page=3',
      ),
    );
    expect(f).toEqual({
      q: 'foo',
      kosher_type: 'dairy',
      dish_type: 'main',
      difficulty: 'easy',
      max_minutes: '30',
      diet: ['gluten_free', 'vegan'],
      page: 3,
    });
  });

  it('ignores unknown values and malformed pages', () => {
    const f = parseFilters(
      new URLSearchParams('kosher_type=baz&max_minutes=7&diet=lorem&page=-2&dish_type='),
    );
    expect(f.kosher_type).toBe('');
    expect(f.max_minutes).toBe('');
    expect(f.diet).toEqual([]);
    expect(f.page).toBe(1);
    expect(hasActiveFilters(f)).toBe(false);
    expect(parseFilters(new URLSearchParams('page=abc')).page).toBe(1);
  });

  it('omits empty values and page 1 from the URL', () => {
    const empty = parseFilters(new URLSearchParams());
    expect(toUrlParams(empty).toString()).toBe('');
    const f = { ...empty, q: '  foo ', diet: ['vegan' as const], page: 2 };
    expect(toUrlParams(f).toString()).toBe('q=foo&diet=vegan&page=2');
  });

  it('adds the page size for the API call', () => {
    const f = parseFilters(new URLSearchParams('dish_type=main'));
    expect(toApiParams(f).toString()).toBe('dish_type=main&page_size=12');
  });
});
