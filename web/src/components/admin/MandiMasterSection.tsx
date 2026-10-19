'use client';

import React, { useState, useEffect } from 'react';
import { Card, Button, Chip } from '@/components/ui';
import { API_BASE, getFriendlyErrorMessage } from '@/lib/api';
import {
  MapPin,
  CheckCircle2,
  AlertTriangle,
  Layers,
  GitMerge,
  Search,
  ExternalLink,
  RefreshCw,
  Edit2,
  Check,
  X,
  ShieldAlert,
} from 'lucide-react';

interface MandiItem {
  id: number;
  name: string;
  canonical_name: string;
  district: string;
  state: string;
  mandal: string | null;
  mandal_lgd_code?: number | null;
  district_lgd_code?: number | null;
  state_lgd_code?: number | null;
  state_id: string | null;
  latitude: number | null;
  longitude: number | null;
  location_verified: boolean;
  geocode_confidence: number | null;
  geocode_source: string | null;
  needs_review: boolean;
  review_reason: string | null;
  is_active: boolean;
  merged_into_id: number | null;
}

interface HierarchyReport {
  total_mandis: number;
  total_verified_coordinates: number;
  total_mandal_mapped: number;
  total_needs_review: number;
  states_breakdown: Array<{
    state_name: string;
    total_mandis: number;
    verified_coordinates_count: number;
    mandal_mapped_count: number;
    needs_review_count: number;
  }>;
  review_queue: MandiItem[];
}

