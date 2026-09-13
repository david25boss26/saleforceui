import React, { useState } from "react";
import {
  Database,
  Play,
  FileSpreadsheet,
  Download,
  FileText,
  Key,
  ChevronDown,
  ChevronUp,
  Search,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Table as TableIcon,
  Code
} from "lucide-react";
import apiService from "../services/api";
import type { SOQLQueryResponse } from "../types";

const SAMPLE_QUERIES = [
  {
    name: "OCE Invoices with Nested Meetings & Members",
    soql: `SELECT id, 
       OCE__meeting__r.recordtype.name, 
       OCE__MeetingMember__r.OCE__Type__c, 
       OCE__Meeting__r.OCE__OrganizingCountry__c, 
       OCE__MeetingMember__r.OCE__Meeting__r.OCE__Status__c, 
       OCE__PaymentStatus__c, 
       OCE__InvoiceStatus__c
FROM OCE__Invoice__c`
  },
  {
    name: "Accounts Master List",
    soql: `SELECT Id, Name, AccountNumber, Type, Industry, AnnualRevenue FROM Account WHERE IsDeleted = false LIMIT 100`
  },
  {
    name: "Product2 Catalog",
    soql: `SELECT Id, Name, ProductCode, Family, IsActive FROM Product2 WHERE IsActive = true LIMIT 100`
  },
  {
    name: "Budgets Master List",
    soql: `SELECT Id, Name, Budget_Code__c, Allocated_Amount__c FROM Budget__c WHERE IsDeleted = false LIMIT 100`
  },
  {
    name: "Checklists Reference",
    soql: `SELECT Id, Name, Checklist_Code__c, Status__c FROM Checklist__c WHERE IsDeleted = false LIMIT 100`
  }
];

