import { ChatSession, Message, UserProfile, Agent, DEFAULT_AGENTS, Brand, Model } from '../types';
import { supabase } from './supabase';
import { ragHeaders, ragUrl } from './ragApi';

// Storage service for local data management
const CHATS_KEY = 'elevex_chats';
const CURRENT_USER_KEY = 'elevex_current_user';
const ADMIN_USERS_KEY = 'elevex_admin_users';
const BRANDS_KEY = 'elevex_brands';
const MODELS_KEY = 'elevex_models';
const SESSION_DB_ID_MAP_KEY = 'elevex_session_db_id_map';
const QUERY_USAGE_KEY = 'elevex_query_usage';
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const CHATS_SYNC_MIN_INTERVAL_MS = 5000;
const AGENTS_SYNC_MIN_INTERVAL_MS = 15000;
const QUERY_WINDOW_MS = 24 * 60 * 60 * 1000;

type FinancialMetricsPeriod = '7d' | '30d' | '90d' | '1y';

let chatsSyncPromise: Promise<ChatSession[]> | null = null;
let lastChatsSyncAt = 0;
let agentsSyncPromise: Promise<Agent[]> | null = null;
let lastAgentsSyncAt = 0;

type QueryUsageRow = {
    windowStart: number;
    used: number;
};

type QueryUsageMap = Record<string, QueryUsageRow>;

type PlanQuotaPolicy = {
    limitPer24h: number | 'Infinity';
    devices: number;
};

const PLAN_QUOTA_POLICIES: Record<UserProfile['plan'], PlanQuotaPolicy> = {
    Free: { limitPer24h: 1, devices: 1 },
    Iniciante: { limitPer24h: 5, devices: 1 },
    Profissional: { limitPer24h: 'Infinity', devices: 1 },
    Empresa: { limitPer24h: 'Infinity', devices: 5 },
};

const PLAN_MONTHLY_PRICE: Record<UserProfile['plan'], number> = {
    Free: 0,
    Iniciante: 9.99,
    Profissional: 19.99,
    Empresa: 99.99,
};

type SupabaseChatSessionRow = {
    id: string;
    user_id: string;
    agent_id: string;
    title: string | null;
    last_message_at: string | null;
    preview: string | null;
    is_archived: boolean | null;
};

type SupabaseMessageRow = {
    id: string;
    session_id: string;
    role: 'user' | 'model' | null;
    text: string | null;
    timestamp?: string | null;
    created_at?: string | null;
};

const isUuid = (value?: string | null) => UUID_REGEX.test(String(value || ''));

const getSessionDbIdMap = (): Record<string, string> => {
    try {
        const raw = localStorage.getItem(SESSION_DB_ID_MAP_KEY);
        const parsed = raw ? JSON.parse(raw) : {};
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
        return {};
    }
};

const saveSessionDbIdMap = (map: Record<string, string>) => {
    localStorage.setItem(SESSION_DB_ID_MAP_KEY, JSON.stringify(map));
};

const resolveDatabaseSessionId = (sessionId: string): string => {
    if (isUuid(sessionId)) return sessionId;

    const map = getSessionDbIdMap();
    const existing = map[sessionId];
    if (existing && isUuid(existing)) return existing;

    const generated = generateUuid();
    map[sessionId] = generated;
    saveSessionDbIdMap(map);
    return generated;
};

const generateUuid = (): string => {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const random = Math.random() * 16 | 0;
        const value = c === 'x' ? random : (random & 0x3 | 0x8);
        return value.toString(16);
    });
};