export function MandiMasterSection() {
  const [report, setReport] = useState<HierarchyReport | null>(null);
  const [mandis, setMandis] = useState<MandiItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'review' | 'all' | 'merge'>('review');

  // Coordinate fix modal
  const [editingMandi, setEditingMandi] = useState<MandiItem | null>(null);
  const [editLat, setEditLat] = useState<string>('');
  const [editLon, setEditLon] = useState<string>('');
  const [editMandal, setEditMandal] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');
  const [fixing, setFixing] = useState<boolean>(false);
  const [fixError, setFixError] = useState<string | null>(null);

  // Merge modal
  const [primaryId, setPrimaryId] = useState<number | ''>('');
  const [duplicateId, setDuplicateId] = useState<number | ''>('');
  const [mergeNotes, setMergeNotes] = useState<string>('Merging duplicate spelling/record');
  const [merging, setMerging] = useState<boolean>(false);
  const [mergeSuccessMsg, setMergeSuccessMsg] = useState<string | null>(null);

  // Search filter
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchHierarchyData = async () => {
    setLoading(true);
    try {
      const repRes = await fetch(`${API_BASE}/admin/mandis/hierarchy-report`);
      if (repRes.ok) {
        const repData = await repRes.json();
        setReport(repData);
      }

      const mandisRes = await fetch(`${API_BASE}/admin/mandis`);
      if (mandisRes.ok) {
        const mandisData = await mandisRes.json();
        setMandis(mandisData);
      }
    } catch (e) {
      console.error('Error fetching mandi master data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHierarchyData();
  }, []);

  const handleOpenEdit = (m: MandiItem) => {
    setEditingMandi(m);
    setEditLat(m.latitude ? m.latitude.toString() : '');
    setEditLon(m.longitude ? m.longitude.toString() : '');
    setEditMandal(m.mandal || '');
    setEditNotes('Verified via OpenStreetMap & mandi phone confirmation');
    setFixError(null);
  };

  const handleSaveCoordinates = async () => {
    if (!editingMandi) return;
    const lat = parseFloat(editLat);
    const lon = parseFloat(editLon);
    if (isNaN(lat) || isNaN(lon)) {
      setFixError('Please enter valid numeric latitude and longitude coordinates.');
      return;
    }

    setFixing(true);
    setFixError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/mandis/${editingMandi.id}/verify-coordinates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lon,
          mandal_name: editMandal.trim() || undefined,
          notes: editNotes,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setFixError(err.detail || 'Failed to update coordinates.');
      } else {
        setEditingMandi(null);
        await fetchHierarchyData();
      }
    } catch (e) {
      setFixError(getFriendlyErrorMessage(e, 'Update coordinates'));
    } finally {
      setFixing(false);
    }
  };

  const handleMergeMandis = async () => {
    if (!primaryId || !duplicateId) return;
    setMerging(true);
    setMergeSuccessMsg(null);
    try {
      const res = await fetch(`${API_BASE}/admin/mandis/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_mandi_id: Number(primaryId),
          duplicate_mandi_id: Number(duplicateId),
          notes: mergeNotes,
        }),
      });

      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setMergeSuccessMsg(data.message || 'Mandi merged successfully.');
        setPrimaryId('');
        setDuplicateId('');
        await fetchHierarchyData();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Merge failed.');
      }
    } catch (e) {
      alert(getFriendlyErrorMessage(e, 'Merge mandis'));
    } finally {
      setMerging(false);
    }
  };

  const filteredMandis = mandis.filter(
    (m) =>
      m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.canonical_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.district.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-600 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Mandis</span>
            <Layers className="w-5 h-5 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-gray-900 mt-2">{report?.total_mandis || 0}</div>
          <p className="text-xs text-gray-500 mt-1">Normalized across government sources</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-green-600 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Location Verified</span>
            <MapPin className="w-5 h-5 text-green-600" />
          </div>
          <div className="text-2xl font-bold text-green-700 mt-2">{report?.total_verified_coordinates || 0}</div>
          <p className="text-xs text-green-600 mt-1">Eligible for distance queries</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-purple-600 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">LGD Mandal Mapped</span>
            <CheckCircle2 className="w-5 h-5 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-purple-700 mt-2">{report?.total_mandal_mapped || 0}</div>
          <p className="text-xs text-purple-600 mt-1">Mapped to sub-district LGD</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Manual Review</span>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-700 mt-2">{report?.total_needs_review || 0}</div>
          <p className="text-xs text-amber-600 mt-1">Unverified or low confidence</p>
        </Card>
      </div>

      {/* State-wise Breakdown */}
      {report?.states_breakdown && report.states_breakdown.length > 0 && (
        <Card className="p-4 bg-slate-50 border border-slate-200">
          <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" /> State-wise Mandi Master Hierarchy
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {report.states_breakdown.map((s) => (
              <div key={s.state_name} className="bg-white p-3 rounded-lg border border-gray-200 text-xs">
                <div className="font-bold text-gray-900 text-sm mb-1">{s.state_name}</div>
                <div className="text-gray-600 flex justify-between py-0.5">
                  <span>Total Markets:</span>
                  <span className="font-semibold text-gray-900">{s.total_mandis}</span>
                </div>
                <div className="text-gray-600 flex justify-between py-0.5">
                  <span>Verified GPS:</span>
                  <span className="font-semibold text-green-700">{s.verified_coordinates_count}</span>
                </div>
                <div className="text-gray-600 flex justify-between py-0.5">
                  <span>LGD Mandals:</span>
                  <span className="font-semibold text-purple-700">{s.mandal_mapped_count}</span>
                </div>
                <div className="text-gray-600 flex justify-between py-0.5">
                  <span>Need Review:</span>
                  <span className={`font-semibold ${s.needs_review_count > 0 ? 'text-amber-600' : 'text-gray-400'}`}>
                    {s.needs_review_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-3 border-b border-gray-200 pb-2">
        <button
          onClick={() => setActiveTab('review')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'review'
              ? 'bg-amber-100 text-amber-900 border border-amber-300 font-semibold'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-amber-600" />
          Review Queue ({report?.total_needs_review || 0})
        </button>
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'all'
              ? 'bg-blue-100 text-blue-900 border border-blue-300 font-semibold'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Layers className="w-4 h-4 text-blue-600" />
          All Master Mandis ({mandis.length})
        </button>
        <button
          onClick={() => setActiveTab('merge')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors ${
            activeTab === 'merge'
              ? 'bg-purple-100 text-purple-900 border border-purple-300 font-semibold'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <GitMerge className="w-4 h-4 text-purple-600" />
          Duplicate Merge Assistant
        </button>
      </div>

      {/* TAB 1: REVIEW QUEUE */}
      {activeTab === 'review' && (
        <Card className="p-5 bg-white border border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900">Mandis Needing Manual Review</h3>
              <p className="text-xs text-gray-500">
                Mandis lacking verified GPS coordinates, low-confidence Nominatim geocoding, or duplicate flags.
              </p>
            </div>
            <Button variant="secondary" onClick={fetchHierarchyData} className="flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </Button>
          </div>

          {report?.review_queue && report.review_queue.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 text-gray-600 uppercase font-semibold border-b">
                  <tr>
                    <th className="py-2.5 px-3">ID</th>
                    <th className="py-2.5 px-3">Raw Market Name</th>
                    <th className="py-2.5 px-3">Canonical Name</th>
                    <th className="py-2.5 px-3">District / State</th>
                    <th className="py-2.5 px-3">Coordinates</th>
                    <th className="py-2.5 px-3">Review Reason</th>
                    <th className="py-2.5 px-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {report.review_queue.map((m) => (
                    <tr key={m.id} className="hover:bg-amber-50/40">
                      <td className="py-2.5 px-3 font-mono text-gray-600">#{m.id}</td>
                      <td className="py-2.5 px-3 font-medium text-gray-900">{m.name}</td>
                      <td className="py-2.5 px-3 text-blue-700 font-semibold">{m.canonical_name || '—'}</td>
                      <td className="py-2.5 px-3 text-gray-700">
                        {m.district}, {m.state}
                      </td>
                      <td className="py-2.5 px-3">
                        {m.latitude && m.longitude ? (
                          <span className="font-mono text-gray-700">
                            {m.latitude.toFixed(4)}, {m.longitude.toFixed(4)}
                          </span>
                        ) : (
                          <span className="text-red-500 font-medium">Missing GPS</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-amber-800 bg-amber-100 px-2 py-0.5 rounded text-[11px]">
                          {m.review_reason || 'Unverified Location'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <Button
                          variant="secondary"
                          onClick={() => handleOpenEdit(m)}
                          className="text-xs flex items-center gap-1 border-blue-600 text-blue-600 hover:bg-blue-50"
                        >
                          <Edit2 className="w-3 h-3" /> Fix Coordinates
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-10 bg-green-50 rounded-lg border border-green-200">
              <CheckCircle2 className="w-8 h-8 text-green-600 mx-auto mb-2" />
              <p className="text-sm font-semibold text-green-800">All mandis verified!</p>
              <p className="text-xs text-green-600 mt-1">
                Zero mandis pending manual geocoding review in the master database.
              </p>
            </div>
          )}
        </Card>
      )}

      {/* TAB 2: ALL MANDIS BROWSER */}
      {activeTab === 'all' && (
        <Card className="p-5 bg-white border border-gray-200">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900">Mandi Master Registry</h3>
              <p className="text-xs text-gray-500">
                Canonical market records, LGD sub-district codes, and verified GPS coordinates.
              </p>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search mandi, district..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-600 uppercase font-semibold border-b">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">Canonical Name</th>
                  <th className="py-2.5 px-3">Raw Name</th>
                  <th className="py-2.5 px-3">District</th>
                  <th className="py-2.5 px-3">Mandal (LGD)</th>
                  <th className="py-2.5 px-3">GPS Coordinates</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredMandis.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="py-2 px-3 font-mono text-gray-600">#{m.id}</td>
                    <td className="py-2 px-3 font-semibold text-gray-900">{m.canonical_name || m.name}</td>
                    <td className="py-2 px-3 text-gray-500 italic">{m.name}</td>
                    <td className="py-2 px-3 text-gray-700">{m.district}</td>
                    <td className="py-2 px-3">
                      {m.mandal ? (
                        <span className="text-purple-800 bg-purple-50 px-2 py-0.5 rounded text-[11px] font-medium">
                          {m.mandal} {m.mandal_lgd_code && `(${m.mandal_lgd_code})`}
                        </span>
                      ) : (
                        <span className="text-gray-400">Unmapped</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      {m.latitude && m.longitude ? (
                        <a
                          href={`https://www.openstreetmap.org/?mlat=${m.latitude}&mlon=${m.longitude}#map=15/${m.latitude}/${m.longitude}`}
                          target="_blank"
                          rel="noreferrer"
                          className="font-mono text-blue-600 hover:underline flex items-center gap-1"
                        >
                          {m.latitude.toFixed(4)}, {m.longitude.toFixed(4)}
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      ) : (
                        <span className="text-red-500">None</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      {m.location_verified ? (
                        <span className="inline-flex items-center gap-1 text-green-700 bg-green-50 px-2 py-0.5 rounded font-medium">
                          <Check className="w-3 h-3" /> Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-0.5 rounded font-medium">
                          <AlertTriangle className="w-3 h-3" /> Unverified
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      <button
                        onClick={() => handleOpenEdit(m)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 3: DUPLICATE MERGE ASSISTANT */}
      {activeTab === 'merge' && (
        <Card className="p-5 bg-white border border-gray-200">
          <div className="mb-4">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <GitMerge className="w-5 h-5 text-purple-600" />
              Duplicate Mandi Merge Assistant
            </h3>
            <p className="text-xs text-gray-500">
              Select a duplicate market to merge into a primary master mandi. All historical prices and phone checks will
              be re-pointed, the duplicate deactivated, and an immutable audit trail logged.
            </p>
          </div>

          {mergeSuccessMsg && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
              <span>{mergeSuccessMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Primary Master Mandi (To Keep Active)
              </label>
              <select
                value={primaryId}
                onChange={(e) => setPrimaryId(e.target.value ? Number(e.target.value) : '')}
                className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Primary Mandi...</option>
                {mandis
                  .filter((m) => m.is_active)
                  .map((m) => (
                    <option key={m.id} value={m.id}>
                      #{m.id} {m.canonical_name || m.name} ({m.district}, {m.state})
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Duplicate Mandi (To Merge & Deactivate)
              </label>
              <select
                value={duplicateId}
                onChange={(e) => setDuplicateId(e.target.value ? Number(e.target.value) : '')}
                className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Duplicate Mandi...</option>
                {mandis
                  .filter((m) => m.id !== primaryId)
                  .map((m) => (
                    <option key={m.id} value={m.id}>
                      #{m.id} {m.name} ({m.district}, {m.state})
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-gray-700 mb-1">Audit Log Note / Rationale</label>
            <input
              type="text"
              value={mergeNotes}
              onChange={(e) => setMergeNotes(e.target.value)}
              className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Spelling variation merged into canonical APMC"
            />
          </div>

          <Button
            onClick={handleMergeMandis}
            disabled={!primaryId || !duplicateId || merging}
            className="w-full md:w-auto bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold px-4 py-2"
          >
            {merging ? 'Merging Records...' : 'Execute Merge & Audit Log'}
          </Button>
        </Card>
      )}

      {/* COORDINATE EDIT MODAL */}
      {editingMandi && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-gray-200">
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-blue-600" /> Verify Mandi Coordinates
              </h4>
              <button onClick={() => setEditingMandi(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-gray-600 mb-4">
              Fix and verify coordinates for <strong>{editingMandi.name}</strong> ({editingMandi.district},{' '}
              {editingMandi.state}). Coordinates will be verified against the state&apos;s geographic boundary.
            </p>

            {fixError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{fixError}</span>
              </div>
            )}

            <div className="space-y-3 mb-5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Latitude (WGS84)</label>
                <input
                  type="text"
                  value={editLat}
                  onChange={(e) => setEditLat(e.target.value)}
                  placeholder="e.g. 16.3067"
                  className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Longitude (WGS84)</label>
                <input
                  type="text"
                  value={editLon}
                  onChange={(e) => setEditLon(e.target.value)}
                  placeholder="e.g. 80.4365"
                  className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Mandal Name (Optional)</label>
                <input
                  type="text"
                  value={editMandal}
                  onChange={(e) => setEditMandal(e.target.value)}
                  placeholder="Leave blank to auto-match nearest LGD mandal"
                  className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Verification Notes</label>
                <input
                  type="text"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  className="w-full p-2 text-xs rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditingMandi(null)} disabled={fixing}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSaveCoordinates}
                disabled={fixing}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {fixing ? 'Verifying...' : 'Save & Verify'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
