import React from 'react';

interface HeaderProps {
  children?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({ children }) => {
  return (
    <header className="h-14 border-b border-border-dark bg-surface-darker flex items-center justify-between px-6 shrink-0 z-20">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded bg-gradient-to-br from-primary to-blue-800 flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-[20px]">radar</span>
          </div>
          <div>
            <h1 className="text-base font-bold tracking-wider leading-none font-display">
              INSIGHT<span className="text-primary">SENTINEL</span>
            </h1>
            <p className="text-[10px] text-text-dim tracking-[0.2em] font-mono uppercase">
              GCR Market Monitor v2.4
            </p>
          </div>
        </div>
        <div className="h-6 w-px bg-border-dark mx-2"></div>
        <div className="flex items-center gap-2 px-2 py-1 bg-primary/10 rounded border border-primary/20">
          <div className="size-2 rounded-full bg-secondary animate-pulse-green"></div>
          <span className="text-xs font-mono text-secondary">SYSTEM ONLINE</span>
        </div>
        {/* Custom status indicator from parent */}
        {children && (
          <>
            <div className="h-6 w-px bg-border-dark mx-2"></div>
            {children}
          </>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden md:flex items-center gap-4 text-xs font-mono text-text-dim">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">memory</span>
            <span>CPU: 34%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">sd_storage</span>
            <span>MEM: 12GB</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">network_check</span>
            <span>LATENCY: 42ms</span>
          </div>
        </div>
        <div className="h-6 w-px bg-border-dark"></div>
        <div className="flex items-center gap-3">
          <button className="text-text-dim hover:text-white transition-colors">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="text-text-dim hover:text-white transition-colors">
            <span className="material-symbols-outlined">settings</span>
          </button>
          <div
            className="size-8 rounded-full bg-surface-dark border border-border-dark overflow-hidden bg-cover bg-center"
            style={{backgroundImage: 'url(https://lh3.googleusercontent.com/aida-public/AB6AXuDwMHy6ymXm63bnObG5oQpJvKrz63hZW5izdr9tsyaUtvlYjBsnqKaXM81MLmj7Q7AwTq_AjofoCod9LljSnYnZ4ICXOEDnNpRgZTtmIAWvCvVPYV0F0ubir--5uAc1I-acVtx8P-G1oLGT-Jisd3u35cuu4kli2LkkyxlQO-xOvYmhWLQlIsQeC5vHcIQlfL8d1loB4y_4zezzyME7EOQGHS_bwQgjTXi32fkbucUJlUHxqqopHtj-MszOIzZNqAujZar4uJgSzCd9)'}}
          ></div>
        </div>
      </div>
    </header>
  );
};
