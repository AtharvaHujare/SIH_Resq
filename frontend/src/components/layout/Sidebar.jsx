import React from 'react';
import {
  LayoutDashboard,
  BarChart3,
  ShieldAlert,
  Home,
  MapPin,
  Sliders,
  ListOrdered,
  FlaskConical,
  FileText,
  ChevronLeft,
  ChevronRight,
  Activity
} from 'lucide-react';

export default function Sidebar({
  activePage,
  onNavigate,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen
}) {
  const navItems = [
    { id: 'dashboard', label: 'Command Dashboard', icon: LayoutDashboard, category: 'Overview' },
    { id: 'risk-analysis', label: 'Risk Analysis', icon: BarChart3, category: 'Hazard Modeling' },
    { id: 'red-zones', label: 'Red Zones Explorer', icon: ShieldAlert, category: 'Hazard Modeling' },
    { id: 'habitations', label: 'Vulnerable Habitations', icon: Home, category: 'Settlement Analysis' },
    { id: 'relocation-sites', label: 'Relocation Sites', icon: MapPin, category: 'Relocation Planning' },
    { id: 'site-suitability', label: 'Suitability & Capacity', icon: Sliders, category: 'Relocation Planning' },
    { id: 'priority-planning', label: 'Priority Action Queue', icon: ListOrdered, category: 'Decision Support' },
    { id: 'what-if', label: 'What-If Simulation', icon: FlaskConical, category: 'Decision Support' },
    { id: 'reports', label: 'Reports & Action Dossiers', icon: FileText, category: 'Governance' }
  ];

  // Group by category
  const categories = ['Overview', 'Hazard Modeling', 'Settlement Analysis', 'Relocation Planning', 'Decision Support', 'Governance'];

  return (
    <aside className={`app-sidebar ${isCollapsed ? 'collapsed' : ''} ${isMobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-menu">
        {categories.map((cat) => {
          const itemsInCat = navItems.filter((item) => item.category === cat);
          if (itemsInCat.length === 0) return null;

          return (
            <div key={cat} style={{ marginBottom: '8px' }}>
              {!isCollapsed && <div className="sidebar-category">{cat}</div>}
              {itemsInCat.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;

                return (
                  <button
                    key={item.id}
                    className={`sidebar-item-btn ${isActive ? 'active' : ''}`}
                    onClick={() => onNavigate(item.id)}
                    title={item.label}
                  >
                    <Icon className="sidebar-icon" size={19} />
                    {!isCollapsed && <span className="sidebar-label">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Sidebar Footer with Engine Status & Collapse Toggle */}
      <div className="sidebar-footer">
        {!isCollapsed && (
          <div className="engine-status-card">
            <div className="status-pulse-dot" />
            <div className="engine-status-text">
              <span className="status-title">RESQ Engine Online</span>
              <span className="status-desc">PostGIS + deterministic rules</span>
            </div>
          </div>
        )}

        <button
          className="collapse-sidebar-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight size={18} /> : (
            <>
              <ChevronLeft size={18} />
              <span>Collapse Menu</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