const getQueryUsageMap = (): QueryUsageMap => {
    try {
        const raw = localStorage.getItem(QUERY_USAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : {};
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
        return {};
    }
};

const saveQueryUsageMap = (usageMap: QueryUsageMap) => {
    localStorage.setItem(QUERY_USAGE_KEY, JSON.stringify(usageMap));
};

const getPlanPolicy = (plan: UserProfile['plan']): PlanQuotaPolicy => {
    return PLAN_QUOTA_POLICIES[plan] || PLAN_QUOTA_POLICIES.Free;
};

const normalizeProfileQuotaFields = (profile: UserProfile): UserProfile => {
    const policy = getPlanPolicy(profile.plan);
    const usageState = getUserQueryQuotaStatus(profile);
    return {
        ...profile,
        creditsLimit: policy.limitPer24h,
        creditsUsed: usageState.used,
    };
};

const ensureAdminUsersSeeded = (): UserProfile[] => {
    const defaults = [ADMIN_PROFILE, USER_PROFILE].map(normalizeProfileQuotaFields);
    try {
        const raw = localStorage.getItem(ADMIN_USERS_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        const existing = Array.isArray(parsed)
            ? parsed.filter((item): item is UserProfile => !!item && typeof item === 'object')
            : [];

        const byId = new Map<string, UserProfile>();
        for (const user of existing) {
            const normalized = normalizeProfileQuotaFields(user);
            byId.set(normalized.id, normalized);
        }
        for (const user of defaults) {
            if (!byId.has(user.id)) {
                byId.set(user.id, user);
            }
        }

        const merged = Array.from(byId.values());
        localStorage.setItem(ADMIN_USERS_KEY, JSON.stringify(merged));
        return merged;
    } catch {
        localStorage.setItem(ADMIN_USERS_KEY, JSON.stringify(defaults));
        return defaults;
    }
};

const upsertAdminUser = (profile: UserProfile): UserProfile[] => {
    const users = ensureAdminUsersSeeded();
    const index = users.findIndex(user => user.id === profile.id || user.email === profile.email);
    const normalized = normalizeProfileQuotaFields(profile);
    if (index >= 0) {
        users[index] = normalized;
    } else {
        users.push(normalized);
    }
    localStorage.setItem(ADMIN_USERS_KEY, JSON.stringify(users));
    return users;
};

const getPeriodRange = (period: FinancialMetricsPeriod) => {
    const now = Date.now();
    const days = period === '7d' ? 7 : period === '90d' ? 90 : period === '1y' ? 365 : 30;
    const currentStart = now - (days * 24 * 60 * 60 * 1000);
    const previousStart = currentStart - (days * 24 * 60 * 60 * 1000);
    return { now, currentStart, previousStart };
};

const formatReais = (value: number): string => {
    return new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(Number.isFinite(value) ? value : 0);
};

export type UserQueryQuotaStatus = {
    plan: UserProfile['plan'];
    limit: number | 'Infinity';
    used: number;
    remaining: number | 'Infinity';
    isBlocked: boolean;
    resetAt: number;
    msUntilReset: number;
    devicesLimit: number;
};

export const getUserQueryQuotaStatus = (profile?: UserProfile | null): UserQueryQuotaStatus => {
    const user = profile || getUserProfile();
    if (!user) {
        const now = Date.now();
        return {
            plan: 'Free',
            limit: 1,
            used: 0,
            remaining: 1,
            isBlocked: false,
            resetAt: now + QUERY_WINDOW_MS,
            msUntilReset: QUERY_WINDOW_MS,
            devicesLimit: 1,
        };
    }

    const now = Date.now();
    const policy = getPlanPolicy(user.plan);
    const usageMap = getQueryUsageMap();
    const current = usageMap[user.id];

    const windowStart = current?.windowStart || now;
    const shouldReset = now - windowStart >= QUERY_WINDOW_MS;
    const normalizedStart = shouldReset ? now : windowStart;
    const used = shouldReset ? 0 : Math.max(0, Number(current?.used || 0));

    if (shouldReset && current) {
        usageMap[user.id] = { windowStart: normalizedStart, used: 0 };
        saveQueryUsageMap(usageMap);
    }

    const limit = policy.limitPer24h;
    const remaining = limit === 'Infinity' ? 'Infinity' : Math.max(0, Number(limit) - used);
    const resetAt = normalizedStart + QUERY_WINDOW_MS;
    const msUntilReset = Math.max(0, resetAt - now);
    const isBlocked = limit === 'Infinity' ? false : used >= Number(limit);

    return {
        plan: user.plan,
        limit,
        used,
        remaining,
        isBlocked,
        resetAt,
        msUntilReset,
        devicesLimit: policy.devices,
    };
};

export const consumeUserQueryCredit = (profile?: UserProfile | null): { allowed: boolean; status: UserQueryQuotaStatus } => {
    const user = profile || getUserProfile();
    const status = getUserQueryQuotaStatus(user);
    if (!user) return { allowed: false, status };
    if (status.isBlocked) return { allowed: false, status };

    const usageMap = getQueryUsageMap();
    const current = usageMap[user.id];
    const now = Date.now();
    const shouldReset = !current || (now - current.windowStart >= QUERY_WINDOW_MS);
    const nextUsed = shouldReset ? 1 : (Math.max(0, Number(current.used || 0)) + 1);
    const nextStart = shouldReset ? now : current.windowStart;

    usageMap[user.id] = { windowStart: nextStart, used: nextUsed };
    saveQueryUsageMap(usageMap);

    const refreshed = getUserQueryQuotaStatus(user);
    const normalized = normalizeProfileQuotaFields({ ...user, creditsUsed: refreshed.used, creditsLimit: refreshed.limit });
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(normalized));

    return { allowed: true, status: refreshed };
};

export const applyPlanToCurrentUser = (plan: UserProfile['plan']) => {
    const user = getUserProfile();
    if (!user) return null;

    const updatedUser = normalizeProfileQuotaFields({
        ...user,
        plan,
        status: 'active',
    });

    const usageMap = getQueryUsageMap();
    usageMap[user.id] = {
        windowStart: Date.now(),
        used: 0,
    };
    saveQueryUsageMap(usageMap);

    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(updatedUser));
    upsertAdminUser(updatedUser);
    return updatedUser;
};

