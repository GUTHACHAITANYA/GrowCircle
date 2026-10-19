'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import {
  ShieldAlert,
  FileText,
  CheckCircle2,
  XCircle,
  Eye,
  Download,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react';

interface AuditLogEntry {
  id: number;
  timestamp: string;
  action: string;
  user_id: number | null;
  actor_role: string | null;
  client_ip: string | null;
  target_resource: string | null;
  target_id: string | null;
  details: string | null;
  status: string;
}

const DEMO_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 1,
    timestamp: '2026-10-16T13:40:12Z',
    action: 'APPROVAL',
    user_id: 1,
    actor_role: 'admin',
    client_ip: '127.0.0.1',
    target_resource: 'BuyerProfile',
    target_id: '1',
    details: 'Admin verified buyer registration for Sri Chaitanya Educational Institutions',
    status: 'SUCCESS',
  },
  {
    id: 2,
    timestamp: '2026-10-16T13:35:40Z',
    action: 'DOCUMENT_VIEW',
    user_id: 1,
    actor_role: 'admin',
    client_ip: '127.0.0.1',
    target_resource: 'BuyerProfile',
    target_id: 'pending_queue',
    details: 'Admin viewed decrypted GST and proof documents for pending buyer queue',
    status: 'SUCCESS',
  },
  {
    id: 3,
    timestamp: '2026-10-16T13:10:05Z',
    action: 'DPDP_DATA_EXPORT',
    user_id: 10,
    actor_role: 'farmer',
    client_ip: '127.0.0.1',
    target_resource: 'User',
    target_id: '10',
    details: 'User downloaded complete personal data package under DPDP Act Section 11',
    status: 'SUCCESS',
  },
  {
    id: 4,
    timestamp: '2026-10-16T12:55:22Z',
    action: 'REJECTION',
    user_id: 1,
    actor_role: 'admin',
    client_ip: '127.0.0.1',
    target_resource: 'Transporter',
    target_id: '3',
    details: 'Admin rejected driver application due to expired commercial fitness certificate',
    status: 'SUCCESS',
  },
];

export const AuditLogsSection: React.FC = () => {
  const { token } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>(DEMO_AUDIT_LOGS);
  const [filterAction, setFilterAction] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const url = filterAction === 'all'
        ? `${API_BASE}/auth/audit-logs`
        : `${API_BASE}/auth/audit-logs?action=${filterAction}`;
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const json = await res.json();
        setLogs(json);
      }
    } catch {
      // Keep demo fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filterAction, token]);

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'DOCUMENT_VIEW':
        return (
          <span className="px-2.5 py-1 rounded-md bg-blue-50 text-blue-800 border border-blue-200 text-xs font-bold flex items-center gap-1.5 w-fit">
            <Eye className="w-3.5 h-3.5" />
            <span>DOCUMENT VIEW</span>
          </span>
        );
      case 'APPROVAL':
        return (
          <span className="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold flex items-center gap-1.5 w-fit">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>APPROVAL</span>
          </span>
        );
      case 'REJECTION':
        return (
          <span className="px-2.5 py-1 rounded-md bg-red-50 text-red-800 border border-red-200 text-xs font-bold flex items-center gap-1.5 w-fit">
            <XCircle className="w-3.5 h-3.5" />
            <span>REJECTION</span>
          </span>
        );
      case 'DPDP_DATA_EXPORT':
        return (
          <span className="px-2.5 py-1 rounded-md bg-purple-50 text-purple-800 border border-purple-200 text-xs font-bold flex items-center gap-1.5 w-fit">
            <Download className="w-3.5 h-3.5" />
            <span>DATA EXPORT</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-800 text-xs font-bold w-fit">
            {action}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-ink flex items-center gap-2">
            <FileText className="w-5 h-5 text-deep-leaf" />
            <span>Security & Compliance Audit Trail</span>
          </h2>
          <p className="text-xs text-muted mt-0.5">
            Immutable log of sensitive actions: decrypted document views, approvals, rejections, and DPDP data exports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="px-3 py-2 bg-white border border-border rounded-xl text-xs font-bold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf"
          >
            <option value="all">All Sensitive Actions</option>
            <option value="DOCUMENT_VIEW">Document Views</option>
            <option value="APPROVAL">Approvals</option>
            <option value="REJECTION">Rejections</option>
            <option value="DPDP_DATA_EXPORT">Data Exports</option>
          </select>

          <Button
            variant="secondary"
            size="md"
            onClick={fetchLogs}
            disabled={isLoading}
            leftIcon={<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border bg-white shadow-xs">
        <table className="w-full text-left text-sm">
          <thead className="bg-cream/60 border-b border-border text-xs text-ink uppercase tracking-wider font-bold">
            <tr>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Actor</th>
              <th className="py-3 px-4">Target Resource</th>
              <th className="py-3 px-4">Details</th>
              <th className="py-3 px-4">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-cream/30 transition-colors">
                <td className="py-3.5 px-4">{getActionBadge(log.action)}</td>
                <td className="py-3.5 px-4">
                  <div className="font-bold text-ink text-xs">
                    {log.actor_role?.toUpperCase() || 'USER'} #{log.user_id || 'System'}
                  </div>
                  <div className="text-[11px] text-muted font-mono">{log.client_ip || 'IP Masked'}</div>
                </td>
                <td className="py-3.5 px-4">
                  <span className="font-mono text-xs font-bold text-ink">
                    {log.target_resource} #{log.target_id}
                  </span>
                </td>
                <td className="py-3.5 px-4 text-xs text-ink max-w-xs">{log.details}</td>
                <td className="py-3.5 px-4 text-xs text-muted whitespace-nowrap">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Recent'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
