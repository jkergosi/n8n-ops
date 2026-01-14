import { describe, expect, it } from 'vitest';
import { cn } from '../utils';

describe('cn utility', () => {
  it('merges class names and removes duplicates', () => {
    expect(cn('p-4', 'text-sm', 'p-4', ['text-sm', 'font-bold'])).toBe(
      'p-4 text-sm font-bold'
    );
  });
});