const replaceChatsForUser = (userId: string, sessions: ChatSession[]) => {
    const allChats = getChats();
    const others = allChats.filter(c => c.userId !== userId);
    localStorage.setItem(CHATS_KEY, JSON.stringify([...others, ...sessions]));
};

const saveChatToDatabase = async (chat: ChatSession): Promise<void> => {
    const dbSessionId = resolveDatabaseSessionId(chat.id);

    const sessionPayload = {
        id: dbSessionId,
        user_id: chat.userId,
        agent_id: chat.agentId,
        title: chat.title,
        last_message_at: chat.lastMessageAt,
        preview: chat.preview,
        is_archived: !!chat.isArchived,
    };

    const { error: upsertError } = await supabase.from('chat_sessions').upsert([sessionPayload]);
    if (upsertError) return;

    await supabase.from('messages').delete().eq('session_id', dbSessionId);
    if (!Array.isArray(chat.messages) || chat.messages.length === 0) return;

    const baseMessages = chat.messages.map(message => ({
        session_id: dbSessionId,
        role: message.role,
        text: message.text,
        timestamp: message.timestamp,
    }));

    let { error: messageError } = await supabase.from('messages').insert(baseMessages);
    if (!messageError) return;

    // Compatibilidade com schema antigo (created_at ao invés de timestamp)
    const fallbackMessages = chat.messages.map(message => ({
        session_id: dbSessionId,
        role: message.role,
        text: message.text,
        created_at: message.timestamp,
    }));

    await supabase.from('messages').insert(fallbackMessages);
};

const deleteChatFromDatabase = async (sessionId: string): Promise<void> => {
    const dbSessionId = resolveDatabaseSessionId(sessionId);
    await supabase.from('chat_sessions').delete().eq('id', dbSessionId);
};

const fetchMessagesForSessions = async (sessionIds: string[]): Promise<SupabaseMessageRow[]> => {
    if (!sessionIds.length) return [];

    const first = await supabase
        .from('messages')
        .select('id,session_id,role,text,timestamp')
        .in('session_id', sessionIds);

    if (!first.error && first.data) return first.data as SupabaseMessageRow[];

    const fallback = await supabase
        .from('messages')
        .select('id,session_id,role,text,created_at')
        .in('session_id', sessionIds);

    if (!fallback.error && fallback.data) return fallback.data as SupabaseMessageRow[];
    return [];
};