export default function SalesforceQueryExplorer() {
  const [soqlQuery, setSoqlQuery] = useState(SAMPLE_QUERIES[0].soql);
  const [showAuthOverrides, setShowAuthOverrides] = useState(false);
  
  // Auth Overrides
  const [sessionId, setSessionId] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [securityToken, setSecurityToken] = useState("");
  const [domain, setDomain] = useState("novartis-events-oce--qa.sandbox.my");
  
  // Results & UI States
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<"excel" | "csv" | null>(null);
  const [queryResult, setQueryResult] = useState<SOQLQueryResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState<"table" | "json">("table");
  const [lastExportUrl, setLastExportUrl] = useState<string | null>(null);
  const [lastExportFile, setLastExportFile] = useState<string | null>(null);

  const handleRunQuery = async () => {
    if (!soqlQuery.trim()) {
      setErrorMsg("Please enter a SOQL query.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setLastExportUrl(null);

    try {
      const payload: any = {
        query: soqlQuery,
        limit: 500
      };
      if (sessionId) payload.session_id = sessionId;
      if (username) payload.username = username;
      if (password) payload.password = password;
      if (securityToken) payload.security_token = securityToken;
      if (domain) payload.domain = domain;

      const res = await apiService.executeSOQLQuery(payload);
      setQueryResult(res);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to execute Salesforce query";
      setErrorMsg(msg);
      setQueryResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: "excel" | "csv") => {
    if (!soqlQuery.trim()) {
      setErrorMsg("Please enter a SOQL query.");
      return;
    }

    setExporting(format);
    setErrorMsg(null);

    try {
      const payload: any = {
        query: soqlQuery,
        export_format: format,
        sheet_name: "Salesforce Data",
        output_filename: `salesforce_export_${Date.now()}.${format === "excel" ? "xlsx" : "csv"}`
      };
      if (sessionId) payload.session_id = sessionId;
      if (username) payload.username = username;
      if (password) payload.password = password;
      if (securityToken) payload.security_token = securityToken;
      if (domain) payload.domain = domain;

      const res = await apiService.exportSOQLQuery(payload);
      
      const downloadUrl = apiService.getExportDownloadUrl(res.filepath);
      setLastExportUrl(downloadUrl);
      setLastExportFile(res.filename);

      // Trigger instant browser download
      window.open(downloadUrl, "_blank");
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Export failed";
      setErrorMsg(msg);
    } finally {
      setExporting(null);
    }
  };

  // Filter rows based on search term
  const filteredData = React.useMemo(() => {
    if (!queryResult || !queryResult.data) return [];
    if (!searchTerm.trim()) return queryResult.data;

    const term = searchTerm.toLowerCase();
    return queryResult.data.filter((row) =>
      Object.values(row).some((val) =>
        String(val ?? "").toLowerCase().includes(term)
      )
    );
  }, [queryResult, searchTerm]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Database className="h-6 w-6 text-sky-400" />
            Salesforce SOQL Query & Data Importer
          </h2>
          <p className="text-sm text-slate-400">
            Execute custom SOQL queries, automatically flatten parent-child relationships, preview data, and export directly to Excel or CSV.
          </p>
        </div>

        {/* Template Queries Quick Picker */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium hidden sm:inline">Templates:</span>
          <select
            className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500"
            onChange={(e) => {
              const selected = SAMPLE_QUERIES.find((q) => q.name === e.target.value);
              if (selected) setSoqlQuery(selected.soql);
            }}
            defaultValue={SAMPLE_QUERIES[0].name}
          >
            {SAMPLE_QUERIES.map((q) => (
              <option key={q.name} value={q.name}>
                {q.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Query Editor Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="bg-slate-950/60 border-b border-slate-800 px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Sparkles className="h-4 w-4 text-sky-400" />
            <span>SOQL Query Editor</span>
          </div>

          <button
            onClick={() => setShowAuthOverrides(!showAuthOverrides)}
            className="text-xs text-slate-400 hover:text-sky-400 flex items-center gap-1.5 transition"
          >
            <Key className="h-3.5 w-3.5 text-amber-400" />
            <span>Connection Credentials</span>
            {showAuthOverrides ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Collapsible Auth Overrides */}
        {showAuthOverrides && (
          <div className="bg-slate-950/90 border-b border-slate-800 p-5 space-y-3 text-xs animate-fadeIn">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Domain / Environment</label>
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="novartis-events-oce--qa.sandbox.my"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:border-sky-500 focus:outline-none font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Salesforce Username (Optional)</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="user@novartis.com.oceqa"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:border-sky-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Salesforce Password (Optional)</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:border-sky-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Security Token (Optional)</label>
                <input
                  type="password"
                  value={securityToken}
                  onChange={(e) => setSecurityToken(e.target.value)}
                  placeholder="Security Token"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:border-sky-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Direct Session ID / Browser Token Alternative */}
            <div className="pt-2 border-t border-slate-850">
              <label className="block text-sky-400 mb-1 font-medium flex items-center justify-between">
                <span>Direct Session ID / Access Token (Bypasses Password & Security Token)</span>
                <span className="text-[10px] text-slate-500 font-normal">Extract from Browser DevTools / Salesforce Inspector</span>
              </label>
              <input
                type="password"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder="Paste session ID e.g. 00D... or OAuth access token"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sky-300 focus:border-sky-500 focus:outline-none font-mono text-xs"
              />
            </div>
          </div>
        )}

        {/* Textarea SOQL Query */}
        <div className="p-5 space-y-4">
          <textarea
            value={soqlQuery}
            onChange={(e) => setSoqlQuery(e.target.value)}
            rows={7}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-sm text-sky-300 focus:outline-none focus:border-sky-500 shadow-inner"
            placeholder="SELECT Id, Name FROM Account"
          />

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2">
              <button
                onClick={handleRunQuery}
                disabled={loading}
                className="bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition flex items-center gap-2 shadow-lg shadow-sky-600/20"
              >
                <Play className={`h-4 w-4 ${loading ? "animate-spin" : "fill-current"}`} />
                <span>{loading ? "Executing Query..." : "Execute & Preview"}</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExport("excel")}
                disabled={exporting !== null}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-semibold px-4 py-2.5 rounded-lg text-sm transition flex items-center gap-2 shadow-lg shadow-emerald-600/20"
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span>{exporting === "excel" ? "Generating Excel..." : "Export to Excel (.xlsx)"}</span>
              </button>

              <button
                onClick={() => handleExport("csv")}
                disabled={exporting !== null}
                className="bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 text-slate-200 font-semibold px-4 py-2.5 rounded-lg text-sm transition flex items-center gap-2 border border-slate-700"
              >
                <FileText className="h-4 w-4 text-sky-400" />
                <span>{exporting === "csv" ? "Generating CSV..." : "Export to CSV"}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Export Download Success Banner */}
      {lastExportUrl && (
        <div className="bg-emerald-950/40 border border-emerald-800/50 rounded-xl p-4 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-300">File Exported Successfully!</p>
              <p className="text-xs text-slate-400">{lastExportFile}</p>
            </div>
          </div>
          <a
            href={lastExportUrl}
            target="_blank"
            rel="noreferrer"
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download Again</span>
          </a>
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-900/50 rounded-xl p-4 flex items-start gap-3 animate-fadeIn">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-rose-300">Salesforce Query Execution Error</p>
            <p className="text-xs text-rose-200/80 font-mono mt-1 break-all">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Query Results Section */}
      {queryResult && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl space-y-0">
          {/* Results Summary Bar */}
          <div className="bg-slate-950/80 border-b border-slate-800 px-5 py-3 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Total Rows:</span>
                <span className="font-bold text-sky-400 bg-sky-950/50 border border-sky-800 px-2 py-0.5 rounded">
                  {queryResult.total_records}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Columns:</span>
                <span className="font-bold text-emerald-400 bg-emerald-950/50 border border-emerald-800 px-2 py-0.5 rounded">
                  {queryResult.columns.length}
                </span>
              </div>
            </div>

            {/* Search filter and View Switcher */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Filter results..."
                  className="bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 w-48"
                />
              </div>

              <div className="flex items-center bg-slate-900 rounded-lg p-0.5 border border-slate-800">
                <button
                  onClick={() => setViewMode("table")}
                  className={`p-1.5 rounded text-xs transition ${
                    viewMode === "table" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="Table View"
                >
                  <TableIcon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode("json")}
                  className={`p-1.5 rounded text-xs transition ${
                    viewMode === "json" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="JSON View"
                >
                  <Code className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Table View */}
          {viewMode === "table" ? (
            <div className="overflow-x-auto max-h-[500px]">
              {filteredData.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No matching records found.
                </div>
              ) : (
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-950/90 text-slate-400 sticky top-0 z-10 border-b border-slate-800 shadow">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-slate-500 uppercase tracking-wider w-12 text-center">
                        #
                      </th>
                      {queryResult.columns.map((col) => (
                        <th key={col} className="px-4 py-3 font-semibold text-slate-300 uppercase tracking-wider whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {filteredData.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-2.5 text-slate-500 text-center">{idx + 1}</td>
                        {queryResult.columns.map((col) => {
                          const val = row[col];
                          const isNull = val === null || val === undefined;
                          return (
                            <td key={col} className="px-4 py-2.5 whitespace-nowrap">
                              {isNull ? (
                                <span className="text-slate-600 italic">null</span>
                              ) : typeof val === "boolean" ? (
                                <span className={val ? "text-emerald-400" : "text-rose-400"}>
                                  {String(val)}
                                </span>
                              ) : (
                                <span className="text-slate-200">{String(val)}</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            /* JSON View */
            <div className="p-4 bg-slate-950 max-h-[500px] overflow-auto">
              <pre className="font-mono text-xs text-sky-400 leading-relaxed">
                {JSON.stringify(filteredData, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
