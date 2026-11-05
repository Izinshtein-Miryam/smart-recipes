import { parseSse } from './ai';

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(c) {
      chunks.forEach((x) => c.enqueue(enc.encode(x)));
      c.close();
    },
  });
}

describe('parseSse', () => {
  it('parses CRLF events split across chunks', async () => {
    const body = streamOf(
      'event: text_delta\r\ndata: {"text":"Lo"}\r\n\r\nevent: do',
      'ne\r\ndata: {"response_id":"r1"}\r\n\r\n',
    );
    const out = [];
    for await (const ev of parseSse(body)) out.push(ev);
    expect(out).toEqual([
      { event: 'text_delta', data: { text: 'Lo' } },
      { event: 'done', data: { response_id: 'r1' } },
    ]);
  });
});
