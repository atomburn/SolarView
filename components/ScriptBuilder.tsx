import React, { useState } from 'react';
import { UserCredentials } from '../types';
import { generatePythonScript, generateGithubWorkflow } from '../services/geminiService';
import { Terminal, Cpu, Loader2, CloudUpload, Github, FileJson, FileCode, ExternalLink, Lock, PlayCircle, CheckCircle, ArrowRight, HelpCircle, AlertCircle } from 'lucide-react';

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
  const [repoUrl, setRepoUrl] = useState<string>('');

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

  const getSecretLink = () => {
    if (!repoUrl) return 'https://github.com';
    const cleanUrl = repoUrl.replace(/\/$/, '');
    return `${cleanUrl}/settings/secrets/actions`;
  };

  const getActionsLink = () => {
    if (!repoUrl) return 'https://github.com';
    const cleanUrl = repoUrl.replace(/\/$/, '');
    return `${cleanUrl}/actions`;
  };

  return (
    <div className="space-y-8 text-black">
      <div className="bg-white border-2 border-black p-8">
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 text-black">
          {mode === 'direct' ? <Cpu className="w-8 h-8" /> : <CloudUpload className="w-8 h-8" />}
          {mode === 'direct' ? 'Direct Hardware Deployment' : 'Sensecraft Cloud Relay'}
        </h2>
        
        {/* Mode Toggles */}
        <div className="flex border-2 border-black mb-8">
          <button 
            onClick={() => setMode('relay')}
            className={`flex-1 py-4 text-sm font-bold uppercase transition-colors ${mode === 'relay' ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-100'}`}
          >
            Cloud Relay
          </button>
          <button 
            onClick={() => setMode('direct')}
            className={`flex-1 py-4 text-sm font-bold uppercase transition-colors ${mode === 'direct' ? 'bg-black text-white' : 'bg-white text-black hover:bg-gray-100'}`}
          >
            Direct Hardware
          </button>
        </div>

        {mode === 'relay' && (
            <div className="mb-8 bg-gray-50 p-6 border border-gray-200 text-black">
                <span className="text-sm font-bold uppercase block mb-4 text-gray-700">Deployment Platform</span>
                <div className="flex flex-col md:flex-row gap-4">
                    <button 
                        onClick={() => setRelayType('local')}
                        className={`flex-1 p-4 border-2 text-left flex items-center gap-4 transition-all ${relayType === 'local' ? 'border-black bg-white text-black' : 'border-transparent text-black hover:bg-gray-100'}`}
                    >
                        <div className={`p-3 rounded-full ${relayType === 'local' ? 'bg-black text-white' : 'bg-gray-200 text-black'}`}>
                            <Terminal className="w-6 h-6" />
                        </div>
                        <div>
                            <div className="text-sm font-bold uppercase">Local / VPS</div>
                            <div className="text-xs text-gray-600 mt-1">Run on your PC or Pi</div>
                        </div>
                    </button>
                    <button 
                         onClick={() => setRelayType('github')}
                         className={`flex-1 p-4 border-2 text-left flex items-center gap-4 transition-all ${relayType === 'github' ? 'border-black bg-white text-black' : 'border-transparent text-black hover:bg-gray-100'}`}
                    >
                         <div className={`p-3 rounded-full ${relayType === 'github' ? 'bg-black text-white' : 'bg-gray-200 text-black'}`}>
                            <Github className="w-6 h-6" />
                        </div>
                        <div>
                            <div className="text-sm font-bold uppercase">GitHub Actions</div>
                            <div className="text-xs text-gray-600 mt-1">Run for free in Cloud</div>
                        </div>
                    </button>
                </div>
            </div>
        )}

        {/* GitHub Specific Input */}
        {mode === 'relay' && relayType === 'github' && (
             <div className="mb-8 animate-refresh">
                <label className="block text-sm font-bold uppercase mb-2 text-black">Your GitHub Repo URL</label>
                <div className="flex gap-2">
                    <input 
                    type="text" 
                    placeholder="https://github.com/username/my-solar-repo"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    className="flex-1 border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-white text-black placeholder-gray-400"
                    />
                </div>
                <p className="text-sm text-gray-600 mt-2">Paste your URL to enable the smart setup buttons below.</p>
             </div>
        )}

        <p className="text-base text-gray-800 mb-8 font-mono leading-relaxed">
          {mode === 'relay' && relayType === 'github' 
             ? "Automate the data relay using GitHub's free cloud servers. You don't need to leave your computer on."
             : mode === 'relay' 
                ? "Generates a Python script that scrapes EG4 data and pushes it to the Sensecraft API. Designed to run on an always-on computer."
                : "Generates a Python script to run ON the reTerminal itself to fetch data and draw directly to the screen frame buffer."}
        </p>

        {/* Common Credentials */}
        <div className="space-y-6 mb-8">
          <h3 className="text-sm font-bold uppercase border-b-2 border-gray-200 pb-2 text-black">EG4 Source</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold uppercase mb-2 text-black">Inverter User</label>
              <input 
                type="text" 
                value={creds.username}
                onChange={(e) => setCreds({...creds, username: e.target.value})}
                className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-white text-black"
              />
            </div>
            <div>
              <label className="block text-sm font-bold uppercase mb-2 text-black">Inverter Password</label>
              <input 
                type="password" 
                value={creds.password}
                onChange={(e) => setCreds({...creds, password: e.target.value})}
                className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-white text-black"
              />
            </div>
          </div>
        </div>

        {/* Conditional Inputs */}
        {mode === 'relay' ? (
          <div className="space-y-6 mb-8 animate-refresh">
            <h3 className="text-sm font-bold uppercase border-b-2 border-gray-200 pb-2 text-black">Sensecraft Target</h3>
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-sm font-bold uppercase mb-2 text-black">Sensecraft API Key</label>
                <input 
                  type="text" 
                  placeholder="Paste your API key here..."
                  value={creds.sensecraftApiKey || ''}
                  onChange={(e) => setCreds({...creds, sensecraftApiKey: e.target.value})}
                  className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-yellow-50 text-black placeholder-gray-400"
                />
              </div>
              <div>
                <label className="block text-sm font-bold uppercase mb-2 text-black">Device ID</label>
                <input 
                  type="text" 
                  placeholder="e.g., 20221942"
                  value={creds.sensecraftDeviceId || ''}
                  onChange={(e) => setCreds({...creds, sensecraftDeviceId: e.target.value})}
                  className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-yellow-50 text-black placeholder-gray-400"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6 mb-8 animate-refresh">
            <h3 className="text-sm font-bold uppercase border-b-2 border-gray-200 pb-2 text-black">Hardware Target</h3>
            <div>
              <label className="block text-sm font-bold uppercase mb-2 text-black">Display S/N</label>
              <input 
                type="text" 
                value={creds.displaySn}
                onChange={(e) => setCreds({...creds, displaySn: e.target.value})}
                className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-white text-black"
              />
            </div>
          </div>
        )}

        <button 
          onClick={handleGenerate}
          disabled={loading}
          className="w-full bg-black text-white py-4 text-lg font-bold hover:bg-gray-800 transition-colors flex items-center justify-center gap-3 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Terminal className="w-6 h-6" />}
          {loading ? 'GENERATING CODE...' : 'GENERATE DEPLOYMENT CODE'}
        </button>
      </div>

      {script && (
        <div className="space-y-8">
            
            {/* FILE OUTPUTS */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-100 border-2 border-black p-4 relative shadow-lg text-black">
                    <div className="absolute top-0 right-0 p-2 z-10">
                        <button 
                            onClick={() => navigator.clipboard.writeText(script)}
                            className="text-xs bg-white text-black border border-black px-3 py-1 hover:bg-black hover:text-white transition-colors font-bold uppercase"
                        >
                            Copy
                        </button>
                    </div>
                    <h3 className="text-base font-bold uppercase mb-4 flex items-center gap-2 border-b border-gray-300 pb-2 text-black">
                        <FileCode className="w-5 h-5" />
                        {mode === 'relay' ? 'solar_relay.py' : 'solar_display.py'}
                    </h3>
                    <pre className="text-sm font-mono overflow-x-auto whitespace-pre-wrap text-slate-900 h-80 overflow-y-scroll border border-gray-300 p-4 bg-white">
                        {script}
                    </pre>
                </div>

                {workflow && (
                    <div className="bg-slate-100 border-2 border-black p-4 relative shadow-lg text-black">
                        <div className="absolute top-0 right-0 p-2 z-10">
                            <button 
                                onClick={() => navigator.clipboard.writeText(workflow)}
                                className="text-xs bg-white text-black border border-black px-3 py-1 hover:bg-black hover:text-white transition-colors font-bold uppercase"
                            >
                                Copy
                            </button>
                        </div>
                        <h3 className="text-base font-bold uppercase mb-4 flex items-center gap-2 border-b border-gray-300 pb-2 text-black">
                            <FileJson className="w-5 h-5" />
                            .github/workflows/solar_sync.yml
                        </h3>
                        <pre className="text-sm font-mono overflow-x-auto whitespace-pre-wrap text-slate-900 h-80 overflow-y-scroll border border-gray-300 p-4 bg-white">
                            {workflow}
                        </pre>
                    </div>
                )}
            </div>

            {/* STEP BY STEP GUIDE */}
            {mode === 'relay' && relayType === 'github' && (
                <div className="border-t-4 border-black pt-10 text-black">
                     <div className="flex items-center gap-4 mb-8">
                        <HelpCircle className="w-8 h-8 text-black" />
                        <h3 className="text-2xl font-black uppercase text-black">Installation Manual</h3>
                     </div>

                     <div className="space-y-8">
                        
                        {/* STEP 1 */}
                        <div className="flex gap-6">
                            <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full">1</div>
                            <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Check Folder Path</h4>
                                <p className="text-base text-gray-800 mb-3">
                                  You do <strong>NOT</strong> need to create a new Action manually. The file you just copied does it for you, BUT it must be in the exact right folder:
                                </p>
                                <ul className="text-sm font-mono bg-yellow-50 p-4 border border-yellow-200 space-y-2 text-black">
                                    <li className="flex items-center gap-3">
                                      <div className="w-5 h-5 flex items-center justify-center bg-green-600 rounded-full text-white"><CheckCircle className="w-3 h-3" /></div>
                                      repo/.github/workflows/solar_sync.yml
                                    </li>
                                    <li className="flex items-center gap-3 opacity-50">
                                      <div className="w-5 h-5 flex items-center justify-center bg-red-600 rounded-full text-white">X</div>
                                      repo/solar_sync.yml
                                    </li>
                                </ul>
                            </div>
                        </div>

                        {/* STEP 2 */}
                        <div className="flex gap-6">
                             <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full">2</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Add Safe Credentials</h4>
                                <p className="text-base text-gray-800 mb-4">Go to <strong>Settings &rarr; Secrets and variables &rarr; Actions</strong> and add these:</p>
                                
                                {repoUrl ? (
                                    <a href={getSecretLink()} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-black text-white px-6 py-3 text-sm font-bold uppercase hover:bg-gray-800 mb-4 shadow-md">
                                        Open Secrets Page <ExternalLink className="w-4 h-4" />
                                    </a>
                                ) : (
                                    <p className="text-sm bg-yellow-50 p-3 border border-yellow-200 mb-3 text-yellow-900 font-bold">
                                        Enter your Repo URL at the top to get a direct link here.
                                    </p>
                                )}

                                <div className="grid grid-cols-1 gap-3">
                                    <div className="flex items-center justify-between bg-white border-2 border-gray-200 p-3 text-sm">
                                        <span className="font-mono font-bold text-lg text-black">EG4_USER</span>
                                    </div>
                                    <div className="flex items-center justify-between bg-white border-2 border-gray-200 p-3 text-sm">
                                        <span className="font-mono font-bold text-lg text-black">EG4_PASS</span>
                                    </div>
                                    <div className="flex items-center justify-between bg-white border-2 border-gray-200 p-3 text-sm">
                                        <span className="font-mono font-bold text-lg text-black">SENSECRAFT_KEY</span>
                                    </div>
                                </div>
                             </div>
                        </div>

                         {/* STEP 3 */}
                         <div className="flex gap-6">
                             <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full">3</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Verify & Run</h4>
                                <p className="text-base text-gray-800 mb-4">
                                  Go to the <strong>Actions</strong> tab. You don't have to wait 5 minutes!
                                </p>
                                
                                <div className="bg-slate-100 p-4 border border-gray-300 mb-4">
                                  <h5 className="font-bold text-xs uppercase mb-2 text-gray-500">How to run manually:</h5>
                                  <ol className="list-decimal list-inside text-sm space-y-1 font-mono">
                                    <li>Click "Deploy Web Dashboard" (or "Solar Sync") in left sidebar</li>
                                    <li>Click the "Run workflow" dropdown button on the right</li>
                                    <li>Click the green "Run workflow" button</li>
                                  </ol>
                                </div>

                                <div className="mt-4">
                                  <p className="text-sm font-bold mb-2">Look for this Green Checkmark:</p>
                                  <div className="border border-gray-200 bg-white p-3 flex items-center gap-3 shadow-sm max-w-sm">
                                     <CheckCircle className="w-5 h-5 text-green-600" />
                                     <div className="flex flex-col">
                                       <span className="font-bold text-sm">Solar Sync</span>
                                       <span className="text-xs text-gray-500">Success</span>
                                     </div>
                                  </div>
                                </div>

                                {repoUrl && (
                                     <a href={getActionsLink()} target="_blank" rel="noopener noreferrer" className="mt-6 inline-flex items-center gap-2 border-2 border-black text-black px-6 py-3 text-sm font-bold uppercase hover:bg-gray-100 shadow-sm">
                                        Go to Actions Tab <ArrowRight className="w-4 h-4" />
                                    </a>
                                )}
                             </div>
                        </div>

                     </div>
                </div>
            )}
        </div>
      )}
    </div>
  );
};