export const syncChatsFromDatabase = async (force = false): Promise<ChatSession[]> => {
    const now = Date.now();
    if (!force && chatsSyncPromise) return chatsSyncPromise;
    if (!force && (now - lastChatsSyncAt) < CHATS_SYNC_MIN_INTERVAL_MS) {
        const user = getUserProfile();
        return user ? getChats().filter(c => c.userId === user.id) : [];
    }

    chatsSyncPromise = (async () => {
        try {
            const user = getUserProfile();
            if (!user) return [];

            const { data: sessionsData, error: sessionsError } = await supabase
                .from('chat_sessions')
                .select('id,user_id,agent_id,title,last_message_at,preview,is_archived')
                .eq('user_id', user.id)
                .order('last_message_at', { ascending: false });

            if (sessionsError || !sessionsData) return [];

            const sessionRows = sessionsData as SupabaseChatSessionRow[];
            const sessionIds = sessionRows.map(s => s.id).filter(Boolean);
            const messagesRows = await fetchMessagesForSessions(sessionIds);

            const groupedMessages = new Map<string, Message[]>();
            for (const row of messagesRows) {
                const sessionId = String(row.session_id || '');
                if (!sessionId) continue;
                const entry: Message = {
                    id: row.id || generateUuid(),
                    role: row.role === 'user' ? 'user' : 'model',
                    text: String(row.text || ''),
                    timestamp: String(row.timestamp || row.created_at || new Date().toISOString()),
                };
                const bucket = groupedMessages.get(sessionId) || [];
                bucket.push(entry);
                groupedMessages.set(sessionId, bucket);
            }

            for (const [, messages] of groupedMessages) {
                messages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
            }

            const mapped: ChatSession[] = sessionRows.map(row => ({
                id: row.id,
                userId: row.user_id,
                agentId: row.agent_id,
                title: row.title || 'Conversa',
                lastMessageAt: row.last_message_at || new Date().toISOString(),
                preview: row.preview || 'Sem mensagens',
                isArchived: !!row.is_archived,
                messages: groupedMessages.get(row.id) || [],
            }));

            replaceChatsForUser(user.id, mapped);
            lastChatsSyncAt = Date.now();
            return mapped;
        } catch {
            return [];
        } finally {
            chatsSyncPromise = null;
        }
    })();

    return chatsSyncPromise;
};

// --- MOCK PROFILES ---
const ADMIN_PROFILE: UserProfile = {
    id: 'admin_001',
    name: 'Roberto Administrador',
    company: 'Elevex Corp',
    email: 'admin@elevex.com',
    plan: 'Empresa',
    creditsUsed: 1420,
    creditsLimit: 'Infinity',
    isAdmin: true,
    status: 'active',
    joinedAt: '2023-01-01',
    nextBillingDate: '2024-12-31',
    tokenUsage: { currentMonth: 540000, lastMonth: 420000, history: [300, 400, 540] }
};

const USER_PROFILE: UserProfile = {
    id: 'user_001',
    name: 'Carlos Técnico',
    company: 'Elevadores Brasil',
    email: 'carlos@tecnico.com',
    plan: 'Profissional',
    creditsUsed: 0,
    creditsLimit: 'Infinity',
    isAdmin: false,
    status: 'active',
    joinedAt: '2024-02-15',
    nextBillingDate: '2024-06-15',
    tokenUsage: { currentMonth: 12000, lastMonth: 8000, history: [5, 8, 12] }
};

// --- AUTH ---

export const login = (type: 'admin' | 'user'): UserProfile => {
    const users = ensureAdminUsersSeeded();
    const fallback = type === 'admin' ? ADMIN_PROFILE : USER_PROFILE;
    const profile = users.find(user => type === 'admin' ? !!user.isAdmin : !user.isAdmin) || fallback;
    const normalized = normalizeProfileQuotaFields(profile);
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(normalized));
    upsertAdminUser(normalized);
    return normalized;
};

export const signup = (data: Partial<UserProfile>): UserProfile => {
    const requestedPlan = (['Free', 'Iniciante', 'Profissional', 'Empresa'] as const).includes(data.plan as UserProfile['plan'])
        ? (data.plan as UserProfile['plan'])
        : 'Free';
    const requestedStatus = data.status || (requestedPlan === 'Free' ? 'active' : 'pending_payment');

    const newProfile: UserProfile = {
        id: `user_${Date.now()}`,
        name: data.name || 'Novo Usuário',
        company: data.company || 'Empresa',
        email: data.email || 'user@email.com',
        plan: requestedPlan,
        creditsUsed: 0,
        creditsLimit: requestedPlan === 'Free' ? 1 : requestedPlan === 'Iniciante' ? 5 : 'Infinity',
        isAdmin: false,
        status: requestedStatus,
        joinedAt: new Date().toISOString().split('T')[0],
        nextBillingDate: new Date().toISOString().split('T')[0],
        tokenUsage: { currentMonth: 0, lastMonth: 0, history: [] }
    };
    const normalized = normalizeProfileQuotaFields(newProfile);
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(normalized));
    upsertAdminUser(normalized);
    return normalized;
};

