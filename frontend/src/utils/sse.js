export function createSseEventParser(onEvent, onError = console.error) {
  let buffer = '';

  const processEvent = (rawEvent) => {
    const dataLines = rawEvent
      .split('\n')
      .filter((line) => line.startsWith('data: '))
      .map((line) => line.slice(6));

    if (dataLines.length === 0) return;

    try {
      const event = JSON.parse(dataLines.join('\n'));
      onEvent(event.type, event);
    } catch (error) {
      onError('Failed to parse SSE event:', error);
    }
  };

  return {
    push(chunk) {
      buffer += chunk;
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      events.forEach(processEvent);
    },
    flush() {
      if (buffer.trim()) {
        processEvent(buffer);
      }
      buffer = '';
    },
  };
}
