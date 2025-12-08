import { GoogleGenAI } from "@google/genai";
import { InverterData, UserCredentials } from "../types";

const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const generateSystemInsight = async (data: InverterData): Promise<string> => {
  if (!apiKey) return "API Key missing. Cannot generate insights.";

  try {
    const prompt = `
      You are an expert solar energy assistant. specificially for EG4 inverters.
      Analyze the following telemetry data from an EG4 12000XP inverter and provide a brief, 
      1-sentence status update suitable for an e-ink display (max 20 words).
      
      Data:
      PV Input: ${data.pvWatts}W
      Battery: ${data.batteryPercent}% (${data.batteryVoltage}V) @ ${data.batteryWatts}W
      Home Load: ${data.loadWatts}W
      Grid: ${data.gridWatts}W (${data.gridStatus})
      
      Tone: Technical but concise.
      Example: "System healthy. Charging battery from solar surplus while powering home load."
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
    });

    return response.text || "System Operational.";
  } catch (error) {
    console.error("Gemini insight error:", error);
    return "Status: Operational (AI Offline)";
  }
};

export const generatePythonScript = async (creds: UserCredentials, mode: 'direct' | 'relay', useEnvVars: boolean = false): Promise<string> => {
  if (!apiKey) return "# Error: API Key missing.";

  try {
    let prompt = "";
    
    const envVarNote = useEnvVars 
      ? `IMPORTANT: Do NOT hardcode credentials. Use os.environ.get('EG4_USER'), os.environ.get('EG4_PASSWORD'), os.environ.get('SENSECRAFT_KEY') etc. for all sensitive data. Add a check to print a warning if they are missing.` 
      : `Embed the credentials directly in the variables for simplicity.`;

    if (mode === 'relay') {
      prompt = `
        Create a Python script that acts as a specific data bridge/relay.
        
        GOAL:
        1. Login to the EG4 Electronics Monitoring Portal (https://monitor.eg4electronics.com/WManage/web/login) using requests.Session().
           - Username: ${useEnvVars ? "Load from Env Var 'EG4_USER'" : creds.username}
           - Password: ${useEnvVars ? "Load from Env Var 'EG4_PASS'" : creds.password}
           - Note: Since the exact API endpoints might change, define variables for LOGIN_URL and DATA_URL at the top with best-guess paths (e.g., /WManage/api/login, /WManage/api/device/getData).
           - The script should attempt to fetch the latest Inverter Data (PV Power, Battery SOC, Load Power).
        
        2. Format that data and PUSH it to the Sensecraft API.
           - Endpoint: https://sensecraft-hmi-api.seeed.cc/api/v1/user/device/push_data
           - Method: POST
           - Header 'api-key': ${useEnvVars ? "Load from Env Var 'SENSECRAFT_KEY'" : `'${creds.sensecraftApiKey}'`}
           - Header 'Content-Type': 'application/json'
           - Body Structure:
             {
               "device_id": ${creds.sensecraftDeviceId},
               "data": {
                  "pv_power": <value_from_eg4>,
                  "battery_soc": <value_from_eg4>,
                  "load_power": <value_from_eg4>
               }
             }

        3. EXECUTION:
           - ${useEnvVars ? "Run ONCE (single execution) for use in a Cron job/Action." : "Run in an infinite loop with 60s sleep."}
           - Include robust error handling.
           - ${envVarNote}
        
        Output ONLY the raw python code.
      `;
    } else {
      // Direct Hardware Mode
      prompt = `
        Create a Python script for a Seeed Studio reTerminal (Raspberry Pi CM4 based) equipped with an E-Ink display.
        
        Goal: 
        The script needs to fetch data from an EG4/LuxPower cloud API (simulate the request structure if exact endpoint is unknown, use placeholders) 
        and display it on the e-ink screen.
        
        User Details:
        - Inverter User: ${creds.username}
        - Inverter PW: ${creds.password}
        - ReTerminal SN: ${creds.displaySn}
        
        Requirements:
        1. Use 'requests' library to fetch data.
        2. Use a standard e-paper library compatible with Raspberry Pi (like 'waveshare-epd' or 'pillow' for drawing).
        3. The script should run a loop every 5 minutes.
        4. Draw a simple UI with PV, Battery, and Load values.
        
        Output ONLY the raw python code.
      `;
    }

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
    });

    let text = response.text || "";
    text = text.replace(/```python/g, "").replace(/```/g, "");
    return text.trim();

  } catch (error) {
    console.error("Gemini script generation error:", error);
    return "# Error generating script. Please check API Key and try again.";
  }
};

export const generateGithubWorkflow = async (): Promise<string> => {
  if (!apiKey) return "# Error: API Key missing.";

  try {
    const prompt = `
      Create a GitHub Actions Workflow YAML file (.github/workflows/solar_sync.yml).
      
      Goal: Run a python script named 'solar_relay.py' every 5 minutes.
      
      Requirements:
      - Trigger: schedule cron "*/5 * * * *" AND workflow_dispatch
      - OS: ubuntu-latest
      - Steps:
        1. Checkout repo
        2. Set up Python 3.9
        3. Install dependencies (requests)
        4. Run 'python solar_relay.py'
      - Environment Variables:
        - Map 'EG4_USER' to secrets.EG4_USER
        - Map 'EG4_PASS' to secrets.EG4_PASS
        - Map 'SENSECRAFT_KEY' to secrets.SENSECRAFT_KEY
      
      Output ONLY the raw YAML code.
    `;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
    });

    let text = response.text || "";
    text = text.replace(/```yaml/g, "").replace(/```/g, "");
    return text.trim();

  } catch (error) {
    console.error("Gemini workflow generation error:", error);
    return "# Error generating workflow.";
  }
};