export const updateUserProfile = (updates: Partial<UserProfile>) => {
    const user = getUserProfile();
    if (user) {
        const updated = normalizeProfileQuotaFields({ ...user, ...updates });
        localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(updated));
        upsertAdminUser(updated);
        return updated;
    }
    return null;
};

export const logout = () => {
    localStorage.removeItem(CURRENT_USER_KEY);
};

export const getUserProfile = (): UserProfile | null => {
    const stored = localStorage.getItem(CURRENT_USER_KEY);
    if (!stored) return null;
    try {
        const parsed = JSON.parse(stored) as UserProfile;
        const normalized = normalizeProfileQuotaFields(parsed);
        localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(normalized));
        upsertAdminUser(normalized);
        return normalized;
    } catch {
        return null;
    }
};

// --- DATA ---

export const getChats = (): ChatSession[] => {
    const stored = localStorage.getItem(CHATS_KEY);
    return stored ? JSON.parse(stored) : [];
};

export const saveChat = (chat: ChatSession) => {
    const chats = getChats();
    const index = chats.findIndex(c => c.id === chat.id);
    if (index >= 0) {
        chats[index] = chat;
    } else {
        chats.push(chat);
    }
    localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
    void saveChatToDatabase(chat);
};

// --- SESSIONS ---

export const getSessions = (includeAllUsers?: boolean): ChatSession[] => {
    const allChats = getChats();
    const user = getUserProfile();
    
    if (!user) return [];
    
    // If admin and includeAllUsers is true, return all sessions
    if (includeAllUsers && user.isAdmin) {
        return allChats;
    }
    
    // Otherwise, return only user's sessions
    return allChats.filter(chat => chat.userId === user.id);
};

export const createNewSession = (agentId: string): ChatSession => {
    const user = getUserProfile();
    if (!user) {
        throw new Error('No user logged in');
    }
    
    const agents = getAgents();
    const agent = agents.find(a => a.id === agentId);
    const agentName = agent?.name || 'Assistente';
    
    const newSession: ChatSession = {
        id: generateUuid(),
        userId: user.id,
        agentId,
        title: `Conversa com ${agentName}`,
        lastMessageAt: new Date().toISOString(),
        preview: 'Nova conversa iniciada',
        isArchived: false,
        messages: []
    };
    
    saveChat(newSession);
    return newSession;
};

export const deleteSession = (sessionId: string) => {
    const user = getUserProfile();
    const chats = getChats();
    const session = chats.find(c => c.id === sessionId);
    // Only allow deleting own sessions (or admin can delete any)
    if (session && user && (session.userId === user.id || user.isAdmin)) {
        const filtered = chats.filter(c => c.id !== sessionId);
        localStorage.setItem(CHATS_KEY, JSON.stringify(filtered));
        void deleteChatFromDatabase(sessionId);
    }
};

export const getSession = (sessionId: string): ChatSession | null => {
    const user = getUserProfile();
    const chats = getChats();
    const session = chats.find(c => c.id === sessionId) || null;
    // Only return session if it belongs to the current user (or admin)
    if (session && user && (session.userId === user.id || user.isAdmin)) {
        return session;
    }
    return null;
};

export const saveSession = (session: ChatSession) => {
    saveChat(session);
};

export const renameSession = (sessionId: string, newTitle: string) => {
    const user = getUserProfile();
    const chats = getChats();
    const session = chats.find(c => c.id === sessionId);
    if (session && user && (session.userId === user.id || user.isAdmin)) {
        session.title = newTitle;
        saveChat(session);
    }
};

export const archiveSession = (sessionId: string, archived: boolean) => {
    const user = getUserProfile();
    const chats = getChats();
    const session = chats.find(c => c.id === sessionId);
    if (session && user && (session.userId === user.id || user.isAdmin)) {
        session.isArchived = archived;
        saveChat(session);
    }
};

// --- AGENTS ---

let runtimeAgents: Agent[] = [...DEFAULT_AGENTS];

const clearLegacyAgentLocalData = () => {
    localStorage.removeItem('elevex_custom_agents');
    localStorage.removeItem('elevex_agents_cache');
};

export const getAgents = (): Agent[] => {
    return runtimeAgents.filter(a => !isBlockedLegacyAgent(a));
};

export const saveAgent = (agent: Agent) => {
    if (isBlockedLegacyAgent(agent)) return;

    const index = runtimeAgents.findIndex((a: Agent) => a.id === agent.id);
    if (index >= 0) {
        runtimeAgents[index] = agent;
    } else {
        runtimeAgents.push(agent);
    }
};

