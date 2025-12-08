import React, { useState, useEffect, useCallback } from 'react';
import { InverterData, TabView, UserCredentials } from './types';
import { generateSystemInsight } from './services/geminiService';
import { SolarCard } from './components/SolarCard';
import { ScriptBuilder } from './components/ScriptBuilder';
import { Sun, Battery, Home, Zap, RefreshCw, LayoutTemplate, Settings, Power } from 'lucide-react';

const MOCK_CREDENTIALS: UserCredentials = {
  username: 'AdamByrne',
  password: 'Solar123',
  displaySn: '100073581253500339',
  sensecraftDeviceId: '20221942',
  sensecraftApiKey: ''
};

const INITIAL_DATA: InverterData = {
  pvWatts: 4250,
  batteryPercent: 88,
  batteryVoltage: 53.4,
  batteryWatts: 1200, // Charging
  loadWatts: 2850,
  gridWatts: 0,
  gridStatus: 'Connected',
  timestamp: new Date().toLocaleTimeString()
};

const App: React.FC = () => {
  const [data, setData] = useState<InverterData>(INITIAL_DATA);
  const [activeTab, setActiveTab] = useState<TabView>(TabView.DASHBOARD);
  const [insight, setInsight] = useState<string>("Analyzing system data...");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Simulate data fetch
  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    
    // Simulate slight fluctuations for realism
    const newData: InverterData = {
      ...data,
      pvWatts: Math.max(0, data.pvWatts + (Math.random() * 200 - 100)),
      loadWatts: Math.max(500, data.loadWatts + (Math.random() * 100 - 50)),
      batteryPercent: Math.min(100, Math.max(0, data.batteryPercent + (data.batteryWatts > 0 ? 0.1 : -0.1))),
      timestamp: new Date().toLocaleTimeString()
    };
    
    // Recalculate flow
    const surplus = newData.pvWatts - newData.loadWatts;
    newData.batteryWatts = surplus; 
    newData.gridWatts = 0; // Assuming off-grid mode for simplicity or zero export

    setTimeout(async () => {
      setData(newData);
      setLastRefreshed(new Date());
      
      // Get Gemini Insight
      const text = await generateSystemInsight(newData);
      setInsight(text);
      
      setIsRefreshing(false);
    }, 1500); // Artificial delay to show "Scanning" UI
  }, [data]);

  // Initial load
  useEffect(() => {
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-refresh timer (5 minutes as requested, though accelerated for demo)
  useEffect(() => {
    const timer = setInterval(refreshData, 300000); // 5 minutes
    return () => clearInterval(timer);
  }, [refreshData]);

  return (
    <div className={`min-h-screen p-4 md:p-8 max-w-4xl mx-auto ${isRefreshing ? 'animate-refresh' : ''}`}>
      
      {/* Header */}
      <header className="mb-8 border-b-4 border-black pb-4 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-black uppercase tracking-tighter">EG4 Monitor</h1>
          <p className="font-mono text-sm mt-1">
            UNIT: 12000XP <span className="mx-2">|</span> USER: {MOCK_CREDENTIALS.username}
          </p>
        </div>
        <div className="text-right font-mono text-xs">
            <div className="flex items-center justify-end gap-2 mb-1">
                <span className={`w-3 h-3 rounded-full ${data.gridStatus === 'Connected' ? 'bg-black' : 'bg-transparent border border-black'}`}></span>
                GRID {data.gridStatus.toUpperCase()}
            </div>
          <div>UPDATED: {lastRefreshed.toLocaleTimeString()}</div>
          <div>NEXT UPDATE: +5m</div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="flex gap-1 mb-6">
        <button 
          onClick={() => setActiveTab(TabView.DASHBOARD)}
          className={`px-6 py-2 font-bold text-sm uppercase border-2 border-black transition-all ${activeTab === TabView.DASHBOARD ? 'bg-black text-white' : 'bg-white hover:bg-gray-200'}`}
        >
          <div className="flex items-center gap-2">
            <LayoutTemplate className="w-4 h-4" />
            Dashboard
          </div>
        </button>
        <button 
          onClick={() => setActiveTab(TabView.SCRIPT_GEN)}
          className={`px-6 py-2 font-bold text-sm uppercase border-2 border-black transition-all ${activeTab === TabView.SCRIPT_GEN ? 'bg-black text-white' : 'bg-white hover:bg-gray-200'}`}
        >
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Hardware Setup
          </div>
        </button>
      </nav>

      {/* Content Area */}
      <main>
        {activeTab === TabView.DASHBOARD ? (
          <div className="space-y-6">
            
            {/* AI Insight Banner */}
            <div className="bg-white border-2 border-black p-4 flex items-start gap-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <div className="bg-black text-white p-2">
                <Power className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-xs uppercase mb-1">System Insight (Gemini AI)</h3>
                <p className="font-mono text-sm leading-tight">{insight}</p>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SolarCard 
                title="PV Input" 
                value={`${Math.round(data.pvWatts)}W`} 
                icon={<Sun className="w-6 h-6" />} 
              />
              <SolarCard 
                title="Battery" 
                value={`${data.batteryPercent}%`} 
                subValue={`${data.batteryVoltage}V / ${data.batteryWatts > 0 ? '+' : ''}${Math.round(data.batteryWatts)}W`}
                icon={<Battery className="w-6 h-6" />} 
                dark={true}
              />
              <SolarCard 
                title="Load" 
                value={`${Math.round(data.loadWatts)}W`} 
                icon={<Home className="w-6 h-6" />} 
              />
               <SolarCard 
                title="Grid" 
                value={`${Math.round(data.gridWatts)}W`} 
                subValue={data.gridStatus}
                icon={<Zap className="w-6 h-6" />} 
              />
            </div>

            {/* Flow Diagram Representation */}
            <div className="border-2 border-black p-8 bg-white relative h-48 flex items-center justify-center">
                <div className="absolute top-2 left-2 text-xs font-bold uppercase">Energy Flow</div>
                
                {/* Simple SVG Flow */}
                <div className="flex items-center gap-4 md:gap-12 w-full justify-center">
                    <div className="text-center">
                        <Sun className="w-8 h-8 mx-auto mb-2" />
                        <span className="font-mono text-xs">{data.pvWatts}W</span>
                    </div>
                    
                    <div className="h-0.5 bg-black flex-1 relative">
                        <div className="absolute -top-1.5 right-0 w-0 h-0 border-t-[6px] border-t-transparent border-l-[10px] border-l-black border-b-[6px] border-b-transparent"></div>
                    </div>

                    <div className="bg-black text-white p-4 rounded-none border-2 border-black z-10">
                        <div className="font-bold text-lg">EG4</div>
                    </div>

                    <div className="h-0.5 bg-black flex-1 relative">
                         <div className="absolute -top-1.5 right-0 w-0 h-0 border-t-[6px] border-t-transparent border-l-[10px] border-l-black border-b-[6px] border-b-transparent"></div>
                    </div>

                    <div className="text-center">
                        <Home className="w-8 h-8 mx-auto mb-2" />
                        <span className="font-mono text-xs">{data.loadWatts}W</span>
                    </div>
                </div>

                {/* Battery Branch */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center">
                    <div className="w-0.5 h-8 bg-black mb-2"></div>
                    <div className="flex items-center gap-2">
                         <Battery className="w-5 h-5" />
                         <span className="font-mono text-xs">{data.batteryPercent}%</span>
                    </div>
                </div>
            </div>

            <div className="flex justify-center mt-8">
                <button 
                    onClick={refreshData}
                    disabled={isRefreshing}
                    className="flex items-center gap-2 text-sm font-bold uppercase hover:underline disabled:opacity-50"
                >
                    <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Force Refresh
                </button>
            </div>

          </div>
        ) : (
          <ScriptBuilder initialCreds={MOCK_CREDENTIALS} />
        )}
      </main>

      {/* Footer / Display Info */}
      <footer className="mt-12 text-center text-xs text-gray-400 font-mono">
        <p>RETERMINAL E1001 DISPLAY CONFIGURATION PREVIEW</p>
        <p>S/N: {MOCK_CREDENTIALS.displaySn}</p>
      </footer>

    </div>
  );
};

export default App;