/**
 * API client for the LLM Council backend.
 */

import { createSseEventParser } from './utils/sse';

// Dynamically determine API base URL
// If running on localhost, use localhost:8001
// If running on a remote IP/domain, use that IP/domain:8001
const getApiBase = () => {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  return `${protocol}//${hostname}:8001`;
};

const API_BASE = getApiBase();

const buildQuery = (params) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value);
    }
  });
  const text = query.toString();
  return text ? `?${text}` : '';
};

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation(councilType = 'premium') {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ council_type: councilType }),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        method: 'DELETE',
      }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * List OpenRouter models for custom council selection.
   */
  async listModels(params = {}) {
    const response = await fetch(`${API_BASE}/api/models${buildQuery(params)}`);
    if (!response.ok) {
      throw new Error('Failed to list models');
    }
    return response.json();
  },

  /**
   * Validate a custom council selection.
   */
  async validateCouncil(models, chairmanModel) {
    const response = await fetch(`${API_BASE}/api/councils/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ models, chairman_model: chairmanModel }),
    });
    if (!response.ok) {
      throw new Error('Failed to validate council');
    }
    return response.json();
  },

  /**
   * List built-in council presets and active models.
   */
  async listCouncils() {
    const response = await fetch(`${API_BASE}/api/councils`);
    if (!response.ok) {
      throw new Error('Failed to list councils');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, councilType = 'premium', customCouncil = null) {
    const body = { content, council_type: councilType };
    if (customCouncil) {
      body.custom_council = customCouncil;
    }

    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @param {string} councilType - Type of council to use ("premium" or "economic")
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent, councilType = 'premium', customCouncil = null) {
    const body = { content, council_type: councilType };
    if (customCouncil) {
      body.custom_council = customCouncil;
    }

    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = createSseEventParser(onEvent);

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        parser.push(decoder.decode());
        parser.flush();
        break;
      }

      parser.push(decoder.decode(value, { stream: true }));
    }
  },
};
