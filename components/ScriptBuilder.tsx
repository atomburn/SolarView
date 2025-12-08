import React, { useState } from 'react';
import { UserCredentials } from '../types';
import { generatePythonScript, generateGithubWorkflow } from '../services/geminiService';
import { Terminal, Cpu, Loader2, CloudUpload, Github, FileJson, FileCode } from 'lucide-react';

interface ScriptBuilderProps {
  initialCreds: UserCredentials;
}

export const ScriptBuilder: React.FC<ScriptBuilderProps> = ({ initialCreds }) => {
  const [creds, setCreds] = useState<UserCredentials>(initialCreds);
  const [script, setScript] = useState<string>('');
  const [workflow, setWorkflow] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'direct' | 'relay'>('relay');
  const [relayType, setRelayType] = useState<'local' | 'github'>('local');

  const handleGenerate = async () => {
    setLoading(true);
    setScript('');
    setWorkflow('');

    const useEnvVars = relayType === 'github';
    const code = await generatePythonScript(creds, mode, useEnvVars);
    setScript(code);

    if (relayType === 'github' && mode === 'relay') {
        const yaml = await generateGithubWorkflow();
        setWorkflow(yaml);
    }

    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border-2 border-black p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          {mode === 'direct' ? <Cpu className="w-5 h-5" /> : <CloudUpload className="w-5 h-5" />}
          {mode === 'direct' ? 'Direct Hardware Deployment' : 'Sensecraft Cloud Relay'}
        </h2>
        
        {/* Mode Toggles */}
        <div className="flex border-2 border-black mb-6">
          <button 
            onClick={() => setMode('relay')}
            className={`flex-1 py-2 text-xs font-bold uppercase transition-colors ${mode === 'relay' ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-100'}`}
          >
            Cloud Relay
          </button>
          <button 
            onClick={() => setMode('direct')}
            className={`flex-1 py-2 text-xs font-bold uppercase transition-colors ${mode === 'direct' ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-100'}`}
          >
            Direct Hardware
          </button>
        </div>

        {mode === 'relay' && (
            <div className="mb-6 bg-gray-50 p-4 border border-gray-200">
                <span className="text-xs font-bold uppercase block mb-2 text-gray-500">Deployment Platform</span>
                <div className="flex gap-4">
                    <button 
                        onClick={() => setRelayType('local')}
                        className={`flex-1 p-3 border-2 text-left flex items-center gap-3 transition-all ${relayType === 'local' ? 'border-black bg-white' : 'border-transparent hover:bg-gray-100'}`}
                    >
                        <div className={`p-2 rounded-full ${relayType === 'local' ? 'bg-black text-white' : 'bg-gray-200'}`}>
                            <Terminal className="w-4 h-4" />
                        </div>
                        <div>
                            <div className="text-xs font-bold uppercase">Local / VPS</div>
                            <div className="text-[10px] text-gray-500">Run on your PC or Pi</div>
                        </div>
                    </button>
                    <button 
                         onClick={() => setRelayType('github')}
                         className={`flex-1 p-3 border-2 text-left flex items-center gap-3 transition-all ${relayType === 'github' ? 'border-black bg-white' : 'border-transparent hover:bg-gray-100'}`}
                    >
                         <div className={`p-2 rounded-full ${relayType === 'github' ? 'bg-black text-white' : 'bg-gray-200'}`}>
                            <Github className="w-4 h-4" />
                        </div>
                        <div>
                            <div className="text-xs font-bold uppercase">GitHub Actions</div>
                            <div className="text-[10px] text-gray-500">Run for free in Cloud</div>
                        </div>
                    </button>
                </div>
            </div>
        )}

        <p className="text-sm text-gray-600 mb-6 font-mono">
          {mode === 'relay' && relayType === 'github' 
             ? "Generates a Python script and a GitHub Workflow YAML. Commit these to a private repo, set your Secrets, and GitHub will run the relay for you automatically."
             : mode === 'relay' 
                ? "Generates a Python script that scrapes EG4 data and pushes it to the Sensecraft API. Designed to run on an always-on computer."
                : "Generates a Python script to run ON the reTerminal itself to fetch data and draw directly to the screen frame buffer."}
        </p>

        {/* Common Credentials */}
        <div className="space-y-4 mb-6">
          <h3 className="text-xs font-bold uppercase border-b border-gray-300 pb-1">EG4 Source</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Inverter User</label>
              <input 
                type="text" 
                value={creds.username}
                onChange={(e) => setCreds({...creds, username: e.target.value})}
                className="w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Inverter Password</label>
              <input 
                type="password" 
                value={creds.password}
                onChange={(e) => setCreds({...creds, password: e.target.value})}
                className="w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black"
              />
            </div>
          </div>
        </div>

        {/* Conditional Inputs */}
        {mode === 'relay' ? (
          <div className="space-y-4 mb-6 animate-refresh">
            <h3 className="text-xs font-bold uppercase border-b border-gray-300 pb-1">Sensecraft Target</h3>
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase mb-1">Sensecraft API Key</label>
                <input 
                  type="text" 
                  placeholder="Paste your API key here..."
                  value={creds.sensecraftApiKey || ''}
                  onChange={(e) => setCreds({...creds, sensecraftApiKey: e.target.value})}
                  className="w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black bg-yellow-50"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase mb-1">Device ID</label>
                <input 
                  type="text" 
                  placeholder="e.g., 20221942"
                  value={creds.sensecraftDeviceId || ''}
                  onChange={(e) => setCreds({...creds, sensecraftDeviceId: e.target.value})}
                  className="w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black bg-yellow-50"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4 mb-6 animate-refresh">
            <h3 className="text-xs font-bold uppercase border-b border-gray-300 pb-1">Hardware Target</h3>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Display S/N</label>
              <input 
                type="text" 
                value={creds.displaySn}
                onChange={(e) => setCreds({...creds, displaySn: e.target.value})}
                className="w-full border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black"
              />
            </div>
          </div>
        )}

        <button 
          onClick={handleGenerate}
          disabled={loading}
          className="w-full bg-black text-white py-3 font-bold hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Terminal className="w-4 h-4" />}
          {loading ? 'GENERATE DEPLOYMENT CODE' : 'GENERATE DEPLOYMENT CODE'}
        </button>
      </div>

      {script && (
        <div className="space-y-6">
            <div className="bg-slate-100 border-2 border-black p-4 relative">
                <div className="absolute top-0 right-0 p-2 z-10">
                    <button 
                        onClick={() => navigator.clipboard.writeText(script)}
                        className="text-xs bg-white border border-black px-2 py-1 hover:bg-black hover:text-white transition-colors"
                    >
                        COPY
                    </button>
                </div>
                <h3 className="text-sm font-bold uppercase mb-2 flex items-center gap-2">
                    <FileCode className="w-4 h-4" />
                    {mode === 'relay' ? 'solar_relay.py' : 'solar_display.py'}
                </h3>
                <pre className="text-xs font-mono overflow-x-auto whitespace-pre-wrap text-slate-800 h-96 overflow-y-scroll border border-gray-300 p-2 bg-white">
                    {script}
                </pre>
            </div>

            {workflow && (
                <div className="bg-slate-100 border-2 border-black p-4 relative">
                    <div className="absolute top-0 right-0 p-2 z-10">
                        <button 
                            onClick={() => navigator.clipboard.writeText(workflow)}
                            className="text-xs bg-white border border-black px-2 py-1 hover:bg-black hover:text-white transition-colors"
                        >
                            COPY
                        </button>
                    </div>
                    <h3 className="text-sm font-bold uppercase mb-2 flex items-center gap-2">
                        <FileJson className="w-4 h-4" />
                        .github/workflows/solar_sync.yml
                    </h3>
                    <pre className="text-xs font-mono overflow-x-auto whitespace-pre-wrap text-slate-800 h-64 overflow-y-scroll border border-gray-300 p-2 bg-white">
                        {workflow}
                    </pre>
                </div>
            )}

          <div className="flex gap-2">
             <div className="flex-1 bg-white border border-black p-3 text-xs">
                <strong>How to Deploy:</strong>
                {mode === 'relay' && relayType === 'github' ? (
                  <ol className="list-decimal list-inside mt-1 space-y-1">
                      <li>Create a new <strong>Private</strong> GitHub Repository.</li>
                      <li>Add the file <code>solar_relay.py</code> to the root.</li>
                      <li>Add the file <code>.github/workflows/solar_sync.yml</code>.</li>
                      <li>Go to Repo Settings &gt; Secrets and Variables &gt; Actions.</li>
                      <li>Add Repository Secrets: <code>EG4_USER</code>, <code>EG4_PASS</code>, <code>SENSECRAFT_KEY</code>.</li>
                      <li>Commit changes. The action will run every 5 minutes automatically.</li>
                  </ol>
                ) : mode === 'relay' ? (
                  <ol className="list-decimal list-inside mt-1 space-y-1">
                      <li>Save as <code>solar_relay.py</code> on a server/Pi.</li>
                      <li>Install: <code>pip3 install requests</code></li>
                      <li>Run: <code>python3 solar_relay.py</code></li>
                  </ol>
                ) : (
                  <ol className="list-decimal list-inside mt-1 space-y-1">
                      <li>SSH into reTerminal.</li>
                      <li>Install: <code>pip3 install requests pillow gpiozero</code></li>
                      <li>Save as <code>solar_display.py</code></li>
                      <li>Run: <code>python3 solar_display.py</code></li>
                  </ol>
                )}
             </div>
          </div>
        </div>
      )}
    </div>
  );
};