export const deleteAgent = (agentId: string) => {
    runtimeAgents = runtimeAgents.filter((a: Agent) => a.id !== agentId);
};

type SupabaseAgentRow = {
    id: string;
    name: string;
    role: string | null;
    description: string | null;
    icon: string | null;
    color: string | null;
    system_instruction: string | null;
    is_custom: boolean | null;
    created_by: string | null;
    brands?: { name?: string } | null;
};

const REMOVED_AGENT_IDS = new Set(['general-tech', 'code-master']);

const normalizeAgentText = (value?: string | null): string =>
    String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

const isBlockedLegacyAgent = (agent: Partial<Agent> & { id?: string }) => {
    if (agent.id && REMOVED_AGENT_IDS.has(agent.id)) return true;

    const name = normalizeAgentText(agent.name);
    const role = normalizeAgentText(agent.role);
    const description = normalizeAgentText(agent.description);

    const blockedByName = name === 'mestre dos codigos' || name === 'tecnico geral';
    const blockedByRole = role === 'decodificador' || role === 'diagnostico universal';
    const blockedByDescription =
        description.includes('especialista em codigos de erro') ||
        description.includes('especialista multimarcas');

    return blockedByName || blockedByRole || blockedByDescription;
};

const mapSupabaseAgentToApp = (row: SupabaseAgentRow): Agent => ({
    id: row.id,
    name: row.name,
    role: row.role || '',
    description: row.description || '',
    icon: row.icon || 'Bot',
    color: row.color || 'blue',
    systemInstruction: row.system_instruction || '',
    brandName: row.brands?.name || undefined,
    isCustom: !!row.is_custom,
    createdBy: row.created_by || undefined,
});

const setAgentsCache = (agents: Agent[]) => {
    runtimeAgents = agents.filter(a => !isBlockedLegacyAgent(a));
};

export const syncAgentsFromDatabase = async (): Promise<Agent[]> => {
    const now = Date.now();
    if (agentsSyncPromise) return agentsSyncPromise;
    if ((now - lastAgentsSyncAt) < AGENTS_SYNC_MIN_INTERVAL_MS && runtimeAgents.length > 0) {
        return runtimeAgents;
    }

    agentsSyncPromise = (async () => {
    try {
        clearLegacyAgentLocalData();

        const response = await fetch(ragUrl('/api/agents'));
        if (!response.ok) {
            return runtimeAgents;
        }

        const data = await response.json();
        if (!Array.isArray(data)) return runtimeAgents;

        const allAgents = (data as SupabaseAgentRow[]).map(mapSupabaseAgentToApp);

        const filtered = allAgents.filter(a => !isBlockedLegacyAgent(a));
        setAgentsCache(filtered);
        lastAgentsSyncAt = Date.now();
        return filtered;
    } catch {
        return runtimeAgents;
    } finally {
        agentsSyncPromise = null;
    }
    })();

    return agentsSyncPromise;
};

