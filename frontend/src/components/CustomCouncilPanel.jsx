import './ChatInterface.css';

export default function CustomCouncilPanel({
  modelQuery,
  setModelQuery,
  freeOnly,
  setFreeOnly,
  minContext,
  setMinContext,
  customModels,
  isLoadingModels,
  selectedModels,
  chairmanModel,
  toggleSelectedModel,
  setChairmanModel,
  customCost,
  customWarnings,
  modelError,
  isLoading,
}) {
  return (
    <div className="custom-council-panel">
      <div className="custom-council-title">1. Choose council models</div>
      <p className="custom-council-help">
        Select 2-8 models for Stage 1 and peer review.
      </p>
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
        <span>Orchestrator: {chairmanModel || 'None'}</span>
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
                      Orchestrator
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
      <div className="custom-orchestrator-step">
        <strong>2. Choose orchestrator</strong>
        <span>
          Click <b>Orchestrator</b> on a selected model. It writes the final Stage 3 answer.
        </span>
      </div>
    </div>
  );
}
