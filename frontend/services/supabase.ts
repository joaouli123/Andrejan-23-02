type Row = Record<string, any>;
import { ragUrl } from './ragApi';

type QueryResult<T> = { data: T | null; error: { message: string } | null };

type FilterOp = {
  kind: 'eq' | 'in';
  field: string;
  value: any;
};

const TABLE_KEYS: Record<string, string> = {
  brands: 'elevex_tbl_brands',
  models: 'elevex_tbl_models',
  source_files: 'elevex_tbl_source_files',
  agents: 'elevex_tbl_agents',
  chat_sessions: 'elevex_tbl_chat_sessions',
  messages: 'elevex_tbl_messages',
};

const nowIso = () => new Date().toISOString();

const getTable = (table: string): Row[] => {
  const key = TABLE_KEYS[table] || `elevex_tbl_${table}`;
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const setTable = (table: string, rows: Row[]) => {
  const key = TABLE_KEYS[table] || `elevex_tbl_${table}`;
  localStorage.setItem(key, JSON.stringify(rows));
};

const toError = (error: any) => ({ message: error?.message || 'Erro inesperado' });

const applyFilters = (rows: Row[], filters: FilterOp[]) => {
  return rows.filter((row) => {
    return filters.every((filter) => {
      if (filter.kind === 'eq') {
        return String(row?.[filter.field]) === String(filter.value);
      }
      if (filter.kind === 'in') {
        const values = Array.isArray(filter.value) ? filter.value : [];
        return values.map(String).includes(String(row?.[filter.field]));
      }
      return true;
    });
  });
};

const sortRows = (rows: Row[], field?: string, ascending = true) => {
  if (!field) return rows;
  const sorted = [...rows].sort((a, b) => {
    const av = a?.[field];
    const bv = b?.[field];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === 'number' && typeof bv === 'number') return av - bv;
    return String(av).localeCompare(String(bv));
  });
  return ascending ? sorted : sorted.reverse();
};

const mapBackendBrand = (row: any) => ({
  id: String(row.id),
  name: row.name,
  created_at: row.created_at || nowIso(),
  slug: row.slug,
});

