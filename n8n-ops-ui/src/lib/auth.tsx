import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from './supabase';
import { apiClient } from './api-client';
import type { Entitlements } from '@/types';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'developer' | 'viewer' | 'platform_admin';
  isPlatformAdmin?: boolean;
}

interface Tenant {
  id: string;
  name: string;
  subscriptionPlan: 'free' | 'pro' | 'agency' | 'agency_plus' | 'enterprise';
}

interface ActorUser {
  id: string;
  email: string;
  name?: string | null;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  initComplete: boolean;
  needsOnboarding: boolean;
  user: User | null;
  tenant: Tenant | null;
  entitlements: Entitlements | null;
  session: Session | null;
  impersonating: boolean;
  actorUser: ActorUser | null;
  login: () => void;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  loginWithOAuth: (provider: 'google' | 'github') => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  startImpersonation: (targetUserId: string) => Promise<void>;
  stopImpersonating: () => Promise<void>;
  completeOnboarding: (organizationName?: string) => Promise<void>;
  refreshEntitlements: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

// Keep a single context instance across Vite HMR updates.
// Without this, edits to this file can produce multiple live module copies (different `?t=`),
// causing providers/consumers to reference different contexts and crash at runtime.
const AUTH_CONTEXT_KEY = '__n8n_ops_auth_context__';
const AuthContext: React.Context<AuthContextType | undefined> =
  (globalThis as any)[AUTH_CONTEXT_KEY] ?? createContext<AuthContextType | undefined>(undefined);
if (import.meta.env.DEV) {
  (globalThis as any)[AUTH_CONTEXT_KEY] = AuthContext;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const isTest = import.meta.env.MODE === 'test';
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [impersonating, setImpersonating] = useState(false);
  const [actorUser, setActorUser] = useState<ActorUser | null>(null);
  const [authStatus, setAuthStatus] = useState<'initializing' | 'authenticated' | 'unauthenticated'>('initializing');

  const isLoading = authStatus === 'initializing';
  const initComplete = authStatus !== 'initializing';

  if (!isTest) {
    console.log('[Auth] Current state:', { authStatus, isLoading, initComplete, hasUser: !!user, hasTenant: !!tenant, impersonating });
  }

  // Fetch user data from backend after Supabase authentication
  const fetchUserData = useCallback(async (accessToken: string) => {
    try {
      apiClient.setAuthToken(accessToken);

      const { data: statusData } = await apiClient.getAuthStatus();

      if (statusData.onboarding_required) {
        setNeedsOnboarding(true);
        setUser(null);
        setTenant(null);
        setAuthStatus('authenticated');
        return;
      }

      if (statusData.user && statusData.tenant) {
        setUser({
          id: statusData.user.id,
          email: statusData.user.email,
          name: statusData.user.name,
          role: statusData.user.role || 'viewer',
          isPlatformAdmin: !!(statusData.user as any)?.is_platform_admin,
        });
        setTenant({
          id: statusData.tenant.id,
          name: statusData.tenant.name,
          subscriptionPlan: statusData.tenant.subscription_plan || 'free',
        });
        setNeedsOnboarding(false);

        setImpersonating(!!(statusData as any)?.impersonating);
        setActorUser(((statusData as any)?.actor_user as ActorUser) || null);

        if (statusData.entitlements) {
          setEntitlements(statusData.entitlements);
        }

        setAuthStatus('authenticated');
      } else {
        setAuthStatus('unauthenticated');
      }
    } catch (error) {
      if (!isTest) console.error('[Auth] Failed to fetch user data:', error);
      setAuthStatus('unauthenticated');
    }
  }, [isTest]);

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Get Supabase session
        const { data: { session: currentSession } } = await supabase.auth.getSession();

        if (currentSession) {
          setSession(currentSession);
        }

        if (currentSession) {
          await fetchUserData(currentSession.access_token);
        } else {
          setAuthStatus('unauthenticated');
        }
      } catch (error) {
        if (!isTest) console.error('[Auth] Failed to init auth:', error);
        setAuthStatus('unauthenticated');
      }
    };

    initAuth();

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        if (!isTest) console.log('[Auth] Auth state changed:', event);

        if (event === 'SIGNED_OUT') {
          setSession(null);
          setUser(null);
          setTenant(null);
          setEntitlements(null);
          setImpersonating(false);
          setActorUser(null);
          setAuthStatus('unauthenticated');
          return;
        }

        if (newSession) {
          setSession(newSession);
          // Don't fetch if impersonating
          if (!impersonating) {
            await fetchUserData(newSession.access_token);
          }
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [fetchUserData, isTest, impersonating]);

  const login = useCallback(() => {
    window.location.href = '/login';
  }, []);

  const loginWithEmail = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      throw error;
    }
  }, []);

  const loginWithOAuth = useCallback(async (provider: 'google' | 'github') => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/login`
      }
    });
    if (error) {
      throw error;
    }
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/login`
      }
    });
    if (error) {
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    setImpersonating(false);
    setActorUser(null);
    await supabase.auth.signOut();
  }, []);

  const startImpersonation = useCallback(async (targetUserId: string) => {
    try {
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }
      apiClient.setAuthToken(session.access_token);
      await apiClient.startPlatformImpersonation(targetUserId);
      window.location.reload();
    } catch (error) {
      if (!isTest) console.error('[Auth] Failed to start impersonation:', error);
      throw error;
    }
  }, [session?.access_token, isTest]);

  const stopImpersonating = useCallback(async () => {
    try {
      await apiClient.stopPlatformImpersonation();
    } catch {
      // Ignore error, just clear local state
    }

    setImpersonating(false);
    setActorUser(null);

    // Restore original session
    if (session) {
      apiClient.setAuthToken(session.access_token);
      await fetchUserData(session.access_token);
    }
    window.location.reload();
  }, [session, fetchUserData]);

  const completeOnboarding = useCallback(async (organizationName?: string) => {
    try {
      await apiClient.completeOnboarding({ organization_name: organizationName });
      setNeedsOnboarding(false);

      // Refresh user data
      if (session) {
        await fetchUserData(session.access_token);
      }
    } catch (error) {
      if (!isTest) console.error('[Auth] Failed to complete onboarding:', error);
      throw error;
    }
  }, [session, fetchUserData, isTest]);

  const refreshEntitlements = useCallback(async () => {
    try {
      const { data } = await apiClient.getAuthStatus();
      if (data.entitlements) {
        setEntitlements(data.entitlements);
      }
    } catch (error) {
      if (!isTest) console.error('[Auth] Failed to refresh entitlements:', error);
    }
  }, [isTest]);

  const refreshAuth = useCallback(async () => {
    if (session) {
      await fetchUserData(session.access_token);
    }
  }, [session, fetchUserData]);

  const isAuthenticated = authStatus === 'authenticated';

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        initComplete,
        needsOnboarding,
        user,
        tenant,
        entitlements,
        session,
        impersonating,
        actorUser,
        login,
        loginWithEmail,
        loginWithOAuth,
        signup,
        logout,
        startImpersonation,
        stopImpersonating,
        completeOnboarding,
        refreshEntitlements,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
