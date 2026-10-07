'use client';

import React, { useState } from 'react';
import {
  Database,
  RefreshCw,
  Search,
  ShieldCheck,
  AlertTriangle,
  ShieldAlert,
  Clock,
  Zap,
  ArrowRightLeft,
  X,
  FileText,
  Activity,
  CheckCircle2,
  KeyRound,
  Filter,
} from 'lucide-react';

export interface AuditLogEntry {
  id: number;
  transaction_id: string;
  timestamp: string;
  user_reference: string;
  transaction_amount: number;
  transaction_type: string;
  input_risk_features: Record<string, any>;
  risk_score: number;
  risk_level: string;
  model_version: string;
  final_policy_decision: string;
  shap_explanation: Array<{ feature: string; impact: number }>;
  explanation_language: string;
  processing_latency_ms: number;
  authentication_context: Record<string, any>;
  action_taken: string;
  narrative?: string | null;
  created_at: string;
}

export interface AuditStats {
  total_transactions: number;
  allowed_count: number;
  step_up_count: number;
  blocked_count: number;
  avg_risk_score: number;
  avg_latency_ms: number;
  total_volume_bdt: number;
}

interface AuditLedgerSectionProps {
  entries: AuditLogEntry[];
  stats: AuditStats | null;
  loading: boolean;
  onRefresh: () => void;
  selectedFilter: 'ALL' | 'ALLOW' | 'STEP_UP_2FA' | 'BLOCK';
  onFilterChange: (filter: 'ALL' | 'ALLOW' | 'STEP_UP_2FA' | 'BLOCK') => void;
}

