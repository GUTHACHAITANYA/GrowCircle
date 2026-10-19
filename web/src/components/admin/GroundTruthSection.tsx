'use client';

import React, { useState, useEffect } from 'react';
import {
  PhoneCall,
  Download,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
  FileSpreadsheet,
  TrendingUp,
  RefreshCw,
  PlusCircle,
} from 'lucide-react';
import { Button, Card, Chip, SupportedLocale } from '@/components/ui';
import { API_BASE, getFriendlyErrorMessage } from '@/lib/api';

interface GroundTruthMetric {
  total_checks: number;
  avg_diff_kg: number;
  avg_diff_pct: number;
  missing_price_count: number;
  missing_price_rate_pct: number;
  late_price_count: number;
  late_price_rate_pct: number;
  verified_match_rate_pct: number;
  mandi_breakdown: Array<{
    mandi_name: string;
    checks_count: number;
    avg_diff_pct: number;
    missing_count: number;
    late_count: number;
  }>;
}

interface GroundTruthCheckRow {
  id: number;
  mandi_id: number;
  mandi_name: string;
  crop_id: string;
  variety: string;
  grade: string;
  check_date: string;
  price_shown_kg: number | null;
  price_quoted_kg: number;
  difference_kg: number | null;
  difference_pct: number | null;
  is_price_missing: boolean;
  is_price_late: boolean;
  contact_name: string | null;
  contact_role: string;
  notes: string | null;
  created_at: string;
}

