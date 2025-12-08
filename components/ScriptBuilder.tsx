import React, { useState } from 'react';
import { UserCredentials } from '../types';
import { generatePythonScript, generateGithubWorkflow } from '../services/geminiService';
import { Terminal, Cpu, Loader2, CloudUpload, Github, FileJson, FileCode, ExternalLink, Lock, PlayCircle, CheckCircle, ArrowRight, HelpCircle } from 'lucide-react';

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

        {/* GitHub Specific Input */}
        {mode === 'relay' && relayType === 'github' && (
             <div className="mb-6 animate-refresh">
                <label className="block text-xs font-bold uppercase mb-1">Your GitHub Repo URL</label>
                <div className="flex gap-2">
                    <input 
                    type="text" 
                    placeholder="https://github.com/username/my-solar-repo"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    className="flex-1 border-2 border-black p-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-black bg-white"
                    />
                </div>
                <p className="text-[10px] text-gray-500 mt-1">Paste your URL to enable the smart setup buttons below.</p>
             </div>
        )}

        <p className="text-sm text-gray-600 mb-6 font-mono">
          {mode === 'relay' && relayType === 'github' 
             ? "Automate the data relay using GitHub's free cloud servers. You don't need to leave your computer on."
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
          {loading ? 'GENERATING CODE...' : 'GENERATE DEPLOYMENT CODE'}
        </button>
      </div>

      {script && (
        <div className="space-y-8">
            
            {/* FILE OUTPUTS */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    <pre className="text-[10px] font-mono overflow-x-auto whitespace-pre-wrap text-slate-800 h-64 overflow-y-scroll border border-gray-300 p-2 bg-white">
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
                        <pre className="text-[10px] font-mono overflow-x-auto whitespace-pre-wrap text-slate-800 h-64 overflow-y-scroll border border-gray-300 p-2 bg-white">
                            {workflow}
                        </pre>
                    </div>
                )}
            </div>

            {/* STEP BY STEP GUIDE */}
            {mode === 'relay' && relayType === 'github' && (
                <div className="border-t-4 border-black pt-8">
                     <div className="flex items-center gap-3 mb-6">
                        <HelpCircle className="w-6 h-6" />
                        <h3 className="text-xl font-black uppercase">Installation Manual</h3>
                     </div>

                     <div className="space-y-6">
                        
                        {/* STEP 1 */}
                        <div className="flex gap-4">
                            <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold shrink-0">1</div>
                            <div className="flex-1">
                                <h4 className="font-bold uppercase text-sm mb-1">Check Files</h4>
                                <p className="text-sm text-gray-600 mb-2">Ensure your GitHub repository has exactly these two files:</p>
                                <ul className="text-xs font-mono bg-gray-100 p-2 border border-gray-300 space-y-1">
                                    <li className="flex items-center gap-2"><CheckCircle className="w-3 h-3 text-green-600" /> solar_relay.py <span className="text-gray-400">(The Code)</span></li>
                                    <li className="flex items-center gap-2"><CheckCircle className="w-3 h-3 text-green-600" /> .github/workflows/solar_sync.yml <span className="text-gray-400">(The Timer)</span></li>
                                </ul>
                            </div>
                        </div>

                        {/* STEP 2 */}
                        <div className="flex gap-4">
                             <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold shrink-0">2</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-sm mb-1">Add Safe Credentials</h4>
                                <p className="text-sm text-gray-600 mb-2">GitHub needs your passwords to log in for you, but we don't put them in the code file.</p>
                                
                                {repoUrl ? (
                                    <a href={getSecretLink()} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-black text-white px-4 py-2 text-xs font-bold uppercase hover:bg-gray-800 mb-3">
                                        Open Secrets Page <ExternalLink className="w-3 h-3" />
                                    </a>
                                ) : (
                                    <p className="text-xs bg-yellow-50 p-2 border border-yellow-200 mb-2 text-yellow-800">
                                        Enter your Repo URL at the top to get a direct link here.
                                    </p>
                                )}

                                <p className="text-xs text-gray-500 mb-2">Click <strong>"New repository secret"</strong> for each of these:</p>

                                <div className="grid grid-cols-1 gap-2">
                                    <div className="flex items-center justify-between bg-white border border-gray-300 p-2 text-xs">
                                        <span className="font-mono font-bold">EG4_USER</span>
                                        <span className="text-gray-500 italic">Your EG4 Username</span>
                                    </div>
                                    <div className="flex items-center justify-between bg-white border border-gray-300 p-2 text-xs">
                                        <span className="font-mono font-bold">EG4_PASS</span>
                                        <span className="text-gray-500 italic">Your EG4 Password</span>
                                    </div>
                                    <div className="flex items-center justify-between bg-white border border-gray-300 p-2 text-xs">
                                        <span className="font-mono font-bold">SENSECRAFT_KEY</span>
                                        <span className="text-gray-500 italic">Your Sensecraft API Key</span>
                                    </div>
                                </div>
                             </div>
                        </div>

                         {/* STEP 3 */}
                         <div className="flex gap-4">
                             <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold shrink-0">3</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-sm mb-1">Verify</h4>
                                <p className="text-sm text-gray-600 mb-2">The script is set to run automatically every 5 minutes.</p>
                                {repoUrl && (
                                     <a href={getActionsLink()} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 border-2 border-black text-black px-4 py-2 text-xs font-bold uppercase hover:bg-gray-100">
                                        Check Workflow Status <PlayCircle className="w-3 h-3" />
                                    </a>
                                )}
                                <p className="text-xs text-gray-400 mt-2">If you see a green checkmark, your E-Ink display should update shortly!</p>
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