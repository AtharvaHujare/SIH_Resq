import React, { useState } from 'react';
import { FileText, Download, Eye, CheckCircle2, ShieldAlert, MapPin, Printer } from 'lucide-react';
import { VULNERABLE_HABITATIONS } from '../data/mockData';

export default function Reports() {
  const [selectedReport, setSelectedReport] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState(null);

  const reportTemplates = [
    {
      id: 'REP_01',
      title: 'Habitation Relocation Action Dossier (Gazetted Order)',
      type: 'Executive Government Dossier',
      description: 'Comprehensive village-specific dossier including spatial coordinates, demographic exposure, TreeSHAP explainability, and recipient site carrying-capacity audit.',
      pages: '12 Pages (PDF)',
      frequency: 'Per Critical Settlement'
    },
    {
      id: 'REP_02',
      title: 'Statewide Multi-Hazard Risk & Red Zone Assessment',
      type: 'Macro Geospatial Summary',
      description: 'Aggregated district summaries combining PostGIS slope gradients, precipitation anomalies, and spatial exposure metrics.',
      pages: '28 Pages (PDF)',
      frequency: 'Bi-Weekly Monsoon Update'
    },
    {
      id: 'REP_03',
      title: 'Priority 1 Urgent Relocation Schedule & Resource Budget',
      type: 'Administrative Allocation Plan',
      description: 'Ranked priority queue for immediate 0-6 month relocation, detailing required water pipelines, road widening, and school classroom additions.',
      pages: '8 Pages (Spreadsheet / PDF)',
      frequency: 'Financial Sanction Schedule'
    },
    {
      id: 'REP_04',
      title: 'Candidate Relocation Sites Comparative Feasibility Audit',
      type: 'Technical Engineering Report',
      description: 'Soil stability, hydrogeological water yield, road distance decay, and carrying capacity headroom across all 64 verified safe parcels.',
      pages: '34 Pages (PDF)',
      frequency: 'Land Bank Catalog'
    }
  ];

  const handleDownload = (report) => {
    setDownloadSuccess(`Generated and downloaded: ${report.title}`);
    setTimeout(() => setDownloadSuccess(null), 4000);
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-title-group">
          <h1>Official Governance Reports & Action Dossiers</h1>
          <span className="page-subtitle">
            Export standardized administrative briefs, statutory relocation orders, and technical feasibility reports for SDMA & District Collectors
          </span>
        </div>
      </div>

      {/* Success Notification Banner */}
      {downloadSuccess && (
        <div
          style={{
            background: '#f0fdf4',
            border: '1px solid var(--risk-low)',
            color: '#166534',
            padding: '12px 18px',
            borderRadius: '10px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <CheckCircle2 size={18} color="var(--risk-low)" />
          <span>{downloadSuccess}</span>
        </div>
      )}

      {/* Report Templates Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px', marginBottom: '30px' }}>
        {reportTemplates.map((rep) => (
          <div
            key={rep.id}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '22px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span className="badge badge-blue">{rep.type}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{rep.pages}</span>
              </div>

              <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', margin: '8px 0' }}>{rep.title}</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '16px' }}>
                {rep.description}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ flex: 1 }}
                onClick={() => setSelectedReport(rep)}
              >
                <Eye size={14} />
                <span>Preview Draft</span>
              </button>
              <button
                className="btn btn-primary btn-sm"
                style={{ flex: 1 }}
                onClick={() => handleDownload(rep)}
              >
                <Download size={14} />
                <span>Export PDF</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Report Preview Modal */}
      {selectedReport && (
        <div className="modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="modal-card" style={{ width: '700px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="var(--gis-blue)" />
                <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--text-primary)' }}>Dossier Preview: {selectedReport.title}</h3>
              </div>
              <button onClick={() => setSelectedReport(null)} style={{ color: 'var(--text-muted)' }}>
                ✕
              </button>
            </div>

            <div className="modal-body" style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.8rem', color: '#1e293b', lineHeight: 1.6, padding: '20px' }}>
              <div style={{ textAlign: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', marginBottom: '16px' }}>
                <strong style={{ fontSize: '0.95rem', color: '#0f172a' }}>
                  GOVERNMENT OF MAHARASHTRA • DISASTER MANAGEMENT RELOCATION DOSSIER
                </strong>
                <br />
                Reference Code: SDMA/RELOC/2026/PS191-WGHATS • Generated: 09-Sep-2026
              </div>

              <div>
                <strong>1. STATUTORY EXECUTIVE SUMMARY</strong>
                <br />
                Under Section 38 of the Disaster Management Act, this document orders the phased relocation planning for high-risk settlement clusters identified by the Intelligent GIS Decision Support System.
              </div>

              <div style={{ marginTop: '12px' }}>
                <strong>2. TARGET VULNERABLE HABITATION IDENTIFIER:</strong>
                <br />
                • Primary Habitation: Taliye Wadi (Upper Sector), District Raigad
                <br />
                • Geomorphological Risk Score: 92.4 / 100 (CRITICAL RED ZONE)
                <br />
                • Exposed Population: 2,480 residents (512 households)
                <br />
                • Dominant Geophysical Threat: 34.2° Slope Shear Failure + 294mm Antecedent Rainfall
              </div>

              <div style={{ marginTop: '12px' }}>
                <strong>3. RECOMMENDED SAFE HAVEN RECIPIENT PARCEL:</strong>
                <br />
                • Target Parcel: Plateau Ridge Sector 2 (Mangaon Upper)
                <br />
                • Safety Clearance: 6.8 km outside active debris flow hazard margin
                <br />
                • Usable Acreage: 45.7 acres (185,000 m²)
                <br />
                • Carrying Capacity Ratio: 1.65x (Absorbs 2,480 people; maximum ceiling 4,100)
                <br />
                • Potable Water Status: Verified 450 kL/day sustainable aquifer yield
              </div>

              <div style={{ marginTop: '12px' }}>
                <strong>4. SIGN-OFF AUTHORIZATION:</strong>
                <br />
                Certified by State Disaster Management Authority • Relief Commissioner Directorate
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedReport(null)}>
                Close Preview
              </button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  handleDownload(selectedReport);
                  setSelectedReport(null);
                }}
              >
                <Download size={15} />
                <span>Download Official PDF Dossier</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
