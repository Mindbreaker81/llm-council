import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import { api } from '../api';
import './ChatInterface.css';

const getCouncilTypeDisplay = (councilType) => {
  if (councilType === 'premium') return '💎 Premium';
  if (councilType === 'economic') return '💰 Economic';
  if (councilType === 'free') return '🆓 Free';
  if (councilType === 'custom') return '⚙ Custom';
  return councilType || 'Premium';
};

const getEffectiveConversationCouncilType = (conversation) => {
  const latestAssistant = [...(conversation?.messages || [])]
    .reverse()
    .find((message) => message.role === 'assistant' && message.council_type);
  return latestAssistant?.council_type || conversation?.council_type || 'premium';
};

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [councilType, setCouncilType] = useState(
    conversation?.council_type || 'premium'
  );
  const [modelQuery, setModelQuery] = useState('');
  const [freeOnly, setFreeOnly] = useState(false);
  const [minContext, setMinContext] = useState('');
  const [customModels, setCustomModels] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [customWarnings, setCustomWarnings] = useState([]);
  const [customCost, setCustomCost] = useState(null);
  const [modelError, setModelError] = useState('');
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [presetCouncils, setPresetCouncils] = useState({});
  const [isExporting, setIsExporting] = useState(false);
  const messagesEndRef = useRef(null);
  const previousConversationIdRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  useEffect(() => {
    if (conversation && previousConversationIdRef.current !== conversation.id) {
      previousConversationIdRef.current = conversation.id;
      setCouncilType(getEffectiveConversationCouncilType(conversation));
    }
  }, [conversation]);

  useEffect(() => {
    let cancelled = false;

    api.listCouncils()
      .then((result) => {
        if (cancelled) return;
        const presets = {};
        (result.presets || []).forEach((preset) => {
          presets[preset.type] = preset;
        });
        setPresetCouncils(presets);
      })
      .catch((error) => {
        console.error('Failed to load council presets:', error);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (councilType !== 'custom') return;

    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      setIsLoadingModels(true);
      setModelError('');
      try {
        const result = await api.listModels({
          q: modelQuery,
          free_only: freeOnly,
          min_context: minContext,
          text_only: true,
          sort: freeOnly ? 'context-high-to-low' : 'pricing-low-to-high',
        });
        if (!controller.signal.aborted) {
          setCustomModels(result.models || []);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setModelError(error.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoadingModels(false);
        }
      }
    }, 250);

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [councilType, modelQuery, freeOnly, minContext]);

  useEffect(() => {
    if (!selectedModels.includes(chairmanModel)) {
      setChairmanModel(selectedModels[0] || '');
    }
  }, [selectedModels, chairmanModel]);

  useEffect(() => {
    if (councilType !== 'custom' || selectedModels.length < 2 || !chairmanModel) {
      setCustomCost(null);
      return;
    }

    let cancelled = false;
    const timeout = setTimeout(async () => {
      try {
        const validation = await api.validateCouncil(selectedModels, chairmanModel);
        if (cancelled) return;
        setCustomWarnings(validation.warnings || []);
        setCustomCost(validation.estimated_cost || null);
        if (!validation.valid) {
          setModelError((validation.errors || ['Invalid custom council']).join(' '));
        } else {
          setModelError('');
        }
      } catch {
        if (!cancelled) {
          setCustomCost(null);
        }
      }
    }, 350);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [councilType, selectedModels, chairmanModel]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      let customCouncil = null;
      if (councilType === 'custom') {
        if (selectedModels.length < 2) {
          setModelError('Select at least 2 council models');
          return;
        }
        if (!chairmanModel) {
          setModelError('Select a chairman model');
          return;
        }

        let validation;
        try {
          validation = await api.validateCouncil(selectedModels, chairmanModel);
        } catch (error) {
          setModelError(error.message);
          return;
        }
        setCustomWarnings(validation.warnings || []);
        if (!validation.valid) {
          setModelError((validation.errors || ['Invalid custom council']).join(' '));
          return;
        }
        customCouncil = {
          models: selectedModels,
          chairman_model: chairmanModel,
        };
      }

      onSendMessage(input, councilType, customCouncil);
      setInput('');
    }
  };

  const toggleSelectedModel = (modelId) => {
    setModelError('');
    setCustomCost(null);
    setSelectedModels((prev) => {
      if (prev.includes(modelId)) {
        return prev.filter((item) => item !== modelId);
      }
      if (prev.length >= 8) {
        setModelError('Select at most 8 council models');
        return prev;
      }
      return [...prev, modelId];
    });
  };

  const activePreset = presetCouncils[councilType];

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleExportPDF = async () => {
    if (!conversation || !conversation.messages || conversation.messages.length === 0) {
      alert('No messages to export');
      return;
    }

    setIsExporting(true);
    try {
      const { exportConversationToPDF } = await import('../utils/pdfExport');
      await exportConversationToPDF(conversation);
    } catch (error) {
      console.error('Error exporting PDF:', error);
      alert('Error generating PDF: ' + error.message);
    } finally {
      setIsExporting(false);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">
                    LLM Council
                    <span className="council-type-indicator">
                      {getCouncilTypeDisplay(msg.council_type || conversation.council_type || 'premium')}
                    </span>
                  </div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
        
        {conversation.messages.length > 0 && (
          <div className="export-pdf-container">
            <button
              className="export-pdf-button"
              onClick={handleExportPDF}
              disabled={isExporting || isLoading}
              title="Export conversation to PDF"
            >
              {isExporting ? (
                <>
                  <span className="spinner-small"></span>
                  Generating PDF...
                </>
              ) : (
                <>
                  📄 Export PDF
                </>
              )}
            </button>
          </div>
        )}
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div className="council-type-selector">
          <label>Council Type:</label>
          <div className="council-type-options">
            <label className="council-type-option">
              <input
                type="radio"
                name="councilType"
                value="premium"
                checked={councilType === 'premium'}
                onChange={(e) => setCouncilType(e.target.value)}
                disabled={isLoading}
              />
              <span>Premium</span>
            </label>
            <label className="council-type-option">
              <input
                type="radio"
                name="councilType"
                value="economic"
                checked={councilType === 'economic'}
                onChange={(e) => setCouncilType(e.target.value)}
                disabled={isLoading}
              />
              <span>Economic</span>
            </label>
            <label className="council-type-option">
              <input
                type="radio"
                name="councilType"
                value="free"
                checked={councilType === 'free'}
                onChange={(e) => setCouncilType(e.target.value)}
                disabled={isLoading}
              />
              <span>Free</span>
            </label>
            <label className="council-type-option">
              <input
                type="radio"
                name="councilType"
                value="custom"
                checked={councilType === 'custom'}
                onChange={(e) => setCouncilType(e.target.value)}
                disabled={isLoading}
              />
              <span>Custom</span>
            </label>
          </div>
        </div>

        {councilType !== 'custom' && activePreset && (
          <div className="active-models-panel">
            <div className="active-models-header">
              <span>Active models</span>
              <span>Chairman: {activePreset.chairman_model}</span>
            </div>
            <div className="active-model-list">
              {activePreset.models.map((model) => (
                <span key={model} className="active-model-chip">
                  {model}
                </span>
              ))}
            </div>
          </div>
        )}

        {councilType === 'custom' && (
          <div className="custom-council-panel">
            <div className="custom-council-title">
              Choose custom council models
            </div>
            <div className="custom-council-toolbar">
              <input
                className="model-search-input"
                type="search"
                placeholder="Search models"
                value={modelQuery}
                onChange={(e) => setModelQuery(e.target.value)}
                disabled={isLoading}
              />
              <label className="custom-filter">
                <input
                  type="checkbox"
                  checked={freeOnly}
                  onChange={(e) => setFreeOnly(e.target.checked)}
                  disabled={isLoading}
                />
                <span>Free only</span>
              </label>
              <select
                className="context-filter"
                value={minContext}
                onChange={(e) => setMinContext(e.target.value)}
                disabled={isLoading}
              >
                <option value="">Any context</option>
                <option value="32000">32k+</option>
                <option value="128000">128k+</option>
                <option value="1000000">1M+</option>
              </select>
            </div>

            <div className="custom-council-summary">
              <span>{selectedModels.length}/8 models selected</span>
              <span>Chairman: {chairmanModel || 'None'}</span>
              {customCost && (
                <span>
                  Est. {customCost.calls_count} calls · ${Number(customCost.estimated_total_usd).toFixed(6)}
                </span>
              )}
            </div>

            {modelError && <div className="custom-council-error">{modelError}</div>}
            {customWarnings.length > 0 && (
              <div className="custom-council-warning">
                {customWarnings.join(' ')}
              </div>
            )}

            <div className="model-list">
              {isLoadingModels ? (
                <div className="model-list-status">Loading models...</div>
              ) : customModels.length === 0 ? (
                <div className="model-list-status">No matching models</div>
              ) : (
                customModels.slice(0, 80).map((model) => {
                  const selected = selectedModels.includes(model.id);
                  return (
                    <div key={model.id} className={`model-row ${selected ? 'selected' : ''}`}>
                      <label className="model-select">
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => toggleSelectedModel(model.id)}
                          disabled={isLoading}
                        />
                        <span>
                          <strong>{model.name}</strong>
                          <small>{model.id}</small>
                        </span>
                      </label>
                      <div className="model-meta">
                        {model.free && <span className="model-badge">Free</span>}
                        {model.dynamic_router && <span className="model-badge">Router</span>}
                        <span>{model.context_length ? `${Math.round(model.context_length / 1000)}k ctx` : 'ctx n/a'}</span>
                        <span>
                          ${model.price_per_million?.prompt || '0'}/M in · ${model.price_per_million?.completion || '0'}/M out
                        </span>
                        {selected && (
                          <button
                            type="button"
                            className={`chairman-button ${chairmanModel === model.id ? 'active' : ''}`}
                            onClick={() => setChairmanModel(model.id)}
                            disabled={isLoading}
                          >
                            Chairman
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        <div className="input-form-row">
          <textarea
            className="message-input"
            placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