export const saveAgentToDatabase = async (agent: Agent): Promise<Agent> => {
    if (isBlockedLegacyAgent(agent)) {
        throw new Error('Este agente foi descontinuado e não pode ser criado');
    }

    const user = getUserProfile();
    if (!user?.isAdmin) {
        throw new Error('Somente admin pode criar/editar agentes globais');
    }

    // Resolve brand_id pela brandName (quando informado)
    let brandId: string | null = null;
    if (agent.brandName) {
        try {
            const brandsResponse = await fetch(ragUrl('/api/brands'));
            const brandsData = brandsResponse.ok ? await brandsResponse.json() : [];
            const matched = Array.isArray(brandsData)
                ? brandsData.find((b: any) => String(b?.name || '').toLowerCase() === String(agent.brandName || '').toLowerCase())
                : null;
            brandId = matched?.id || null;
        } catch {
            brandId = null;
        }
    }

    const payload = {
        id: agent.id,
        name: agent.name,
        role: agent.role,
        description: agent.description,
        icon: agent.icon,
        color: agent.color,
        system_instruction: agent.systemInstruction,
        brand_id: brandId,
        is_custom: true,
        created_by: user?.id || agent.createdBy || null,
    };

    const response = await fetch(ragUrl('/api/agents'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...ragHeaders(true),
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Falha ao salvar agente no banco');
    }

    await syncAgentsFromDatabase();
    return agent;
};

export const deleteAgentFromDatabase = async (agentId: string): Promise<void> => {
    try {
        const user = getUserProfile();
        if (!user?.isAdmin) {
            throw new Error('Somente admin pode excluir agentes globais');
        }

        const response = await fetch(ragUrl(`/api/agents/${encodeURIComponent(agentId)}`), {
            method: 'DELETE',
            headers: {
                ...ragHeaders(true),
            },
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || 'Falha ao excluir agente no banco');
        }

        await syncAgentsFromDatabase();
    } catch {
        throw new Error('Falha ao excluir agente no banco');
    }
};

// --- ADMIN ---

export const getAdminUsers = (): UserProfile[] => {
    const users = ensureAdminUsersSeeded();
    const current = getUserProfile();
    if (current) {
        return upsertAdminUser(current);
    }
    return users;
};

export const toggleUserStatus = (userId: string, newStatus: 'active' | 'inactive' | 'overdue' | 'pending_payment'): UserProfile[] => {
    const users = getAdminUsers();
    const user = users.find(u => u.id === userId);
    if (user) {
        user.status = newStatus;
    }
    localStorage.setItem(ADMIN_USERS_KEY, JSON.stringify(users));
    const current = getUserProfile();
    if (current && current.id === userId) {
        localStorage.setItem(CURRENT_USER_KEY, JSON.stringify({ ...current, status: newStatus }));
    }
    return users;
};

export const getFinancialMetrics = (period: FinancialMetricsPeriod = '30d') => {
    const users = getAdminUsers().filter(user => !user.isAdmin);
    const chats = getChats();
    const { now, currentStart, previousStart } = getPeriodRange(period);

    const activeStatuses: UserProfile['status'][] = ['active'];
    const activeUsers = users.filter(user => activeStatuses.includes(user.status)).length;
    const totalUsers = users.length;

    const currentRevenue = users
        .filter(user => activeStatuses.includes(user.status))
        .reduce((sum, user) => sum + PLAN_MONTHLY_PRICE[user.plan], 0);

    const previousRevenue = users
        .filter(user => {
            const joined = new Date(user.joinedAt).getTime();
            return joined <= currentStart && activeStatuses.includes(user.status);
        })
        .reduce((sum, user) => sum + PLAN_MONTHLY_PRICE[user.plan], 0);

    const currentQueries = chats.reduce((sum, session) => {
        if (!session.lastMessageAt) return sum;
        const ts = new Date(session.lastMessageAt).getTime();
        if (ts >= currentStart && ts <= now) {
            const userMessages = Array.isArray(session.messages)
                ? session.messages.filter(message => message.role === 'user').length
                : 0;
            return sum + Math.max(1, userMessages);
        }
        return sum;
    }, 0);

    const previousQueries = chats.reduce((sum, session) => {
        if (!session.lastMessageAt) return sum;
        const ts = new Date(session.lastMessageAt).getTime();
        if (ts >= previousStart && ts < currentStart) {
            const userMessages = Array.isArray(session.messages)
                ? session.messages.filter(message => message.role === 'user').length
                : 0;
            return sum + Math.max(1, userMessages);
        }
        return sum;
    }, 0);

    const deactivatedInPeriod = users.filter(user => {
        const joined = new Date(user.joinedAt).getTime();
        return user.status !== 'active' && joined >= currentStart && joined <= now;
    }).length;

    const churn = totalUsers > 0 ? (deactivatedInPeriod / totalUsers) * 100 : 0;
    const revenueChange = previousRevenue > 0 ? ((currentRevenue - previousRevenue) / previousRevenue) * 100 : (currentRevenue > 0 ? 100 : 0);
    const queriesChange = previousQueries > 0 ? ((currentQueries - previousQueries) / previousQueries) * 100 : (currentQueries > 0 ? 100 : 0);

    const planCounts: Record<UserProfile['plan'], number> = {
        Empresa: users.filter(user => user.plan === 'Empresa').length,
        Profissional: users.filter(user => user.plan === 'Profissional').length,
        Iniciante: users.filter(user => user.plan === 'Iniciante').length,
        Free: users.filter(user => user.plan === 'Free').length,
    };

    const planDistribution = (Object.entries(planCounts) as [UserProfile['plan'], number][]).map(([plan, count]) => ({
        plan,
        count,
        percent: totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0,
    }));

    const usageByAgent = new Map<string, number>();
    for (const session of chats) {
        const current = usageByAgent.get(session.agentId) || 0;
        const messageCount = Array.isArray(session.messages)
            ? session.messages.filter(message => message.role === 'user').length
            : 0;
        usageByAgent.set(session.agentId, current + Math.max(1, messageCount));
    }

    const agents = getAgents();
    const topAgents = Array.from(usageByAgent.entries())
        .map(([agentId, queries]) => ({
            agentName: agents.find(agent => agent.id === agentId)?.name || 'Assistente',
            queries,
        }))
        .sort((a, b) => b.queries - a.queries)
        .slice(0, 5);

    return {
        totalUsers,
        activeUsers,
        mrr: formatReais(currentRevenue),
        churnRate: `${churn.toFixed(1)}%`,
        totalQueries: currentQueries,
        revenueChange,
        queriesChange,
        planDistribution,
        topAgents,
    };
};

// --- BRANDS & MODELS ---

export const getBrands = (): Brand[] => {
    const stored = localStorage.getItem(BRANDS_KEY);
    if (!stored) {
        // Initialize with default brands
        const defaultBrands: Brand[] = [
            { id: 'brand_001', name: 'Schindler', created_at: new Date().toISOString() },
            { id: 'brand_002', name: 'Otis', created_at: new Date().toISOString() },
            { id: 'brand_003', name: 'Thyssenkrupp', created_at: new Date().toISOString() },
            { id: 'brand_004', name: 'Atlas', created_at: new Date().toISOString() }
        ];
        localStorage.setItem(BRANDS_KEY, JSON.stringify(defaultBrands));
        return defaultBrands;
    }
    return JSON.parse(stored);
};

export const saveBrand = (brand: Brand): Brand => {
    const brands = getBrands();
    const existing = brands.findIndex(b => b.id === brand.id);
    
    if (existing >= 0) {
        brands[existing] = brand;
    } else {
        // New brand
        if (!brand.id) {
            brand.id = `brand_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }
        if (!brand.created_at) {
            brand.created_at = new Date().toISOString();
        }
        brands.push(brand);
    }
    
    localStorage.setItem(BRANDS_KEY, JSON.stringify(brands));
    return brand;
};

export const updateBrand = (brandId: string, updates: Partial<Brand>): Brand | null => {
    const brands = getBrands();
    const index = brands.findIndex(b => b.id === brandId);
    
    if (index >= 0) {
        brands[index] = { ...brands[index], ...updates };
        localStorage.setItem(BRANDS_KEY, JSON.stringify(brands));
        return brands[index];
    }
    
    return null;
};

export const deleteBrand = (brandId: string) => {
    const brands = getBrands();
    const filtered = brands.filter(b => b.id !== brandId);
    localStorage.setItem(BRANDS_KEY, JSON.stringify(filtered));
    
    // Also delete associated models
    const models = getModels();
    const filteredModels = models.filter(m => m.brand_id !== brandId);
    localStorage.setItem(MODELS_KEY, JSON.stringify(filteredModels));
};

export const getModels = (brandId?: string): Model[] => {
    const stored = localStorage.getItem(MODELS_KEY);
    const models = stored ? JSON.parse(stored) : [];
    
    if (brandId) {
        return models.filter((m: Model) => m.brand_id === brandId);
    }
    
    return models;
};

export const saveModel = (model: Model): Model => {
    const models = getModels();
    const existing = models.findIndex(m => m.id === model.id);
    
    if (existing >= 0) {
        models[existing] = model;
    } else {
        // New model
        if (!model.id) {
            model.id = `model_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }
        if (!model.created_at) {
            model.created_at = new Date().toISOString();
        }
        models.push(model);
    }
    
    localStorage.setItem(MODELS_KEY, JSON.stringify(models));
    return model;
};

export const updateModel = (modelId: string, updates: Partial<Model>): Model | null => {
    const models = getModels();
    const index = models.findIndex(m => m.id === modelId);
    
    if (index >= 0) {
        models[index] = { ...models[index], ...updates };
        localStorage.setItem(MODELS_KEY, JSON.stringify(models));
        return models[index];
    }
    
    return null;
};

export const deleteModel = (modelId: string) => {
    const models = getModels();
    const filtered = models.filter(m => m.id !== modelId);
    localStorage.setItem(MODELS_KEY, JSON.stringify(filtered));
};
