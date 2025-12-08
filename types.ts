export interface InverterData {
  pvWatts: number;
  batteryPercent: number;
  batteryVoltage: number;
  batteryWatts: number; // Positive = Charging, Negative = Discharging
  loadWatts: number;
  gridWatts: number; // Positive = Buying, Negative = Selling
  gridStatus: 'Connected' | 'Disconnected' | 'Error';
  timestamp: string;
}

export interface UserCredentials {
  username: string;
  password?: string;
  stationId?: string;
  inverterSn?: string;
  displaySn?: string;
  sensecraftApiKey?: string;
  sensecraftDeviceId?: string;
}

export enum TabView {
  DASHBOARD = 'DASHBOARD',
  SCRIPT_GEN = 'SCRIPT_GEN',
}