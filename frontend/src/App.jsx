import React, { useState } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import RiskAnalysis from './pages/RiskAnalysis';
import RedZones from './pages/RedZones';
import Habitations from './pages/Habitations';
import RelocationSites from './pages/RelocationSites';
import SiteSuitability from './pages/SiteSuitability';
import PriorityPlanning from './pages/PriorityPlanning';
import WhatIfSimulation from './pages/WhatIfSimulation';
import Reports from './pages/Reports';

import HabitationDetailModal from './components/habitation/HabitationDetailModal';
import GlobalSearchModal from './components/common/GlobalSearchModal';

export default function App() {
  // Navigation & View State
  const [activePage, setActivePage] = useState('dashboard');
  const [currentDistrict, setCurrentDistrict] = useState('Guwahati');

  // Modal / Selection State
  const [selectedHabitation, setSelectedHabitation] = useState(null);
  const [selectedSite, setSelectedSite] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Sidebar Layout State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const handleSelectHabitation = (hab) => {
    setSelectedHabitation(hab);
  };

  const handleSelectSite = (site) => {
    setSelectedSite(site);
    setActivePage('site-suitability');
  };

  const handleExportReport = (item) => {
    setActivePage('reports');
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <Navbar
        currentDistrict={currentDistrict}
        onDistrictChange={setCurrentDistrict}
        onOpenSearch={() => setIsSearchOpen(true)}
        onToggleSidebar={() => {
          if (window.innerWidth <= 1024) {
            setIsMobileSidebarOpen(!isMobileSidebarOpen);
          } else {
            setIsSidebarCollapsed(!isSidebarCollapsed);
          }
        }}
        isSidebarOpen={isMobileSidebarOpen}
      />

      {/* Main Body with Sidebar + Active Page */}
      <div className="app-body">
        <Sidebar
          activePage={activePage}
          onNavigate={(pageId) => {
            setActivePage(pageId);
            setIsMobileSidebarOpen(false);
          }}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          isMobileOpen={isMobileSidebarOpen}
        />

        <main className="app-main">
          {activePage === 'dashboard' && (
            <Dashboard
              currentDistrict={currentDistrict}
              onDistrictChange={setCurrentDistrict}
              onSelectHabitation={handleSelectHabitation}
              onSelectSite={handleSelectSite}
              onNavigate={setActivePage}
            />
          )}

          {activePage === 'risk-analysis' && (
            <RiskAnalysis onNavigate={setActivePage} />
          )}

          {activePage === 'red-zones' && (
            <RedZones
              onSelectHabitation={handleSelectHabitation}
              onSelectSite={handleSelectSite}
            />
          )}

          {activePage === 'habitations' && (
            <Habitations onSelectHabitation={handleSelectHabitation} />
          )}

          {activePage === 'relocation-sites' && (
            <RelocationSites onSelectSite={handleSelectSite} />
          )}

          {activePage === 'site-suitability' && (
            <SiteSuitability />
          )}

          {activePage === 'priority-planning' && (
            <PriorityPlanning
              onSelectHabitation={handleSelectHabitation}
              onExportReport={handleExportReport}
            />
          )}

          {activePage === 'what-if' && (
            <WhatIfSimulation onSelectSite={handleSelectSite} />
          )}

          {activePage === 'reports' && (
            <Reports />
          )}
        </main>
      </div>

      {/* Global Modals */}
      <HabitationDetailModal
        habitation={selectedHabitation}
        onClose={() => setSelectedHabitation(null)}
        onInspectSite={handleSelectSite}
        onExportReport={handleExportReport}
      />

      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectHabitation={handleSelectHabitation}
        onSelectSite={handleSelectSite}
      />
    </div>
  );
}