const backendBrands = {
  async select(): Promise<QueryResult<any[]>> {
    try {
      const res = await fetch(ragUrl('/api/brands'));
      if (!res.ok) return { data: [], error: null };
      const data = await res.json();
      return { data: (data || []).map(mapBackendBrand), error: null };
    } catch {
      return { data: [], error: null };
    }
  },
  async insert(rows: Row[]): Promise<QueryResult<any[]>> {
    try {
      const created: any[] = [];
      for (const row of rows || []) {
        const name = String(row?.name || '').trim();
        if (!name) continue;
        const res = await fetch(ragUrl('/api/brands'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        });
        if (!res.ok) {
          const text = await res.text();
          return { data: null, error: { message: text || `Falha ao criar marca (${res.status})` } };
        }
        created.push(mapBackendBrand(await res.json()));
      }
      return { data: created, error: null };
    } catch (error) {
      return { data: null, error: toError(error) };
    }
  },
  async update(id: string, values: Row): Promise<QueryResult<any[]>> {
    try {
      const res = await fetch(ragUrl(`/api/brands/${encodeURIComponent(String(id))}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values || {}),
      });
      if (!res.ok) {
        const text = await res.text();
        return { data: null, error: { message: text || `Falha ao atualizar marca (${res.status})` } };
      }
      const updated = mapBackendBrand(await res.json());
      return { data: [updated], error: null };
    } catch (error) {
      return { data: null, error: toError(error) };
    }
  },
  async delete(id: string): Promise<QueryResult<any[]>> {
    try {
      const res = await fetch(ragUrl(`/api/brands/${encodeURIComponent(String(id))}`), { method: 'DELETE' });
      if (!res.ok) {
        const text = await res.text();
        return { data: null, error: { message: text || `Falha ao excluir marca (${res.status})` } };
      }
      return { data: [], error: null };
    } catch (error) {
      return { data: null, error: toError(error) };
    }
  },
};

class QueryBuilder {
  private table: string;
  private operation: 'select' | 'insert' | 'update' | 'delete' | 'upsert' = 'select';
  private payload: any = null;
  private filters: FilterOp[] = [];
  private orderField?: string;
  private orderAsc = true;
  private limitCount?: number;
  private expectSingle = false;

  constructor(table: string) {
    this.table = table;
  }

  select(_columns?: string) {
    this.operation = 'select';
    return this;
  }

  insert(rows: Row[]) {
    this.operation = 'insert';
    this.payload = rows;
    return this;
  }

  upsert(rows: Row[]) {
    this.operation = 'upsert';
    this.payload = rows;
    return this;
  }

  update(values: Row) {
    this.operation = 'update';
    this.payload = values;
    return this;
  }

  delete() {
    this.operation = 'delete';
    return this;
  }

  eq(field: string, value: any) {
    this.filters.push({ kind: 'eq', field, value });
    return this;
  }

  in(field: string, value: any[]) {
    this.filters.push({ kind: 'in', field, value });
    return this;
  }

  order(field: string, options?: { ascending?: boolean }) {
    this.orderField = field;
    this.orderAsc = options?.ascending !== false;
    return this;
  }

  limit(count: number) {
    this.limitCount = count;
    return this;
  }

  maybeSingle() {
    this.expectSingle = true;
    return this;
  }

  private async runBrands(): Promise<QueryResult<any>> {
    if (this.operation === 'select') {
      const result = await backendBrands.select();
      if (result.error || !result.data) return result;
      let rows = applyFilters(result.data, this.filters);
      rows = sortRows(rows, this.orderField, this.orderAsc);
      if (typeof this.limitCount === 'number') rows = rows.slice(0, this.limitCount);
      if (this.expectSingle) return { data: rows[0] || null, error: null };
      return { data: rows, error: null };
    }

    const idFilter = this.filters.find((f) => f.kind === 'eq' && f.field === 'id');

    if (this.operation === 'insert') {
      return backendBrands.insert(this.payload || []);
    }

    if (this.operation === 'update') {
      if (!idFilter) return { data: null, error: { message: 'Filtro id obrigatório para update' } };
      return backendBrands.update(String(idFilter.value), this.payload || {});
    }

    if (this.operation === 'delete') {
      if (!idFilter) return { data: null, error: { message: 'Filtro id obrigatório para delete' } };
      return backendBrands.delete(String(idFilter.value));
    }

    if (this.operation === 'upsert') {
      const rows = Array.isArray(this.payload) ? this.payload : [];
      const output: Row[] = [];
      for (const row of rows) {
        if (row?.id) {
          const updated = await backendBrands.update(String(row.id), row);
          if (updated.error) return updated;
          if (Array.isArray(updated.data)) output.push(...updated.data);
        } else {
          const created = await backendBrands.insert([row]);
          if (created.error) return created;
          if (Array.isArray(created.data)) output.push(...created.data);
        }
      }
      return { data: output, error: null };
    }

    return { data: [], error: null };
  }

  private async runLocal(): Promise<QueryResult<any>> {
    try {
      let rows = getTable(this.table);

      if (this.operation === 'select') {
        rows = applyFilters(rows, this.filters);
        rows = sortRows(rows, this.orderField, this.orderAsc);
        if (typeof this.limitCount === 'number') rows = rows.slice(0, this.limitCount);
        if (this.expectSingle) return { data: rows[0] || null, error: null };
        return { data: rows, error: null };
      }

      if (this.operation === 'insert') {
        const inserts = (Array.isArray(this.payload) ? this.payload : []).map((item) => ({
          ...item,
          id: item?.id || `${this.table}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
          created_at: item?.created_at || nowIso(),
        }));
        rows = [...rows, ...inserts];
        setTable(this.table, rows);
        return { data: inserts, error: null };
      }

      if (this.operation === 'upsert') {
        const upserts = Array.isArray(this.payload) ? this.payload : [];
        const byId = new Map(rows.map((r) => [String(r.id), r]));
        for (const item of upserts) {
          const id = String(item?.id || `${this.table}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`);
          const previous = byId.get(id) || {};
          byId.set(id, {
            ...previous,
            ...item,
            id,
            created_at: previous?.created_at || item?.created_at || nowIso(),
          });
        }
        rows = Array.from(byId.values());
        setTable(this.table, rows);
        return { data: rows, error: null };
      }

      const targetRows = applyFilters(rows, this.filters);

      if (this.operation === 'update') {
        const updates = this.payload || {};
        const targetIds = new Set(targetRows.map((r) => String(r.id)));
        rows = rows.map((row) => (targetIds.has(String(row.id)) ? { ...row, ...updates } : row));
        setTable(this.table, rows);
        const updated = rows.filter((r) => targetIds.has(String(r.id)));
        if (this.expectSingle) return { data: updated[0] || null, error: null };
        return { data: updated, error: null };
      }

      if (this.operation === 'delete') {
        const targetIds = new Set(targetRows.map((r) => String(r.id)));
        rows = rows.filter((row) => !targetIds.has(String(row.id)));
        setTable(this.table, rows);
        return { data: [], error: null };
      }

      return { data: [], error: null };
    } catch (error) {
      return { data: null, error: toError(error) };
    }
  }

  private execute(): Promise<QueryResult<any>> {
    if (this.table === 'brands') {
      return this.runBrands();
    }
    return this.runLocal();
  }

  then<TResult1 = QueryResult<any>, TResult2 = never>(
    onfulfilled?: ((value: QueryResult<any>) => TResult1 | PromiseLike<TResult1>) | null,
    onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | null,
  ): Promise<TResult1 | TResult2> {
    return this.execute().then(onfulfilled as any, onrejected as any);
  }
}

export const supabase = {
  from(table: string) {
    return new QueryBuilder(table);
  },
};