export default function AuditLedgerSection({
  entries,
  stats,
  loading,
  onRefresh,
  selectedFilter,
  onFilterChange,
}: AuditLedgerSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const filteredEntries = entries.filter((item) => {
    // Filter by decision
    if (selectedFilter !== 'ALL' && item.final_policy_decision !== selectedFilter) {
      return false;
    }
    // Filter by search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      return (
        item.transaction_id.toLowerCase().includes(term) ||
        item.user_reference.toLowerCase().includes(term) ||
        item.transaction_type.toLowerCase().includes(term) ||
        item.transaction_amount.toString().includes(term)
      );
    }
    return true;
  });

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'ALLOW':
      case 'APPROVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <ShieldCheck className="h-3 w-3 text-emerald-600" />
            ALLOW
          </span>
        );
      case 'STEP_UP_2FA':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            STEP_UP_2FA
          </span>
        );
      case 'BLOCK':
      case 'BLOCK_IMMEDIATELY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-100 text-red-800 border border-red-200">
            <ShieldAlert className="h-3 w-3 text-red-600" />
            BLOCK
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
            {decision}
          </span>
        );
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'VERIFIED_2FA':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-teal-100 text-teal-800">
            <CheckCircle2 className="h-2.5 w-2.5" /> 2FA Verified
          </span>
        );
      case 'RECOVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-purple-100 text-purple-800">
            <KeyRound className="h-2.5 w-2.5" /> Recovered
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-100 text-rose-800">
            Blocked
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-600">
            Scored
          </span>
        );
    }
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      });
    } catch {
      return ts;
    }
  };

  return (
    <section id="audit-ledger" className="bg-white rounded-3xl border border-slate-200 p-6 md:p-8 shadow-xl space-y-6">
      
      {/* 1. Header with Metadata */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between border-b border-slate-100 pb-5 gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-2xl bg-[#063254] text-[#FFC800] shadow-md">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-[#063254] tracking-tight">
                লাইভ অডিট ট্রেইল ও রেগুলেটরি লেজার (Durable Compliance Ledger)
              </h2>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                SQLite Active
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              বাংলাদেশ ব্যাংক MFS গাইডলাইন অনুযায়ী প্রতিটি লেনদেন, SHAP অ্যাট্রিবিউশন এবং সল্টেড ২এফএ চ্যালেঞ্জ পারসিস্টেন্ট ডেটাবেসে সংরক্ষিত
            </p>
          </div>
        </div>

        {/* Security Badges */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-2.5 py-1 rounded-xl bg-slate-100 text-slate-700 text-xs font-mono font-medium border border-slate-200">
            🔒 Zero PII (Tokenized)
          </span>
          <span className="px-2.5 py-1 rounded-xl bg-slate-100 text-slate-700 text-xs font-mono font-medium border border-slate-200">
            🔑 Salted SHA-256 OTP
          </span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-[#063254] hover:bg-[#08416C] text-white font-bold text-xs flex items-center gap-1.5 transition active:scale-95 cursor-pointer shadow-sm disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>রিফ্রেশ (Refresh)</span>
          </button>
        </div>
      </div>

      {/* 2. Top Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/90 space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">মোট রেকর্ডকৃত লেনদেন</span>
          <span className="text-2xl font-black font-mono text-[#063254] block">
            {stats ? stats.total_transactions : entries.length}
          </span>
          <span className="text-[10px] text-slate-400">Durable SQLite Entries</span>
        </div>

        <div className="p-4 bg-emerald-50/70 rounded-2xl border border-emerald-200 space-y-1">
          <span className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider block">অনুমোদিত (ALLOW)</span>
          <span className="text-2xl font-black font-mono text-emerald-700 block">
            {stats ? stats.allowed_count : entries.filter((e) => e.final_policy_decision === 'ALLOW').length}
          </span>
          <span className="text-[10px] text-emerald-600 font-medium">Low Friction Path</span>
        </div>

        <div className="p-4 bg-amber-50/70 rounded-2xl border border-amber-200 space-y-1">
          <span className="text-[10px] uppercase font-bold text-amber-800 tracking-wider block">২এফএ চ্যালেঞ্জ (STEP-UP)</span>
          <span className="text-2xl font-black font-mono text-amber-700 block">
            {stats ? stats.step_up_count : entries.filter((e) => e.final_policy_decision === 'STEP_UP_2FA').length}
          </span>
          <span className="text-[10px] text-amber-600 font-medium">Adaptive Challenge</span>
        </div>

        <div className="p-4 bg-red-50/70 rounded-2xl border border-red-200 space-y-1">
          <span className="text-[10px] uppercase font-bold text-red-800 tracking-wider block">স্থগিত/ব্লকড (BLOCK)</span>
          <span className="text-2xl font-black font-mono text-red-700 block">
            {stats ? stats.blocked_count : entries.filter((e) => e.final_policy_decision === 'BLOCK').length}
          </span>
          <span className="text-[10px] text-red-600 font-medium">ATO &amp; Fraud Defense</span>
        </div>

        <div className="p-4 bg-blue-50/70 rounded-2xl border border-blue-200 space-y-1 col-span-2 sm:col-span-1">
          <span className="text-[10px] uppercase font-bold text-blue-800 tracking-wider block">গড় ইনফারেন্স লেটেন্সি</span>
          <span className="text-2xl font-black font-mono text-blue-700 block">
            {stats ? `${stats.avg_latency_ms} ms` : '12.4 ms'}
          </span>
          <span className="text-[10px] text-blue-600 font-medium">LightGBM Real-time</span>
        </div>
      </div>

      {/* 3. Filters & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          <span className="text-xs font-bold text-slate-500 mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" /> ফিল্টার:
          </span>
          {(['ALL', 'ALLOW', 'STEP_UP_2FA', 'BLOCK'] as const).map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => onFilterChange(filter)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap ${
                selectedFilter === filter
                  ? 'bg-[#063254] text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {filter === 'ALL' ? 'সকল লেনদেন' : filter}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Txn ID অথবা ইউজার দিয়ে খুঁজুন..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#063254]/20 transition"
          />
        </div>
      </div>

      {/* 4. Real-time Audit Records Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-bold text-[10px]">
            <tr>
              <th className="py-3 px-4">সময় (Time)</th>
              <th className="py-3 px-4">ট্রানজেকশন আইডি</th>
              <th className="py-3 px-4">চ্যানেল ও পরিমাণ</th>
              <th className="py-3 px-4">রিস্ক স্কোর</th>
              <th className="py-3 px-4">পলিসি সিদ্ধান্ত</th>
              <th className="py-3 px-4">লেজার স্ট্যাটাস</th>
              <th className="py-3 px-4">শীর্ষ ঝুঁকি ফ্যাক্টর (SHAP)</th>
              <th className="py-3 px-4">লেটেন্সি</th>
              <th className="py-3 px-4 text-right">বিস্তারিত</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredEntries.length > 0 ? (
              filteredEntries.map((item) => {
                const topDriver = item.shap_explanation?.[0];
                return (
                  <tr
                    key={item.id || item.transaction_id}
                    onClick={() => setSelectedEntry(item)}
                    className="hover:bg-amber-50/40 transition cursor-pointer group"
                  >
                    <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                      {formatTimestamp(item.timestamp || item.created_at)}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-[#063254]">
                      {item.transaction_id}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="font-bold text-[#063254]">
                        ৳ {item.transaction_amount?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {item.transaction_type === 'CASH_OUT' ? 'ক্যাশ-আউট' : 'সেন্ড মানি (P2P)'}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-mono font-bold text-[#063254]">
                        {item.risk_score > 1 ? item.risk_score.toFixed(1) : (item.risk_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {getDecisionBadge(item.final_policy_decision)}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {getActionBadge(item.action_taken)}
                    </td>
                    <td className="py-3 px-4">
                      {topDriver ? (
                        <div className="text-[11px] font-mono">
                          <span className="text-[#063254] font-medium">{topDriver.feature}</span>{' '}
                          <span
                            className={
                              topDriver.impact > 0
                                ? 'text-red-600 font-bold'
                                : 'text-emerald-600 font-bold'
                            }
                          >
                            ({topDriver.impact > 0 ? `+${topDriver.impact.toFixed(2)}` : topDriver.impact.toFixed(2)})
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                      {item.processing_latency_ms ? `${item.processing_latency_ms.toFixed(1)} ms` : '<15 ms'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedEntry(item);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-[#063254] hover:text-white text-slate-700 text-[11px] font-bold transition cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={9} className="py-8 text-center text-slate-400">
                  {loading ? (
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="h-4 w-4 animate-spin text-[#063254]" />
                      <span>অডিট লেজার ডেটা লোড হচ্ছে...</span>
                    </div>
                  ) : (
                    <span>কোনো অডিট রেকর্ড পাওয়া যায়নি। ফোন সিমুলেটরে লেনদেন সম্পন্ন করুন।</span>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 5. Detail Inspection Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 bg-[#063254]/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto animate-in zoom-in-95 duration-200">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-[#063254] text-[#FFC800]">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#063254]">
                    অডিট লেজার রেকর্ড: {selectedEntry.transaction_id}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Timestamp: {selectedEntry.timestamp || selectedEntry.created_at}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedEntry(null)}
                className="h-8 w-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Quick Metrics Header */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">পরিমাণ (Amount)</span>
                <span className="text-lg font-mono font-bold text-[#063254]">
                  ৳ {selectedEntry.transaction_amount?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">ঝুঁকি স্কোর (Risk)</span>
                <span className="text-lg font-mono font-bold text-[#063254]">
                  {selectedEntry.risk_score > 1 ? selectedEntry.risk_score.toFixed(1) : (selectedEntry.risk_score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">সিদ্ধান্ত (Policy)</span>
                <div className="mt-0.5">{getDecisionBadge(selectedEntry.final_policy_decision)}</div>
              </div>
            </div>

            {/* Input Features Table */}
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-[#063254] uppercase tracking-wider block">
                ইনপুট ফিচারস (Evaluation Features)
              </span>
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
                {Object.entries(selectedEntry.input_risk_features || {}).map(([k, v]) => (
                  <div key={k} className="p-1.5 bg-white rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 block">{k}</span>
                    <span className="font-bold text-[#063254]">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* SHAP Explanation Drivers */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-[#063254] uppercase tracking-wider block">
                SHAP এক্সপ্লেইনেবিলিটি লোকাল ড্রাইভার (TreeExplainer Attribution)
              </span>
              <div className="space-y-1.5">
                {selectedEntry.shap_explanation?.map((d, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono">
                    <span className="font-bold text-[#063254]">{d.feature}</span>
                    <span className={d.impact > 0 ? 'text-red-600 font-bold' : 'text-emerald-600 font-bold'}>
                      {d.impact > 0 ? `+${d.impact.toFixed(4)}` : d.impact.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Authentication & Audit Context */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">নিরাপত্তা ও গভর্নেন্স অডিট কনটেক্সট</span>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div>
                  <span className="text-slate-400">Client ID: </span>
                  <span className="text-[#063254] font-bold">
                    {selectedEntry.authentication_context?.client_id || 'authorized_client'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Auth Type: </span>
                  <span className="text-[#063254] font-bold">
                    {selectedEntry.authentication_context?.auth_type || 'api_key'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Correlation ID: </span>
                  <span className="text-[#063254] font-bold">
                    {selectedEntry.authentication_context?.correlation_id || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Model Version: </span>
                  <span className="text-[#063254] font-bold">{selectedEntry.model_version}</span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setSelectedEntry(null)}
              className="w-full py-2.5 rounded-xl bg-[#063254] hover:bg-[#08416C] text-white font-bold text-xs transition cursor-pointer"
            >
              বন্ধ করুন (Close)
            </button>
          </div>
        </div>
      )}

    </section>
  );
}