export const GroundTruthSection: React.FC<{ locale: SupportedLocale }> = ({ locale }) => {
  const [metrics, setMetrics] = useState<GroundTruthMetric>({
    total_checks: 0,
    avg_diff_kg: 0.0,
    avg_diff_pct: 0.0,
    missing_price_count: 0,
    missing_price_rate_pct: 0.0,
    late_price_count: 0,
    late_price_rate_pct: 0.0,
    verified_match_rate_pct: 0.0,
    mandi_breakdown: [],
  });

  const [checks, setChecks] = useState<GroundTruthCheckRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Form State
  const [formMandiId, setFormMandiId] = useState<number>(1);
  const [formPriceQuoted, setFormPriceQuoted] = useState<string>('24.5');
  const [formRole, setFormRole] = useState<string>('secretary');
  const [formContactName, setFormContactName] = useState<string>('Sri Rama Rao (Secretary)');
  const [formContactPhone, setFormContactPhone] = useState<string>('+919848011223');
  const [formVariety, setFormVariety] = useState<string>('Amruthapani');
  const [formNotes, setFormNotes] = useState<string>('Morning 08:30 auction call verification');

  const fetchAuditData = async () => {
    try {
      setLoading(true);
      const [repRes, listRes] = await Promise.all([
        fetch(`${API_BASE}/admin/ground-truth/report`),
        fetch(`${API_BASE}/admin/ground-truth?limit=50`),
      ]);

      if (repRes.ok) {
        const repData = await repRes.json();
        setMetrics(repData);
      }
      if (listRes.ok) {
        const listData = await listRes.json();
        setChecks(listData);
      }
    } catch (err) {
      console.warn('Ground truth backend fetch warning:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const handleRecordCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formPriceQuoted || isNaN(Number(formPriceQuoted))) return;

    try {
      setIsSubmitting(true);
      const payload = {
        mandi_id: Number(formMandiId),
        crop_id: 'banana',
        variety: formVariety,
        grade: 'FAQ',
        check_date: new Date().toISOString().split('T')[0],
        price_quoted_kg: parseFloat(formPriceQuoted),
        contact_role: formRole,
        contact_name: formContactName.trim() || null,
        contact_phone: formContactPhone.trim() || null,
        notes: formNotes.trim() || null,
      };

      const res = await fetch(`${API_BASE}/admin/ground-truth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setNotification('Phone audit check recorded successfully!');
        setTimeout(() => setNotification(null), 3000);
        await fetchAuditData();
      }
    } catch (err) {
      alert(getFriendlyErrorMessage(err, 'Save ground truth check'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadTemplate = () => {
    window.open(`${API_BASE}/admin/ground-truth/template.csv`, '_blank');
  };

  const handleUploadCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/admin/ground-truth/upload-csv`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setNotification(`Imported ${data.records_imported} audit checks from CSV.`);
        setTimeout(() => setNotification(null), 3500);
        await fetchAuditData();
      }
    } catch (err) {
      alert(getFriendlyErrorMessage(err, 'CSV upload'));
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner Alert */}
      {notification && (
        <div className="bg-deep-leaf text-white px-4 py-3 rounded-2xl flex items-center gap-2 shadow-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-semibold">{notification}</span>
        </div>
      )}

      {/* Accuracy & Ground-Truth KPI Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-border shadow-xs">
          <span className="text-xs text-muted font-bold block mb-1">Total Phone Audits</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-ink">{metrics.total_checks}</span>
          <span className="text-[11px] text-muted block mt-1">Direct secretary calls</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-border shadow-xs">
          <span className="text-xs text-muted font-bold block mb-1">Mean Discrepancy</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-extrabold text-amber">
              ₹{metrics.avg_diff_kg.toFixed(2)}
            </span>
            <span className="text-xs text-muted font-medium">/kg</span>
          </div>
          <span className="text-[11px] text-muted block mt-1">Avg difference: {metrics.avg_diff_pct.toFixed(1)}%</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-border shadow-xs">
          <span className="text-xs text-muted font-bold block mb-1">Verified Match Rate</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-deep-leaf">
            {metrics.verified_match_rate_pct.toFixed(0)}%
          </span>
          <span className="text-[11px] text-muted block mt-1">Within &plusmn;5% tolerance</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-border shadow-xs">
          <span className="text-xs text-muted font-bold block mb-1">Missing Price Rate</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-danger">
            {metrics.missing_price_rate_pct.toFixed(0)}%
          </span>
          <span className="text-[11px] text-muted block mt-1">{metrics.missing_price_count} calls without app price</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-border shadow-xs">
          <span className="text-xs text-muted font-bold block mb-1">Late Data Rate</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-amber-700">
            {metrics.late_price_rate_pct.toFixed(0)}%
          </span>
          <span className="text-[11px] text-muted block mt-1">&gt; 24h delay from auction</span>
        </div>
      </div>

      {/* Manual Check Form & CSV Tools */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Record Phone Audit Form */}
        <div className="lg:col-span-2 bg-white p-6 sm:p-7 rounded-3xl border border-border shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg sm:text-xl font-bold text-ink">
                Record Mandi Phone Audit
              </h2>
              <p className="text-xs text-muted">
                Test: &ldquo;If I call that mandi secretary, do they say the same price?&rdquo;
              </p>
            </div>
          </div>

          <form onSubmit={handleRecordCheck} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-muted mb-1">Mandi / Market Yard</label>
                <select
                  value={formMandiId}
                  onChange={(e) => setFormMandiId(Number(e.target.value))}
                  className="w-full p-2.5 rounded-xl border border-border text-sm text-ink focus:ring-2 focus:ring-deep-leaf"
                >
                  <option value={1}>Guntur Mandi (Guntur)</option>
                  <option value={2}>Tenali Mandi (Guntur)</option>
                  <option value={3}>Vijayawada Mandi (NTR)</option>
                  <option value={4}>Duggirala Mandi (Guntur)</option>
                  <option value={5}>Madanapalle Mandi (Annamayya)</option>
                  <option value={6}>Kurnool Mandi (Kurnool)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-muted mb-1">
                  Quoted Price on Phone (₹ / kg) <span className="text-danger">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={formPriceQuoted}
                  onChange={(e) => setFormPriceQuoted(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border text-sm text-ink font-bold focus:ring-2 focus:ring-deep-leaf"
                  placeholder="e.g. 24.50"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-muted mb-1">Contact Role</label>
                <select
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border text-sm text-ink focus:ring-2 focus:ring-deep-leaf"
                >
                  <option value="secretary">Mandi Secretary</option>
                  <option value="commission_agent">Commission Agent (Adathi)</option>
                  <option value="trader">Wholesale Trader</option>
                  <option value="farmer">Farmer at Yard</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-muted mb-1">Contact Name &amp; Phone</label>
                <input
                  type="text"
                  value={formContactName}
                  onChange={(e) => setFormContactName(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border text-sm text-ink focus:ring-2 focus:ring-deep-leaf"
                  placeholder="e.g. Rama Rao (+919848011223)"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-muted mb-1">Auditor Notes</label>
              <textarea
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                rows={2}
                className="w-full p-2.5 rounded-xl border border-border text-sm text-ink focus:ring-2 focus:ring-deep-leaf"
                placeholder="Details of call, quality comments, auction time..."
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="w-full py-3 font-bold"
              leftIcon={<PlusCircle className="w-5 h-5" />}
            >
              {isSubmitting ? 'Verifying & Saving...' : 'Record Phone Check & Compare App Price'}
            </Button>
          </form>
        </div>

        {/* CSV Tools & Template Card */}
        <div className="bg-white p-6 sm:p-7 rounded-3xl border border-border shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-amber/10 text-amber flex items-center justify-center">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-heading text-lg font-bold text-ink">
                  Bulk CSV Validation
                </h3>
                <p className="text-xs text-muted">
                  Import multi-market field caller surveys
                </p>
              </div>
            </div>

            <p className="text-xs text-muted leading-relaxed mb-6">
              Use our standardized CSV template to record daily morning call rounds with market secretaries across all districts.
            </p>

            <div className="space-y-3">
              <Button
                variant="secondary"
                onClick={handleDownloadTemplate}
                className="w-full justify-center"
                leftIcon={<Download className="w-4 h-4" />}
              >
                Download CSV Template
              </Button>

              <label className="w-full cursor-pointer flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border-2 border-dashed border-border text-sm font-semibold text-ink hover:border-deep-leaf hover:bg-cream/40 transition-colors">
                <Upload className="w-4 h-4 text-deep-leaf" />
                <span>Upload Completed CSV</span>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleUploadCsv}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border">
            <span className="text-[11px] text-muted block mb-1 font-semibold">Strict Rule B &amp; C Compliance</span>
            <span className="text-xs text-muted leading-relaxed block">
              Discrepancies exceeding 15% trigger automated quarantine alerts. All records preserve timestamp and caller provenance.
            </span>
          </div>
        </div>
      </div>

      {/* Audit Log Comparison Table */}
      <div className="bg-white rounded-3xl border border-border shadow-sm overflow-hidden">
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">
              Recent Phone Audits &amp; Discrepancy Log
            </h3>
            <p className="text-xs text-muted">
              Live ground-truth vs displayed price comparison
            </p>
          </div>
          <Button variant="secondary" size="md" onClick={fetchAuditData} leftIcon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>
        </div>

        {checks.length === 0 ? (
          <div className="p-12 text-center text-muted text-sm">
            No manual phone audits recorded yet. Conduct a call check above or upload a CSV.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-cream/60 border-b border-border text-xs text-muted uppercase font-bold">
                <tr>
                  <th className="py-3 px-4">Market Yard</th>
                  <th className="py-3 px-4">Check Date</th>
                  <th className="py-3 px-4">App Shown Price</th>
                  <th className="py-3 px-4">Phone Quoted</th>
                  <th className="py-3 px-4">Difference</th>
                  <th className="py-3 px-4">Audit Status</th>
                  <th className="py-3 px-4">Contact / Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {checks.map((c) => {
                  const isMatch = c.difference_pct !== null && Math.abs(c.difference_pct) <= 5.0;
                  const isHighDiff = c.difference_pct !== null && Math.abs(c.difference_pct) > 15.0;

                  return (
                    <tr key={c.id} className="hover:bg-cream/20 transition-colors">
                      <td className="py-3 px-4 font-bold text-ink">{c.mandi_name}</td>
                      <td className="py-3 px-4 text-muted text-xs">{c.check_date}</td>
                      <td className="py-3 px-4 font-medium">
                        {c.price_shown_kg !== null ? `₹${c.price_shown_kg.toFixed(2)}/kg` : (
                          <span className="text-danger text-xs font-bold">Missing</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-bold text-ink">₹{c.price_quoted_kg.toFixed(2)}/kg</td>
                      <td className="py-3 px-4">
                        {c.difference_kg !== null ? (
                          <span
                            className={`font-bold text-xs ${
                              isMatch ? 'text-deep-leaf' : isHighDiff ? 'text-danger' : 'text-amber-700'
                            }`}
                          >
                            {c.difference_kg > 0 ? `+₹${c.difference_kg.toFixed(2)}` : `₹${c.difference_kg.toFixed(2)}`} (
                            {c.difference_pct !== null && c.difference_pct > 0 ? `+${c.difference_pct.toFixed(1)}%` : `${c.difference_pct?.toFixed(1)}%`}
                            )
                          </span>
                        ) : (
                          <span className="text-muted text-xs">&mdash;</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {c.is_price_missing ? (
                          <Chip variant="danger" size="sm">
                            Price Missing
                          </Chip>
                        ) : c.is_price_late ? (
                          <Chip variant="accent" size="sm">
                            Late (&gt;24h)
                          </Chip>
                        ) : isMatch ? (
                          <Chip variant="primary" size="sm">
                            Verified Match
                          </Chip>
                        ) : isHighDiff ? (
                          <Chip variant="danger" size="sm">
                            High Discrepancy
                          </Chip>
                        ) : (
                          <Chip variant="accent" size="sm">
                            Slight Difference
                          </Chip>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-muted max-w-xs truncate">
                        {c.contact_name ? `${c.contact_name} (${c.contact_role}): ` : ''}
                        {c.notes || 'No notes'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
