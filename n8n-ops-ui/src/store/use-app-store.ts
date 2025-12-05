import { create } from 'zustand';
import type { EnvironmentType } from '@/types';

interface AppState {
  selectedEnvironment: EnvironmentType;
  setSelectedEnvironment: (env: EnvironmentType) => void;

  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedEnvironment: 'dev',
  setSelectedEnvironment: (env) => set({ selectedEnvironment: env }),

  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  theme: 'light',
  setTheme: (theme) => set({ theme }),
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
}));
