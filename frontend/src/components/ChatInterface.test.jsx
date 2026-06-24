import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ChatInterface from './ChatInterface';

vi.mock('../utils/pdfExport', () => ({
  exportConversationToPDF: vi.fn(),
}));

vi.mock('../api', () => ({
  api: {
    listCouncils: vi.fn().mockResolvedValue({
      presets: [
        {
          type: 'premium',
          models: ['openai/gpt-5.1'],
          chairman_model: 'openai/gpt-5.1',
        },
      ],
    }),
    listModels: vi.fn().mockResolvedValue({ models: [] }),
    validateCouncil: vi.fn().mockResolvedValue({ valid: true, warnings: [] }),
  },
}));

describe('ChatInterface', () => {
  it('renders a custom council assistant response', () => {
    render(
      <ChatInterface
        isLoading={false}
        onSendMessage={vi.fn()}
        conversation={{
          id: 'conversation-1',
          title: 'Custom test',
          created_at: '2026-06-24T00:00:00',
          council_type: 'premium',
          messages: [
            {
              role: 'user',
              content: 'What should I use?',
            },
            {
              role: 'assistant',
              council_type: 'custom',
              stage1: [
                {
                  model: 'openai/gpt-oss-120b:free',
                  response: 'Use a custom council.',
                },
              ],
              stage2: [],
              stage3: {
                model: 'openai/gpt-oss-120b:free',
                response: 'Final custom answer.',
              },
              metadata: {
                label_to_model: {},
                aggregate_rankings: [],
              },
            },
          ],
        }}
      />
    );

    expect(screen.getByText('⚙ Custom')).toBeInTheDocument();
    expect(screen.getByText('Stage 3: Final Council Answer')).toBeInTheDocument();
    expect(screen.getByText('Final custom answer.')).toBeInTheDocument();
  });
});
