import React, { useState } from 'react';
import { UserCredentials } from '../types';
import { generatePythonScript, generateGithubWorkflow } from '../services/geminiService';
import { Terminal, Cpu, Loader2, CloudUpload, Github, FileJson, FileCode, ExternalLink, Lock, PlayCircle, CheckCircle, ArrowRight, HelpCircle, AlertCircle, PlusSquare, XCircle, Copy, Trash2 } from 'lucide-react';

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

  const getNewFileLink = (filename?: string) => {
    if (!repoUrl) return 'https://github.com';
    const cleanUrl = repoUrl.replace(/\/$/, '');
    const url = `${cleanUrl}/new/main`;
    if (filename) return `${url}?filename=${filename}`;
    return url;
  };

  const getCodeLink = () => {
    if (!repoUrl) return 'https://github.com';
    const cleanUrl = repoUrl.replace(/\/$/, '');
    return `${cleanUrl}`;
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
             <div className="md:col-span-2">
              <label className="block text-sm font-bold uppercase mb-2 text-black">Station / Plant ID (Optional)</label>
              <input 
                type="text" 
                placeholder="Leave blank to auto-detect"
                value={creds.stationId || ''}
                onChange={(e) => setCreds({...creds, stationId: e.target.value})}
                className="w-full border-2 border-black p-3 font-mono text-base focus:outline-none focus:ring-2 focus:ring-black bg-white text-black placeholder-gray-400"
              />
              <p className="text-xs text-gray-500 mt-1">If your script fails with "Missing EG4_STATION_ID", enter your plant ID here.</p>
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
            
            {/* FILE OUTPUTS - VISUAL REFERENCE ONLY */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-50 hover:opacity-100 transition-opacity">
                 {/* Condensed view of files since we use the steps below */}
                 <div className="col-span-2 text-center text-sm text-gray-500 italic">
                    (Files generated below. Please follow the numbered steps.)
                 </div>
            </div>

            {/* STEP BY STEP GUIDE */}
            {mode === 'relay' && relayType === 'github' && (
                <div className="border-t-4 border-black pt-10 text-black">
                     <div className="flex items-center gap-4 mb-8">
                        <HelpCircle className="w-8 h-8 text-black" />
                        <h3 className="text-2xl font-black uppercase text-black">Installation Manual</h3>
                     </div>
                     
                     {/* CRITICAL CLEANUP STEP */}
                     <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-8">
                        <h4 className="font-bold text-red-900 flex items-center gap-2 mb-2">
                             <Trash2 className="w-5 h-5" />
                             STEP 0: REQUIRED CLEANUP
                        </h4>
                        <div className="text-red-800 text-sm space-y-2">
                            <p className="font-bold">You currently have a broken file that is crashing GitHub. You must delete it before continuing.</p>
                            <ol className="list-decimal list-inside bg-white p-3 border border-red-200">
                                <li>Open your <a href={getCodeLink()} target="_blank" className="underline font-bold text-blue-700">GitHub Code Tab</a>.</li>
                                <li>Find the file named <code className="bg-red-100 px-1 font-bold">name: Solar Sync...</code> (it has a very long name).</li>
                                <li>Click that file &rarr; Click the <Trash2 className="inline w-3 h-3 text-gray-500"/> (Trash Can) icon &rarr; Commit changes.</li>
                            </ol>
                        </div>
                     </div>

                     <div className="space-y-12">
                        
                        {/* STEP 1: PYTHON SCRIPT */}
                        <div className="flex gap-6 relative">
                            <div className="absolute -left-3 top-8 bottom-0 w-0.5 bg-gray-200"></div>
                            <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full z-10">1</div>
                            <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Python Script (solar_relay.py)</h4>
                                
                                <div className="bg-blue-50 border border-blue-200 p-4 text-sm mb-4">
                                     <strong className="text-blue-900 block mb-2">UPDATE REQUIRED:</strong>
                                     <p>Because you received a "Missing EG4_STATION_ID" error, you must update this file with the new code below.</p>
                                </div>
                                
                                <div className="bg-slate-100 border-2 border-black p-4 mb-4">
                                    <div className="flex justify-between items-center mb-2 border-b border-gray-300 pb-2">
                                        <div className="font-mono font-bold text-sm">solar_relay.py</div>
                                        <button 
                                            onClick={() => navigator.clipboard.writeText(script)}
                                            className="text-xs flex items-center gap-1 hover:text-blue-600 font-bold uppercase"
                                        >
                                            <Copy className="w-3 h-3" /> Copy Content
                                        </button>
                                    </div>
                                    <pre className="text-xs font-mono h-32 overflow-y-scroll text-gray-600 select-all">{script}</pre>
                                </div>

                                <div className="bg-blue-50 border border-blue-200 p-4 text-sm mb-4">
                                    <div className="font-bold mb-2">Instructions:</div>
                                    <ol className="list-decimal list-inside space-y-2">
                                        <li>Go to <strong>Code</strong> tab &rarr; Click <strong>solar_relay.py</strong>.</li>
                                        <li>Click the <strong>Pencil Icon</strong> (Edit).</li>
                                        <li>Delete everything and paste the <strong>NEW code</strong> from above.</li>
                                        <li>Click <strong>Commit changes</strong>.</li>
                                    </ol>
                                </div>
                            </div>
                        </div>

                        {/* STEP 2: WORKFLOW FILE */}
                        <div className="flex gap-6 relative">
                             <div className="absolute -left-3 top-8 bottom-0 w-0.5 bg-gray-200"></div>
                             <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full z-10">2</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Update the Workflow</h4>

                                <div className="bg-slate-100 border-2 border-black p-4 mb-4">
                                    <div className="flex justify-between items-center mb-2 border-b border-gray-300 pb-2">
                                        <div className="font-mono font-bold text-sm">.github/workflows/solar_sync.yml</div>
                                        <button 
                                            onClick={() => navigator.clipboard.writeText(workflow)}
                                            className="text-xs flex items-center gap-1 hover:text-blue-600 font-bold uppercase"
                                        >
                                            <Copy className="w-3 h-3" /> Copy YAML
                                        </button>
                                    </div>
                                    <pre className="text-xs font-mono h-32 overflow-y-scroll text-gray-600 select-all">{workflow}</pre>
                                </div>
                                
                                <div className="bg-blue-50 border border-blue-200 p-4 text-sm mb-4">
                                    <div className="font-bold mb-2">Instructions:</div>
                                    <ol className="list-decimal list-inside space-y-3">
                                        <li>Go to <strong>Code</strong> tab &rarr; <strong>.github/workflows</strong> &rarr; <strong>solar_sync.yml</strong>.</li>
                                        <li>Click the <strong>Pencil Icon</strong> (Edit).</li>
                                        <li>Replace content with the NEW YAML above (it now includes EG4_STATION_ID).</li>
                                        <li>Click <strong>Commit changes</strong>.</li>
                                    </ol>
                                </div>
                            </div>
                        </div>

                        {/* STEP 3: SECRETS */}
                        <div className="flex gap-6 relative">
                             <div className="absolute -left-3 top-8 bottom-0 w-0.5 bg-gray-200"></div>
                             <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full z-10">3</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Add New Secret</h4>
                                <p className="text-base text-gray-800 mb-4">You need to add the Station ID secret, even if you left it blank (it can be empty if auto-detect works).</p>
                                
                                {repoUrl ? (
                                    <a href={getSecretLink()} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 border-2 border-black text-black px-4 py-2 text-sm font-bold uppercase hover:bg-gray-100 mb-4 shadow-sm">
                                        Open Secrets Page <ExternalLink className="w-4 h-4" />
                                    </a>
                                ) : (
                                    <p className="text-sm bg-yellow-50 p-3 border border-yellow-200 mb-3 text-yellow-900 font-bold">
                                        Enter your Repo URL at the top to get a direct link here.
                                    </p>
                                )}

                                <div className="grid grid-cols-1 gap-2 text-sm font-mono">
                                    <div className="bg-gray-100 p-2 text-gray-500">EG4_USER (Already done)</div>
                                    <div className="bg-gray-100 p-2 text-gray-500">EG4_PASS (Already done)</div>
                                    <div className="bg-green-100 p-2 font-bold border-2 border-green-500">EG4_STATION_ID <span className="text-xs font-normal text-gray-600">(Add this! Use value from input above)</span></div>
                                    <div className="bg-gray-100 p-2 text-gray-500">SENSECRAFT_KEY (Already done)</div>
                                </div>
                             </div>
                        </div>

                         {/* STEP 4: RUN */}
                         <div className="flex gap-6">
                             <div className="w-10 h-10 bg-black text-white flex items-center justify-center font-bold text-xl shrink-0 rounded-full z-10">4</div>
                             <div className="flex-1">
                                <h4 className="font-bold uppercase text-lg mb-2 text-black">Run Manually</h4>
                                <p className="text-base text-gray-800 mb-4">
                                  Go to <strong>Actions</strong> &rarr; <strong>Solar Sync Relay</strong> &rarr; <strong>Run workflow</strong>.
                                </p>
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