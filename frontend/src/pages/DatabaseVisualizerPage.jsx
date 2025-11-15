import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { isSuperAdmin } from '../utils/permissionUtils';
import { Button } from '../components/ui/button';

const humanizeBytes = (value) => {
  if (!value && value !== 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = Number(value);
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

const formatDate = (value) => {
  if (!value) {
    return '—';
  }
  try {
    return new Date(value).toLocaleString();
  } catch (err) {
    return value;
  }
};

const DatabaseVisualizerPage = ({ user }) => {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [forbidden, setForbidden] = useState(false);
  const [expandedTables, setExpandedTables] = useState({});
  const superAdmin = useMemo(() => isSuperAdmin(user), [user]);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError('');
    setForbidden(false);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/dev/db-overview`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 20000
      });
      setOverview(response.data);
    } catch (err) {
      console.error('Failed to load database overview:', err);
      if (err.response?.status === 403) {
        setForbidden(true);
      } else {
        setError(err.response?.data?.detail || err.message || 'Unable to load database overview.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (superAdmin) {
      fetchOverview();
    } else {
      setLoading(false);
    }
  }, [fetchOverview, superAdmin]);

  const toggleTable = (tableName) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName]
    }));
  };

  if (!superAdmin) {
    return (
      <div className="min-h-screen bg-[#05060d] text-white flex flex-col items-center justify-center p-6">
        <div className="max-w-lg text-center">
          <h1 className="text-3xl font-semibold mb-4">403 – Access Restricted</h1>
          <p className="text-gray-400 mb-8">
            The database visualizer is available to Super Admins only. Please contact your workspace owner if you need
            access.
          </p>
          <Button asChild className="bg-purple-600 hover:bg-purple-500 text-white">
            <a href="/">Return to dashboard</a>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05060d] text-white">
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-widest text-purple-400">Developer Utility</p>
            <h1 className="text-3xl font-bold">Database Overview – {overview?.summary?.database_name || 'pf_messenger'}</h1>
            <p className="text-gray-400">
              Live metadata powered by information_schema. Snapshotting runs each time this page loads.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="ghost" className="text-gray-300 border border-white/10" onClick={() => (window.location.href = '/')}>
              Exit
            </Button>
            <Button onClick={fetchOverview} disabled={loading}>
              {loading ? 'Refreshing…' : 'Refresh'}
            </Button>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="h-12 w-12 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : forbidden ? (
          <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-6 text-center text-red-200">
            You do not have permission to view this data.
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-6 text-center text-red-200">
            {error}
          </div>
        ) : (
          overview && (
            <div className="space-y-10">
              <section className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-white/5 bg-white/5 p-5">
                  <p className="text-sm text-gray-400">Database</p>
                  <p className="text-2xl font-semibold">{overview.summary.database_name || 'pf_messenger'}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    Last schema update: {formatDate(overview.summary.last_update)}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/5 bg-white/5 p-5">
                  <p className="text-sm text-gray-400">Tables</p>
                  <p className="text-2xl font-semibold">{overview.summary.table_count}</p>
                  <p className="text-xs text-gray-500 mt-2">Approx. rows: {overview.summary.total_rows.toLocaleString()}</p>
                </div>
                <div className="rounded-2xl border border-white/5 bg-white/5 p-5">
                  <p className="text-sm text-gray-400">Storage</p>
                  <p className="text-2xl font-semibold">{overview.summary.total_size_readable}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    Data: {humanizeBytes(overview.summary.data_size_bytes)} · Index:{' '}
                    {humanizeBytes(overview.summary.index_size_bytes)}
                  </p>
                </div>
              </section>

              {overview.summary.info_message && (
                <div className="rounded-2xl border border-yellow-500/40 bg-yellow-500/10 p-4 text-sm text-yellow-200">
                  {overview.summary.info_message}
                </div>
              )}

              <section>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">Tables ({overview.tables.length})</h2>
                    <p className="text-sm text-gray-400">Click a table to inspect its columns and metadata.</p>
                  </div>
                </div>
                <div className="space-y-3">
                  {overview.tables.map((table) => (
                    <div key={table.name} className="rounded-2xl border border-white/5 bg-white/2">
                      <button
                        type="button"
                        className="w-full flex flex-col gap-1 md:flex-row md:items-center md:justify-between p-4 text-left hover:bg-white/5"
                        onClick={() => toggleTable(table.name)}
                      >
                        <div>
                          <p className="text-lg font-semibold">{table.name}</p>
                          <p className="text-sm text-gray-400">
                            Rows: {table.rows?.toLocaleString() ?? '—'} · Size: {table.total_size_readable}
                          </p>
                        </div>
                        <div className="text-sm text-gray-400">
                          Updated {formatDate(table.update_time) || formatDate(table.create_time)}
                        </div>
                      </button>
                      {expandedTables[table.name] && (
                        <div className="px-4 pb-4">
                          <div className="overflow-x-auto rounded-xl border border-white/5">
                            <table className="min-w-full text-sm">
                              <thead className="bg-white/5 text-gray-300">
                                <tr>
                                  <th className="px-3 py-2 text-left">Column</th>
                                  <th className="px-3 py-2 text-left">Type</th>
                                  <th className="px-3 py-2 text-left">Nullable</th>
                                  <th className="px-3 py-2 text-left">Default</th>
                                  <th className="px-3 py-2 text-left">Key</th>
                                  <th className="px-3 py-2 text-left">Extra</th>
                                </tr>
                              </thead>
                              <tbody>
                                {table.columns.map((column) => (
                                  <tr key={column.name} className="border-t border-white/5">
                                    <td className="px-3 py-2 font-mono text-sm">{column.name}</td>
                                    <td className="px-3 py-2">{column.data_type}</td>
                                    <td className="px-3 py-2">{column.nullable ? 'YES' : 'NO'}</td>
                                    <td className="px-3 py-2 text-gray-400">{column.default ?? '—'}</td>
                                    <td className="px-3 py-2">{column.key || '—'}</td>
                                    <td className="px-3 py-2 text-gray-400">{column.extra || '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              <section className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-white/5 bg-white/5 p-5 space-y-4">
                  <div>
                    <h2 className="text-xl font-semibold">Relationships</h2>
                    <p className="text-sm text-gray-400">Foreign keys discovered via information_schema.</p>
                  </div>
                  <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                    {overview.relationships.length === 0 ? (
                      <p className="text-gray-400 text-sm">No relationships detected.</p>
                    ) : (
                      overview.relationships.map((rel) => (
                        <div key={`${rel.table}.${rel.column}`} className="rounded-xl border border-white/10 p-3 bg-black/20">
                          <p className="font-mono text-sm">
                            <span className="text-purple-300">{rel.table}</span>.
                            <span className="text-purple-200">{rel.column}</span>
                            <span className="text-gray-400"> → </span>
                            <span className="text-sky-300">{rel.references_table}</span>.
                            <span className="text-sky-200">{rel.references_column}</span>
                          </p>
                          {rel.constraint_name && (
                            <p className="text-xs text-gray-500 mt-1">Constraint: {rel.constraint_name}</p>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/5 bg-white/5 p-5 space-y-4">
                  <div className="flex flex-col gap-1">
                    <h2 className="text-xl font-semibold">Schema Changes</h2>
                    <p className="text-sm text-gray-400">Automatic snapshots highlight new tables and column updates.</p>
                  </div>
                  {overview.schema_changes.latest_summary && overview.schema_changes.latest_summary.change_count ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl border border-purple-500/40 bg-purple-500/10 p-3">
                        <p className="text-xs uppercase text-purple-200 tracking-widest">New Tables</p>
                        <p className="text-2xl font-semibold">
                          {overview.schema_changes.latest_summary.new_tables || 0}
                        </p>
                      </div>
                      <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3">
                        <p className="text-xs uppercase text-emerald-200 tracking-widest">Column Updates</p>
                        <p className="text-2xl font-semibold">
                          {overview.schema_changes.latest_summary.columns_changed || 0}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400">No schema changes detected yet.</p>
                  )}
                  <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                    {overview.schema_changes.recent_snapshots.length === 0 ? (
                      <p className="text-sm text-gray-400">Snapshots will appear after the first capture.</p>
                    ) : (
                      overview.schema_changes.recent_snapshots.map((snapshot) => (
                        <div key={snapshot.id} className="rounded-xl border border-white/10 p-3 bg-black/20">
                          <p className="text-sm font-semibold">Snapshot #{snapshot.id}</p>
                          <p className="text-xs text-gray-500 mb-2">{formatDate(snapshot.created_at)}</p>
                          {snapshot.changes.length === 0 ? (
                            <p className="text-xs text-gray-500">No changes captured.</p>
                          ) : (
                            <ul className="space-y-2 text-sm">
                              {snapshot.changes.map((change, idx) => (
                                <li key={`${snapshot.id}-${change.table_name}-${change.column_name || 'table'}-${idx}`}>
                                  <span className="font-semibold text-purple-200">{change.change_type}</span> ·{' '}
                                  <span className="text-gray-300">{change.table_name}</span>
                                  {change.column_name && (
                                    <>
                                      <span className="text-gray-400">.</span>
                                      <span className="text-gray-200">{change.column_name}</span>
                                    </>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-white/5 bg-white/5 p-5 space-y-4">
                <div className="flex flex-col gap-1">
                  <h2 className="text-xl font-semibold">Storage Breakdown</h2>
                  <p className="text-sm text-gray-400">
                    Largest tables by combined data + index footprint. Values are approximate.
                  </p>
                </div>
                <div className="space-y-4">
                  {overview.storage.top_tables.length === 0 ? (
                    <p className="text-sm text-gray-400">No table statistics available.</p>
                  ) : (
                    overview.storage.top_tables.map((table) => {
                      const maxSize = overview.storage.top_tables[0]?.size_bytes || 1;
                      const percent = Math.min(100, Math.round((table.size_bytes / maxSize) * 100));
                      return (
                        <div key={table.name}>
                          <div className="flex justify-between text-sm">
                            <p className="font-semibold">{table.name}</p>
                            <p className="text-gray-400">{table.size_readable}</p>
                          </div>
                          <div className="h-2 bg-white/10 rounded-full mt-2 overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500" style={{ width: `${percent}%` }} />
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Rows: {table.rows?.toLocaleString?.() ?? '—'} ({percent}% of largest table)
                          </p>
                        </div>
                      );
                    })
                  )}
                </div>
              </section>
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default DatabaseVisualizerPage;
