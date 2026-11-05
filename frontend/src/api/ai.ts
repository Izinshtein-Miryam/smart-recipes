import { api, ApiError } from './client';
import type { AdaptedRecipe, FridgeSearchItem, Ingredient, Lang } from './types';
import type { RecipeFilters } from './types';

export function fridgeSearch(body: {
  ingredients: string[];
  lang: Lang;
  max_minutes?: number;
  difficulty?: string;
  kashrut?: string;
}) {
  return api<{ results: FridgeSearchItem[] }>('/ai/fridge-search', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function adaptRecipe(recipeId: string, instruction: string) {
  return api<AdaptedRecipe>('/ai/adapt', {
    method: 'POST',
    body: JSON.stringify({ recipe_id: recipeId, instruction }),
  });
}

export type ChatEvent =
  | { event: 'text_delta'; data: { text: string } }
  | { event: 'tool_started'; data: { name: string } }
  | { event: 'recipe_adapted'; data: AdaptedRecipe }
  | { event: 'recipe_scaled'; data: { servings: number; ingredients: Ingredient[] } }
  | { event: 'done'; data: { response_id: string | null } }
  | { event: 'error'; data: { code: string } };

/** Parses a text/event-stream body (sse-starlette uses CRLF line endings). */
export async function* parseSse(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    let idx: number;
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let event = 'message';
      const data: string[] = [];
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
      }
      if (data.length) yield { event, data: JSON.parse(data.join('\n')) } as ChatEvent;
    }
    if (done) return;
  }
}

export async function* chatStream(
  body: { recipe_id: string; message: string; previous_response_id: string | null },
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, res.statusText);
  yield* parseSse(res.body);
}

export type { RecipeFilters };
