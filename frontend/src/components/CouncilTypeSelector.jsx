import './ChatInterface.css';
import { getCouncilTypeDisplay } from '../utils/council';

export default function CouncilTypeSelector({
  councilType,
  onChange,
  isLoading,
  presetCouncils,
}) {
  const activePreset = presetCouncils[councilType];

  const options = [
    { value: 'premium' },
    { value: 'economic' },
    { value: 'free' },
    { value: 'custom' },
  ];

  return (
    <div className="council-type-selector">
      <label>Council Type:</label>
      <div className="council-type-options">
        {options.map(({ value }) => (
          <label key={value} className="council-type-option">
            <input
              type="radio"
              name="councilType"
              value={value}
              checked={councilType === value}
              onChange={(e) => onChange(e.target.value)}
              disabled={isLoading}
            />
            <span>
              {getCouncilTypeDisplay(value)}
            </span>
          </label>
        ))}
      </div>

      {councilType !== 'custom' && activePreset && (
        <div className="active-models-panel">
          <div className="active-models-header">
            <span>Active models</span>
            <span>Orchestrator: {activePreset.chairman_model}</span>
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
    </div>
  );
}
