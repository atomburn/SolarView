import React from 'react';

interface SolarCardProps {
  title: string;
  value: string;
  subValue?: string;
  icon: React.ReactNode;
  dark?: boolean;
}

export const SolarCard: React.FC<SolarCardProps> = ({ title, value, subValue, icon, dark = false }) => {
  return (
    <div className={`p-4 border-2 border-black flex flex-col justify-between h-32 ${dark ? 'bg-black text-white' : 'bg-white text-black'}`}>
      <div className="flex justify-between items-start">
        <span className="font-bold uppercase text-xs tracking-wider">{title}</span>
        <div className="opacity-80">{icon}</div>
      </div>
      <div className="mt-2">
        <div className="text-3xl font-mono font-bold">{value}</div>
        {subValue && <div className="text-xs font-mono mt-1 opacity-70">{subValue}</div>}
      </div>
    </div>
  );
};