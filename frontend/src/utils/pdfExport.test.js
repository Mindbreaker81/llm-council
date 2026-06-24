import { describe, expect, it } from 'vitest';
import { generatePdfContent } from './pdfExport';

function flattenText(value) {
  if (!value) return [];
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(flattenText);
  if (typeof value === 'object') {
    return Object.values(value).flatMap(flattenText);
  }
  return [];
}

describe('generatePdfContent', () => {
  it('includes export provenance and complete council metadata', () => {
    const content = generatePdfContent({
      id: 'conversation-123',
      title: 'PDF audit',
      created_at: '2026-06-24T10:00:00.000Z',
      council_type: 'custom',
      messages: [
        {
          role: 'user',
          content: 'What should we do?'
        },
        {
          role: 'assistant',
          council_type: 'custom',
          custom_council: {
            models: ['openai/gpt-5.1', 'anthropic/claude-sonnet-4.5'],
            chairman_model: 'openai/gpt-5.1'
          },
          model_metadata: {
            'openai/gpt-5.1': {
              name: 'GPT 5.1',
              context_length: 128000,
              pricing: {
                prompt: '0.00000125',
                completion: '0.00001'
              }
            },
            'anthropic/claude-sonnet-4.5': {
              name: 'Claude Sonnet 4.5',
              context_length: 200000,
              pricing: {
                prompt: '0.000003',
                completion: '0.000015'
              }
            }
          },
          metadata: {
            label_to_model: {
              A: 'openai/gpt-5.1',
              B: 'anthropic/claude-sonnet-4.5'
            },
            aggregate_rankings: []
          },
          stage1: [
            {
              model: 'openai/gpt-5.1',
              response: 'Use a council.'
            },
            {
              model: 'anthropic/claude-sonnet-4.5',
              response: 'Compare the options.'
            }
          ],
          stage2: [
            {
              model: 'anthropic/claude-sonnet-4.5',
              ranking: 'B, A',
              parsed_ranking: ['B', 'A']
            }
          ],
          stage3: {
            model: 'openai/gpt-5.1',
            response: 'Final answer.'
          }
        }
      ]
    });

    const text = flattenText(content).join('\n');

    expect(text).toContain('Export Details');
    expect(text).toContain('Source');
    expect(text).toContain('LLM Council');
    expect(text).toContain('Conversation ID');
    expect(text).toContain('conversation-123');
    expect(text).toContain('Council models');
    expect(text).toContain('openai/gpt-5.1');
    expect(text).toContain('anthropic/claude-sonnet-4.5');
    expect(text).toContain('Peer reviewers');
    expect(text).toContain('Orchestrator: openai/gpt-5.1');
    expect(text).toContain('OpenRouter Model Snapshot');
    expect(text).toContain('GPT 5.1');
    expect(text).toContain('Claude Sonnet 4.5');
    expect(text).not.toContain('Chairman:');
  });
});
