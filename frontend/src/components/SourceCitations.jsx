import React from 'react';

/**
 * Displays citations/sources for a bot message.
 */
function SourceCitations({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-panel">
      <div className="sources-panel-title">📚 Sources</div>
      <div>
        {sources.map((src, idx) => (
          <span key={idx} className="source-tag">
            📄 {src}
          </span>
        ))}
      </div>
    </div>
  );
}

export default SourceCitations;
