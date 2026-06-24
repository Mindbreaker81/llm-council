import assert from 'node:assert/strict';
import { createSseEventParser } from '../src/utils/sse.js';

function collectEvents(chunks, flush = true) {
  const events = [];
  const errors = [];
  const parser = createSseEventParser(
    (type, event) => events.push({ type, event }),
    (...args) => errors.push(args)
  );

  chunks.forEach((chunk) => parser.push(chunk));
  if (flush) parser.flush();

  return { events, errors };
}

{
  const { events, errors } = collectEvents([
    'data: {"type":"stage1_',
    'complete","data":[1]}\n\n',
  ]);

  assert.equal(errors.length, 0);
  assert.deepEqual(events, [
    { type: 'stage1_complete', event: { type: 'stage1_complete', data: [1] } },
  ]);
}

{
  const { events, errors } = collectEvents([
    'data: {"type":"a"}\n\n',
    'data: {"type":"b","message":"ok"}\n\n',
  ]);

  assert.equal(errors.length, 0);
  assert.deepEqual(events.map((item) => item.type), ['a', 'b']);
  assert.equal(events[1].event.message, 'ok');
}

{
  const { events, errors } = collectEvents([
    'event: ignored\n',
    'data: {"type":"complete"}',
  ]);

  assert.equal(errors.length, 0);
  assert.deepEqual(events, [
    { type: 'complete', event: { type: 'complete' } },
  ]);
}

{
  const { events, errors } = collectEvents([
    'data: {"type":',
    '\n\n',
  ]);

  assert.equal(events.length, 0);
  assert.equal(errors.length, 1);
}

console.log('sse parser tests passed');
