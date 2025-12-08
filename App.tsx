import React, { useState, useEffect, useCallback } from 'react';
import { InverterData, TabView, UserCredentials } from './types';
import { generateSystemInsight } from './services/geminiService';
import { SolarCard } from './components/SolarCard';
import { ScriptBuilder } from './components/ScriptBuilder';
import { Sun, Battery, Home, Zap, RefreshCw, LayoutTemplate, Settings, Power, WifiOff, Info } from 'lucide-react';

const MOCK_CREDENTIALS: UserCredentials = {
  username: 'AdamByrne',
  password: 'Solar123',
  displaySn: '100073581253500339',
  sensecraftDeviceId: '20221942',
  sensecraftApiKey: ''
};

const INITIAL_DATA: InverterData = {
  pvWatts: 8250, // More realistic peak for a 12000XP
  batteryPercent: 92,
  batteryVoltage: 54.2,
  batteryWatts: 3500, // Charging
  loadWatts: 4750,
  gridWatts: 0,
  gridStatus: 'Connected',
  timestamp: new Date().toLocaleTimeString()
};

const App: React.FC = () => {
  const [data, setData] = useState<InverterData>(INITIAL_DATA);
  const [activeTab, setActiveTab] = useState<TabView>(TabView.DASHBOARD);
  const [insight, setInsight] = useState<string>("Initializing system connection...");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [simulationMode, setSimulationMode] = useState(true);

  // Simulate data fetch
  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    
    // Simulate slight fluctuations for realism
    const newData: InverterData = {
      ...data,
      pvWatts: Math.max(0, data.pvWatts + (Math.random() * 400 - 200)),
      loadWatts: Math.max(500, data.loadWatts + (Math.random() * 200 - 100)),
      batteryPercent: Math.min(100, Math.max(0, data.batteryPercent + (data.batteryWatts > 0 ? 0.2 : -0.1))),
      timestamp: new Date().toLocaleTimeString()
    };
    
    // Recalculate flow logic for 12000XP
    // PV - Load = Surplus (Battery Charge)
    const surplus = newData.pvWatts - newData.loadWatts;
    newData.batteryWatts = surplus; 
    newData.gridWatts = 0; // Assuming off-grid mode mostly

    setTimeout(async () => {
      setData(newData);
      setLastRefreshed(new Date());
      
      // Get Gemini Insight
      const text = await generateSystemInsight(newData);
      setInsight(text);
      
      setIsRefreshing(false);
    }, 1200); 
  }, [data]);

  // Initial load
  useEffect(() => {
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-refresh timer
  useEffect(() => {
    const timer = setInterval(refreshData, 300000); // 5 minutes
    return () => clearInterval(timer);
  }, [refreshData]);

  return (
    <div className={`min-h-screen p-4 md:p-8 max-w-5xl mx-auto text-black ${isRefreshing ? 'animate-refresh' : ''}`}>
      
      {/* Header */}
      <header className="mb-8 border-b-4 border-black pb-4 flex flex-col md:flex-row justify-between items-start md:items-end gap-4 text-black">
        <div>
          <h1 className="text-5xl font-black uppercase tracking-tighter text-black">EG4 Monitor</h1>
          <div className="flex flex-col md:flex-row md:items-center gap-2 mt-2">
            <p className="font-mono text-base font-bold text-black">
                UNIT: 12000XP <span className="mx-2 hidden md:inline">|</span> USER: {MOCK_CREDENTIALS.username}
            </p>
            {simulationMode && (
                <div className="inline-flex items-center gap-1 bg-yellow-100 border border-yellow-500 text-yellow-800 px-2 py-0.5 text-xs font-bold uppercase rounded">
                    <WifiOff className="w-3 h-3" />
                    Simulation Mode
                </div>
            )}
          </div>
        </div>
        <div className="text-right font-mono text-sm text-black">
            <div className="flex items-center justify-end gap-2 mb-1 font-bold">
                <span className={`w-3 h-3 rounded-full ${data.gridStatus === 'Connected' ? 'bg-black' : 'bg-transparent border border-black'}`}></span>
                GRID {data.gridStatus.toUpperCase()}
            </div>
          <div>UPDATED: {lastRefreshed.toLocaleTimeString()}</div>
          <div>NEXT UPDATE: +5m</div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="flex gap-2 mb-8">
        <button 
          onClick={() => setActiveTab(TabView.DASHBOARD)}
          className={`px-8 py-3 font-bold text-base uppercase border-2 border-black transition-all ${activeTab === TabView.DASHBOARD ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-200'}`}
        >
          <div className="flex items-center gap-2">
            <LayoutTemplate className="w-5 h-5" />
            Dashboard
          </div>
        </button>
        <button 
          onClick={() => setActiveTab(TabView.SCRIPT_GEN)}
          className={`px-8 py-3 font-bold text-base uppercase border-2 border-black transition-all ${activeTab === TabView.SCRIPT_GEN ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-200'}`}
        >
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Hardware Setup
          </div>
        </button>
      </nav>

      {/* Content Area */}
      <main>
        {activeTab === TabView.DASHBOARD ? (
          <div className="space-y-8">
            
            {/* Simulation Warning */}
            {simulationMode && (
                <div className="bg-slate-100 border-l-4 border-black p-4 text-sm flex gap-3 items-start">
                     <Info className="w-5 h-5 flex-shrink-0" />
                     <div>
                        <p className="font-bold mb-1">Why is this data simulated?</p>
                        <p className="text-gray-700">
                            Web browsers cannot securely connect directly to the EG4 inverter login page due to security restrictions (CORS). 
                            To view your <strong>actual real-time data</strong>, go to the <strong>Hardware Setup</strong> tab and set up the Cloud Relay script. 
                            This dashboard is currently showing a preview of what the interface will look like.
                        </p>
                     </div>
                </div>
            )}
            
            {/* AI Insight Banner */}
            <div className="bg-white border-2 border-black p-6 flex items-start gap-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] text-black">
              <div className="bg-black text-white p-3">
                <Power className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-bold text-sm uppercase mb-2 text-black">System Insight (Gemini AI)</h3>
                <p className="font-mono text-lg leading-tight text-black">{insight}</p>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
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
            <div className="border-2 border-black p-8 bg-white relative h-64 flex items-center justify-center text-black">
                <div className="absolute top-4 left-4 text-sm font-bold uppercase text-black">Energy Flow</div>
                
                {/* Simple SVG Flow */}
                <div className="flex items-center gap-4 md:gap-16 w-full justify-center text-black">
                    <div className="text-center">
                        <Sun className="w-12 h-12 mx-auto mb-3" />
                        <span className="font-mono text-sm font-bold">{data.pvWatts}W</span>
                    </div>
                    
                    <div className="h-1 bg-black flex-1 relative">
                        <div className="absolute -top-2 right-0 w-0 h-0 border-t-[8px] border-t-transparent border-l-[12px] border-l-black border-b-[8px] border-b-transparent"></div>
                    </div>

                    <div className="bg-black text-white p-6 rounded-none border-4 border-black z-10">
                        <div className="font-bold text-2xl">EG4</div>
                    </div>

                    <div className="h-1 bg-black flex-1 relative">
                         <div className="absolute -top-2 right-0 w-0 h-0 border-t-[8px] border-t-transparent border-l-[12px] border-l-black border-b-[8px] border-b-transparent"></div>
                    </div>

                    <div className="text-center">
                        <Home className="w-12 h-12 mx-auto mb-3" />
                        <span className="font-mono text-sm font-bold">{data.loadWatts}W</span>
                    </div>
                </div>

                {/* Battery Branch */}
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center text-black">
                    <div className="w-1 h-12 bg-black mb-3"></div>
                    <div className="flex items-center gap-3">
                         <Battery className="w-8 h-8" />
                         <span className="font-mono text-sm font-bold">{data.batteryPercent}%</span>
                    </div>
                </div>
            </div>

            <div className="flex justify-center mt-8">
                <button 
                    onClick={refreshData}
                    disabled={isRefreshing}
                    className="flex items-center gap-3 text-base font-bold uppercase hover:underline disabled:opacity-50 text-black"
                >
                    <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Force Refresh
                </button>
            </div>

          </div>
        ) : (
          <ScriptBuilder initialCreds={MOCK_CREDENTIALS} />
        )}
      </main>

      {/* Footer / Display Info */}
      <footer className="mt-16 text-center text-sm text-gray-500 font-mono pb-8">
        <p>RETERMINAL E1001 DISPLAY CONFIGURATION PREVIEW</p>
        <p>S/N: {MOCK_CREDENTIALS.displaySn}</p>
      </footer>

    </div>
  );
};

export default App;