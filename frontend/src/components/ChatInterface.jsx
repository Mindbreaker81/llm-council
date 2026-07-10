import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import CouncilTypeSelector from './CouncilTypeSelector';
import CustomCouncilPanel from './CustomCouncilPanel';
import { getCouncilTypeDisplay } from '../utils/council';
import { api } from '../api';
import './ChatInterface.css';

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
  statusMessage,
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
  const inputRef = useRef(null);
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
      window.setTimeout(() => inputRef.current?.focus(), 0);
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
  const activeCouncilModelCount = councilType === 'custom'
    ? selectedModels.length
    : activePreset?.models?.length || 0;
  const activeOrchestrator = councilType === 'custom'
    ? chairmanModel
    : activePreset?.chairman_model;
  const estimatedCalls = councilType === 'custom'
    ? (customCost?.calls_count || (selectedModels.length > 0 ? selectedModels.length * 2 + 1 : 0))
    : (activePreset?.models?.length ? activePreset.models.length * 2 + 1 : 0);

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
                      <span>{msg.progressText || 'Querying council models...'}</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>{msg.progressText || 'Reviewing model responses...'}</span>
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
                      <span>{msg.progressText || 'Synthesizing final answer...'}</span>
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
        {statusMessage && (
          <div className="form-status-message">{statusMessage}</div>
        )}
        <CouncilTypeSelector
          councilType={councilType}
          onChange={setCouncilType}
          isLoading={isLoading}
          presetCouncils={presetCouncils}
        />

        {councilType === 'custom' && (
          <CustomCouncilPanel
            modelQuery={modelQuery}
            setModelQuery={setModelQuery}
            freeOnly={freeOnly}
            setFreeOnly={setFreeOnly}
            minContext={minContext}
            setMinContext={setMinContext}
            customModels={customModels}
            isLoadingModels={isLoadingModels}
            selectedModels={selectedModels}
            chairmanModel={chairmanModel}
            toggleSelectedModel={toggleSelectedModel}
            setChairmanModel={setChairmanModel}
            customCost={customCost}
            customWarnings={customWarnings}
            modelError={modelError}
            isLoading={isLoading}
          />
        )}

        <div className="council-run-summary">
          <span>{activeCouncilModelCount || '-'} council models</span>
          <span>Orchestrator: {activeOrchestrator || 'None'}</span>
          <span>{estimatedCalls || '-'} estimated calls</span>
        </div>

        <div className="input-form-row">
          <textarea
            ref={inputRef}
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
            {councilType === 'custom' ? 'Ask Custom Council' : 'Ask Council'}
          </button>
        </div>
      </form>
    </div>
  );
}
