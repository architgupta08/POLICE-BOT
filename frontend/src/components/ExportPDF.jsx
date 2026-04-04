import React from 'react';
import { exportSessionPDF } from '../services/api';

/**
 * Button to export the current chat session as a PDF.
 */
function ExportPDF({ sessionId, disabled }) {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleExport = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      await exportSessionPDF(sessionId);
    } catch (err) {
      setError('PDF export failed. Please try again.');
      console.error('PDF export error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
      <button
        className="btn-toolbar"
        onClick={handleExport}
        disabled={disabled || loading || !sessionId}
        title="Export this conversation as PDF"
      >
        {loading ? '⏳ Exporting…' : '📄 Export PDF'}
      </button>
      {error && (
        <span style={{ fontSize: 11, color: 'var(--danger)' }}>{error}</span>
      )}
    </div>
  );
}

export default ExportPDF;
