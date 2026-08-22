import React, { useState, useEffect } from "react";
import { 
  Play, 
  Terminal, 
  History, 
  Settings, 
  AlertTriangle, 
  XCircle, 
  Upload, 
  Clock, 
  Database, 
  CloudLightning, 
  RefreshCw, 
  FileSpreadsheet, 
  Download,
  Eye,
  ToggleLeft,
  ToggleRight
} from "lucide-react";
import apiService from "./services/api";
import type { Pipeline, ETLExecution, ConfigData } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "pipelines" | "history" | "errors" | "config">("dashboard");
  
  // Health State
  const [health, setHealth] = useState({ status: "loading", database: "loading", salesforce: "loading", scheduler: "loading" });
  
  // Data States
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [executions, setExecutions] = useState<ETLExecution[]>([]);
  const [config, setConfig] = useState<ConfigData | null>(null);
  
  // Configuration Editor States
  const [selectedConfigKey, setSelectedConfigKey] = useState<keyof ConfigData>("field_mappings");
  const [configText, setConfigText] = useState("");
  const [configStatus, setConfigStatus] = useState<string | null>(null);

  // File Ingestion Selection
  const [selectedPipeline, setSelectedPipeline] = useState<string>("");
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const [uploadedFilePath, setUploadedFilePath] = useState<string | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState<boolean>(false);
  const [runProgress, setRunProgress] = useState<string | null>(null);

  // Detailed Execution Selection
  const [selectedExecId, setSelectedExecId] = useState<string | null>(null);
  const [execDetails, setExecDetails] = useState<any | null>(null);
  const [execErrors, setExecErrors] = useState<any | null>(null);

  // Loading States
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchHealth();
    fetchData();
  }, []);

  const fetchHealth = async () => {
    try {
      const data = await apiService.getHealth();
      setHealth(data);
    } catch {
      setHealth({ status: "unhealthy", database: "disconnected", salesforce: "disconnected", scheduler: "stopped" });
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const pipeList = await apiService.getPipelines();
      setPipelines(pipeList);
      if (pipeList.length > 0 && !selectedPipeline) {
        setSelectedPipeline(pipeList[0].name);
      }
      
      const execList = await apiService.getExecutions();
      setExecutions(execList);
      
      const configData = await apiService.getConfig();
      setConfig(configData);
      setConfigText(configData[selectedConfigKey]);
    } catch (err) {
      console.error("Error loading platform data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigKeyChange = (key: keyof ConfigData) => {
    setSelectedConfigKey(key);
    if (config) {
      setConfigText(config[key]);
    }
    setConfigStatus(null);
  };

  const saveConfig = async () => {
    setConfigStatus("Saving...");
    try {
      await apiService.updateConfig(selectedConfigKey, configText);
      setConfigStatus("Configuration saved successfully!");
      // Reload configurations
      const updatedConfig = await apiService.getConfig();
      setConfig(updatedConfig);
    } catch (err: any) {
      setConfigStatus(`Error: ${err.response?.data?.detail || "Failed to parse YAML configuration."}`);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadingFile(file);
      setDuplicateWarning(false);
      
      try {
        const uploadRes = await apiService.uploadFile(file);
        setUploadedFilePath(uploadRes.filepath);
        if (uploadRes.is_duplicate) {
          setDuplicateWarning(true);
        }
      } catch (err: any) {
        alert(err.response?.data?.detail || "Failed to upload file");
        setUploadingFile(null);
      }
    }
  };

  const triggerETL = async (dryRun: boolean) => {
    if (!selectedPipeline || !uploadedFilePath) {
      alert("Please select a pipeline and upload a form file first.");
      return;
    }

    setRunProgress(dryRun ? "Starting Dry-Run..." : "Executing Ingestion Pipeline...");
    try {
      let result;
      if (dryRun) {
        result = await apiService.dryRunPipeline(selectedPipeline, uploadedFilePath);
      } else {
        result = await apiService.runPipeline(selectedPipeline, uploadedFilePath);
      }
      setRunProgress(null);
      
      // Select the run and display it
      setSelectedExecId(result.execution_id);
      loadExecutionInspector(result.execution_id);
      
      // Clear files
      setUploadingFile(null);
      setUploadedFilePath(null);
      setDuplicateWarning(false);
      
      // Refresh Lists
      fetchData();
      setActiveTab("dashboard");
    } catch (err: any) {
      setRunProgress(null);
      alert(err.response?.data?.detail || "Execution crashed.");
    }
  };

  const toggleSchedule = async (pipe: Pipeline) => {
    try {
      if (pipe.is_enabled) {
        await apiService.pausePipeline(pipe.name);
      } else {
        await apiService.resumePipeline(pipe.name);
      }
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const loadExecutionInspector = async (execId: string) => {
    setSelectedExecId(execId);
    setExecDetails(null);
    setExecErrors(null);
    try {
      const details = await apiService.getExecutionDetails(execId);
      setExecDetails(details);
      
      const errors = await apiService.getExecutionErrors(execId);
      setExecErrors(errors);
    } catch (err) {
      console.error("Failed to load details for " + execId, err);
    }
  };

  // Metric Computations
  const successExecutions = executions.filter(e => e.status === "SUCCESS" || e.status === "PARTIAL_SUCCESS");
  const overallSuccessRate = executions.length > 0 
    ? Math.round((successExecutions.length / executions.length) * 100) 
    : 100;
    
  const totalProcessedRecords = executions.reduce((acc, curr) => acc + curr.records_successful, 0);
  const avgDuration = executions.length > 0
    ? (executions.reduce((acc, curr) => acc + curr.execution_duration, 0) / executions.length).toFixed(1)
    : "0.0";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Banner Navigation */}
      <header className="bg-slate-900/80 backdrop-blur border-b border-slate-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-tr from-sky-500 to-indigo-500 p-2.5 rounded-lg shadow-lg">
            <CloudLightning className="h-6 w-6 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Antigravity Salesforce ETL
              <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700 text-sky-400 font-mono">v1.0.0</span>
            </h1>
            <p className="text-xs text-slate-400">Config-Driven Data Integration Platform</p>
          </div>
        </div>

        {/* System Connectivity Badges */}
        <div className="flex items-center space-x-4">
          {/* DB Health */}
          <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800 text-xs">
            <Database className="h-3.5 w-3.5 text-indigo-400" />
            <span className="text-slate-300">Database:</span>
            <span className={`font-semibold ${health.database === "connected" ? "text-emerald-400" : "text-rose-400"}`}>
              {health.database}
            </span>
          </div>

          {/* Salesforce Health */}
          <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800 text-xs">
            <CloudLightning className="h-3.5 w-3.5 text-sky-400" />
            <span className="text-slate-300">Salesforce:</span>
            <span className={`font-semibold ${health.salesforce === "connected" || health.salesforce === "mocked" ? "text-emerald-400" : "text-rose-400"}`}>
              {health.salesforce}
            </span>
          </div>

          {/* Scheduler Health */}
          <div className="flex items-center space-x-1.5 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800 text-xs">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-slate-300">Scheduler:</span>
            <span className={`font-semibold ${health.scheduler === "running" ? "text-emerald-400" : "text-rose-400"}`}>
              {health.scheduler}
            </span>
          </div>

          {/* Refresh Button */}
          <button onClick={() => { fetchHealth(); fetchData(); }} className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition flex items-center gap-1.5">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-sky-400" : ""}`} />
            {loading && <span className="text-[10px] text-sky-400 font-semibold animate-pulse">Syncing...</span>}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Nav */}
        <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col p-4 space-y-1.5 shrink-0">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest px-3 font-semibold mb-2">Operations</span>
          
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "dashboard" ? "bg-sky-600/10 text-sky-400 border-l-2 border-sky-500" : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            <Play className="h-4 w-4" />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab("pipelines")}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "pipelines" ? "bg-sky-600/10 text-sky-400 border-l-2 border-sky-500" : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            <Clock className="h-4 w-4" />
            <span>Pipelines & Run</span>
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "history" ? "bg-sky-600/10 text-sky-400 border-l-2 border-sky-500" : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            <History className="h-4 w-4" />
            <span>Run History</span>
          </button>

          <button
            onClick={() => setActiveTab("errors")}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "errors" ? "bg-sky-600/10 text-sky-400 border-l-2 border-sky-500" : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            <span>Errors Audit</span>
          </button>

          <span className="text-[10px] text-slate-500 uppercase tracking-widest px-3 font-semibold mt-6 mb-2">System Config</span>

          <button
            onClick={() => setActiveTab("config")}
            className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "config" ? "bg-sky-600/10 text-sky-400 border-l-2 border-sky-500" : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            <Settings className="h-4 w-4" />
            <span>YAML Configurations</span>
          </button>
        </aside>

        {/* Content Box */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          
          {/* Ingestion Running overlay */}
          {runProgress && (
            <div className="absolute inset-0 bg-slate-950/80 z-40 backdrop-blur-sm flex items-center justify-center">
              <div className="bg-slate-900 border border-slate-850 p-8 rounded-xl flex flex-col items-center max-w-sm text-center shadow-2xl">
                <RefreshCw className="h-10 w-10 text-sky-500 animate-spin mb-4" />
                <h3 className="font-bold text-lg text-white mb-2">{runProgress}</h3>
                <p className="text-sm text-slate-400">Processing master files, aligning schemas, joining Salesforce lookups, applying validators, and pushing Bulk API batches.</p>
              </div>
            </div>
          )}

          {/* VIEW: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="space-y-8">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight text-white">Execution Metrics</h2>
                  <p className="text-sm text-slate-400">Key metrics for data integrations and execution state.</p>
                </div>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-4 gap-6">
                {/* Executions Count */}
                <div className="bg-slate-900 border border-slate-850 p-6 rounded-xl relative overflow-hidden group">
                  <div className="absolute -top-3 -right-3 bg-sky-500/5 h-20 w-20 rounded-full group-hover:scale-125 transition duration-500"></div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Ingested Files</p>
                  <p className="text-3xl font-bold mt-2 text-white">{executions.length}</p>
                  <p className="text-xs text-slate-400 mt-1">Total pipeline runs processed</p>
                </div>

                {/* Success Rate */}
                <div className="bg-slate-900 border border-slate-850 p-6 rounded-xl relative overflow-hidden group">
                  <div className="absolute -top-3 -right-3 bg-emerald-500/5 h-20 w-20 rounded-full group-hover:scale-125 transition duration-500"></div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Success Rate</p>
                  <p className={`text-3xl font-bold mt-2 ${overallSuccessRate > 90 ? "text-emerald-400" : "text-amber-400"}`}>
                    {overallSuccessRate}%
                  </p>
                  <p className="text-xs text-slate-400 mt-1">Files completed with no fatal failure</p>
                </div>

                {/* Successful Records */}
                <div className="bg-slate-900 border border-slate-850 p-6 rounded-xl relative overflow-hidden group">
                  <div className="absolute -top-3 -right-3 bg-indigo-500/5 h-20 w-20 rounded-full group-hover:scale-125 transition duration-500"></div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Records Pushed</p>
                  <p className="text-3xl font-bold mt-2 text-white">{totalProcessedRecords}</p>
                  <p className="text-xs text-slate-400 mt-1">Records upserted to Salesforce</p>
                </div>

                {/* Avg Duration */}
                <div className="bg-slate-900 border border-slate-850 p-6 rounded-xl relative overflow-hidden group">
                  <div className="absolute -top-3 -right-3 bg-amber-500/5 h-20 w-20 rounded-full group-hover:scale-125 transition duration-500"></div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Average Processing Time</p>
                  <p className="text-3xl font-bold mt-2 text-white">{avgDuration}s</p>
                  <p className="text-xs text-slate-400 mt-1">Avg run speed per pipeline</p>
                </div>
              </div>

              {/* Ingestion Console */}
              <div className="bg-slate-900 border border-slate-850 p-6 rounded-xl">
                <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                  <Upload className="h-5 w-5 text-sky-400" />
                  ETL Execution Console
                </h3>
                <p className="text-sm text-slate-400 mb-6">Manually process custom external forms immediately using our schema normalization engine.</p>
                
                <div className="grid grid-cols-2 gap-8">
                  {/* Select Form */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Target Integration Pipeline</label>
                      <select
                        value={selectedPipeline}
                        onChange={(e) => setSelectedPipeline(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 px-4 py-2.5 rounded-lg text-sm text-white focus:outline-none focus:border-sky-500"
                      >
                        {pipelines.map(p => (
                          <option key={p.id} value={p.name}>{p.name} ({p.description})</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Source Response File (.xlsx, .xls, .csv)</label>
                      <div className="border-2 border-dashed border-slate-800 hover:border-sky-500 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition relative bg-slate-950/40">
                        <input
                          type="file"
                          accept=".xlsx,.xls,.csv"
                          onChange={handleFileChange}
                          className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                        <FileSpreadsheet className="h-8 w-8 text-slate-500 mb-2" />
                        <span className="text-sm font-medium text-slate-300">
                          {uploadingFile ? uploadingFile.name : "Select or drag file"}
                        </span>
                        <span className="text-xs text-slate-500 mt-1">Excel or CSV formats supported</span>
                      </div>
                    </div>

                    {/* Duplicate Warning */}
                    {duplicateWarning && (
                      <div className="bg-amber-950/20 border border-amber-800/40 text-amber-300 p-4 rounded-lg flex items-start space-x-3 text-xs">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <div>
                          <p className="font-semibold">Idempotency Warning</p>
                          <p className="mt-0.5">This file content hash was processed previously. Running this again will update Salesforce records using their idempotency keys.</p>
                        </div>
                      </div>
                    )}

                    {/* Trigger Actions */}
                    <div className="flex items-center space-x-4 pt-2">
                      <button
                        onClick={() => triggerETL(false)}
                        disabled={!uploadedFilePath}
                        className="flex-1 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium py-2.5 rounded-lg text-sm transition flex items-center justify-center space-x-2"
                      >
                        <Play className="h-4 w-4" />
                        <span>Run ETL Loader</span>
                      </button>
                      <button
                        onClick={() => triggerETL(true)}
                        disabled={!uploadedFilePath}
                        className="flex-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 disabled:bg-slate-800/50 disabled:text-slate-600 py-2.5 rounded-lg text-sm transition flex items-center justify-center space-x-2"
                      >
                        <Terminal className="h-4 w-4" />
                        <span>Run Dry-Run Mode</span>
                      </button>
                    </div>
                  </div>

                  {/* pipeline guide */}
                  <div className="bg-slate-950/40 border border-slate-850 p-6 rounded-lg text-xs space-y-4">
                    <h4 className="font-semibold text-white tracking-wider uppercase text-[10px] text-slate-400">How Form Normalization Works</h4>
                    <ul className="space-y-3 text-slate-400 list-disc pl-4">
                      <li>Files are mapped dynamically against the configurations set in <span className="font-semibold text-slate-300">field_mappings.yaml</span>.</li>
                      <li>Column headers do not need to match exactly; they will align based on their defined <span className="font-semibold text-slate-300">aliases</span>.</li>
                      <li>Lookups against master lists (Products, Budgets, Checklists) are matched to obtain valid Salesforce IDs.</li>
                      <li>Rows containing lookup failures, validation errors, or duplicate entries will be separated into reports.</li>
                      <li>Successful entries will be pushed to Salesforce via Bulk API 2.0.</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Recent runs */}
              <div>
                <h3 className="text-lg font-bold text-white mb-4">Recent Ingestions</h3>
                <div className="bg-slate-900 border border-slate-850 rounded-xl overflow-hidden">
                  <table className="w-full border-collapse text-left text-sm">
                    <thead>
                      <tr className="bg-slate-850/50 border-b border-slate-850 text-slate-400 font-semibold text-xs uppercase tracking-wider">
                        <th className="px-6 py-3.5">Execution ID</th>
                        <th className="px-6 py-3.5">Pipeline</th>
                        <th className="px-6 py-3.5">Status</th>
                        <th className="px-6 py-3.5">Records Ingested</th>
                        <th className="px-6 py-3.5">Success</th>
                        <th className="px-6 py-3.5">Failed</th>
                        <th className="px-6 py-3.5">Duration</th>
                        <th className="px-6 py-3.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-850 text-slate-300">
                      {executions.slice(0, 5).map((e) => (
                        <tr key={e.id} className="hover:bg-slate-850/20 transition">
                          <td className="px-6 py-4 font-mono font-bold text-white">{e.execution_id}</td>
                          <td className="px-6 py-4">{e.pipeline_name}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                              e.status === "SUCCESS" ? "bg-emerald-950/20 text-emerald-400 border-emerald-800/30" :
                              e.status === "PARTIAL_SUCCESS" ? "bg-amber-950/20 text-amber-400 border-amber-800/30" :
                              "bg-rose-950/20 text-rose-400 border-rose-800/30"
                            }`}>
                              {e.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 font-semibold">{e.records_received}</td>
                          <td className="px-6 py-4 text-emerald-400">{e.records_successful}</td>
                          <td className="px-6 py-4 text-rose-400">{e.records_failed}</td>
                          <td className="px-6 py-4 text-slate-400">{e.execution_duration.toFixed(1)}s</td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => { setActiveTab("history"); loadExecutionInspector(e.execution_id); }}
                              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg font-medium transition flex items-center space-x-1 ml-auto"
                            >
                              <Eye className="h-3 w-3" />
                              <span>Inspect</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* VIEW: PIPELINES */}
          {activeTab === "pipelines" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">Ingestion Pipelines</h2>
                <p className="text-sm text-slate-400">Review defined ETL pipelines, schedules, and active state controls.</p>
              </div>

              <div className="grid grid-cols-2 gap-6">
                {pipelines.map(pipe => (
                  <div key={pipe.id} className="bg-slate-900 border border-slate-850 p-6 rounded-xl flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold text-lg text-white">{pipe.name}</h3>
                        <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                          pipe.is_enabled ? "bg-emerald-950/20 text-emerald-400 border-emerald-800/30" : "bg-slate-950 text-slate-500 border-slate-800"
                        }`}>
                          {pipe.is_enabled ? "Active Scheduler" : "Scheduler Paused"}
                        </span>
                      </div>
                      <p className="text-sm text-slate-400 mb-6">{pipe.description}</p>
                      
                      <div className="space-y-2 bg-slate-950/50 p-4 rounded-lg border border-slate-850 text-xs text-slate-400 mb-6">
                        <div className="flex justify-between">
                          <span>Cron Expression:</span>
                          <span className="font-mono text-slate-200">{pipe.schedule_cron}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Timezone:</span>
                          <span className="text-slate-200">{pipe.schedule_timezone}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Status:</span>
                          <span className="text-slate-200 font-semibold">{pipe.status}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 border-t border-slate-850 pt-4">
                      <button
                        onClick={() => toggleSchedule(pipe)}
                        className={`flex-1 py-2 px-3 text-xs font-medium rounded-lg transition flex items-center justify-center space-x-1.5 ${
                          pipe.is_enabled 
                            ? "bg-amber-600/10 hover:bg-amber-600/20 text-amber-400 border border-amber-800/20" 
                            : "bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border border-emerald-800/20"
                        }`}
                      >
                        {pipe.is_enabled ? <ToggleLeft className="h-4 w-4" /> : <ToggleRight className="h-4 w-4" />}
                        <span>{pipe.is_enabled ? "Pause Schedule" : "Resume Schedule"}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW: RUN HISTORY */}
          {activeTab === "history" && (
            <div className="flex space-x-8">
              {/* List */}
              <div className="flex-1 space-y-6">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight text-white">Execution History</h2>
                  <p className="text-sm text-slate-400">Review metrics and logs from historical pipeline executions.</p>
                </div>

                <div className="bg-slate-900 border border-slate-850 rounded-xl overflow-hidden">
                  <table className="w-full border-collapse text-left text-sm">
                    <thead>
                      <tr className="bg-slate-850/50 border-b border-slate-850 text-slate-400 font-semibold text-xs uppercase tracking-wider">
                        <th className="px-6 py-3.5">Execution ID</th>
                        <th className="px-6 py-3.5">Pipeline</th>
                        <th className="px-6 py-3.5">Date</th>
                        <th className="px-6 py-3.5">Status</th>
                        <th className="px-6 py-3.5">Success</th>
                        <th className="px-6 py-3.5 font-bold text-rose-400">Failed</th>
                        <th className="px-6 py-3.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-850 text-slate-300">
                      {executions.map((e) => (
                        <tr key={e.id} className={`hover:bg-slate-850/20 transition ${selectedExecId === e.execution_id ? "bg-slate-850/30 border-l-2 border-sky-500" : ""}`}>
                          <td className="px-6 py-4 font-mono font-bold text-white">{e.execution_id}</td>
                          <td className="px-6 py-4">{e.pipeline_name}</td>
                          <td className="px-6 py-4 text-xs text-slate-400">
                            {new Date(e.start_time).toLocaleString()}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                              e.status === "SUCCESS" ? "bg-emerald-950/20 text-emerald-400 border-emerald-800/30" :
                              e.status === "PARTIAL_SUCCESS" ? "bg-amber-950/20 text-amber-400 border-amber-800/30" :
                              "bg-rose-950/20 text-rose-400 border-rose-800/30"
                            }`}>
                              {e.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-emerald-400 font-medium">{e.records_successful}</td>
                          <td className="px-6 py-4 text-rose-400 font-medium">{e.records_failed}</td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => loadExecutionInspector(e.execution_id)}
                              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg font-medium transition flex items-center space-x-1 ml-auto"
                            >
                              <Eye className="h-3 w-3" />
                              <span>Inspect</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Inspector Panel */}
              {selectedExecId && (
                <div className="w-96 bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between shrink-0 shadow-2xl space-y-6 h-fit">
                  {execDetails ? (
                    <div className="space-y-6">
                      <div className="flex items-center justify-between border-b border-slate-850 pb-4">
                        <div>
                          <h3 className="font-bold text-lg text-white">Inspector: {selectedExecId}</h3>
                          <p className="text-xs text-slate-400">Details of pipeline execution</p>
                        </div>
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                          execDetails.summary.status === "SUCCESS" ? "bg-emerald-950/20 text-emerald-400 border-emerald-800/30" :
                          execDetails.summary.status === "PARTIAL_SUCCESS" ? "bg-amber-950/20 text-amber-400 border-amber-800/30" :
                          "bg-rose-950/20 text-rose-400 border-rose-800/30"
                        }`}>
                          {execDetails.summary.status}
                        </span>
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                          <p className="text-slate-500 font-medium">Ingested</p>
                          <p className="text-lg font-bold text-white mt-1">{execDetails.summary.records_received}</p>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                          <p className="text-slate-500 font-medium">Loaded Successfully</p>
                          <p className="text-lg font-bold text-emerald-400 mt-1">{execDetails.summary.records_successful}</p>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                          <p className="text-slate-500 font-medium">Failed Records</p>
                          <p className="text-lg font-bold text-rose-400 mt-1">{execDetails.summary.records_failed}</p>
                        </div>
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                          <p className="text-slate-500 font-medium">Processing Speed</p>
                          <p className="text-lg font-bold text-slate-200 mt-1">{execDetails.summary.execution_duration.toFixed(1)}s</p>
                        </div>
                      </div>

                      {/* Error text */}
                      {execDetails.summary.error_summary && (
                        <div className="bg-rose-950/20 border border-rose-900/30 p-3 rounded-lg text-xs text-rose-300">
                          <p className="font-semibold">Summary Notes</p>
                          <p className="mt-1">{execDetails.summary.error_summary}</p>
                        </div>
                      )}

                      {/* Spreadsheet Download Panel */}
                      <div className="space-y-2">
                        <h4 className="font-semibold text-xs uppercase tracking-wider text-slate-400">Download Run Artifacts</h4>
                        <div className="grid grid-cols-1 gap-2">
                          <a
                            href={apiService.getDownloadUrl(selectedExecId, "summary")}
                            className="bg-slate-950 hover:bg-slate-850 p-2.5 rounded-lg border border-slate-850 text-xs font-medium text-slate-300 flex items-center justify-between"
                          >
                            <span>1. Execution Summary</span>
                            <Download className="h-3.5 w-3.5 text-sky-400" />
                          </a>
                          
                          {execDetails.summary.records_successful > 0 && (
                            <a
                              href={apiService.getDownloadUrl(selectedExecId, "successful")}
                              className="bg-slate-950 hover:bg-slate-850 p-2.5 rounded-lg border border-slate-850 text-xs font-medium text-slate-300 flex items-center justify-between"
                            >
                              <span>2. Successful Records</span>
                              <Download className="h-3.5 w-3.5 text-emerald-400" />
                            </a>
                          )}

                          {execDetails.summary.records_failed > 0 && (
                            <a
                              href={apiService.getDownloadUrl(selectedExecId, "failed")}
                              className="bg-slate-950 hover:bg-slate-850 p-2.5 rounded-lg border border-slate-850 text-xs font-medium text-slate-300 flex items-center justify-between"
                            >
                              <span>3. Failed Ingestion Records</span>
                              <Download className="h-3.5 w-3.5 text-rose-400" />
                            </a>
                          )}

                          {execErrors && (execErrors.mapping_errors.length > 0 || execErrors.validation_errors.length > 0) && (
                            <a
                              href={apiService.getDownloadUrl(selectedExecId, "validation")}
                              className="bg-slate-950 hover:bg-slate-850 p-2.5 rounded-lg border border-slate-850 text-xs font-medium text-slate-300 flex items-center justify-between"
                            >
                              <span>4. Validation & Lookup Errors</span>
                              <Download className="h-3.5 w-3.5 text-amber-400" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-12">
                      <RefreshCw className="h-6 w-6 text-sky-500 animate-spin" />
                      <span className="text-xs text-slate-500 mt-2">Retrieving log audits...</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* VIEW: ERRORS AUDIT */}
          {activeTab === "errors" && (
            <div className="space-y-8">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">Errors Drill-Down</h2>
                <p className="text-sm text-slate-400">Audit mapping gaps, reference failures, syntax validation issues, and duplicates.</p>
              </div>

              {/* Show error logs of the most recent execution if any */}
              {executions.length > 0 ? (
                <div className="space-y-6">
                  {/* Select Execution context */}
                  <div className="flex items-center space-x-4 bg-slate-900 border border-slate-850 p-4 rounded-xl">
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Filter Execution Context:</label>
                    <select
                      value={selectedExecId || ""}
                      onChange={(e) => loadExecutionInspector(e.target.value)}
                      className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs text-white focus:outline-none"
                    >
                      <option value="">-- Choose Run ID --</option>
                      {executions.map(e => (
                        <option key={e.id} value={e.execution_id}>{e.execution_id} ({e.pipeline_name} - {new Date(e.start_time).toLocaleDateString()})</option>
                      ))}
                    </select>
                  </div>

                  {execErrors ? (
                    <div className="space-y-8">
                      {/* Lookup & Mapping Errors */}
                      <div className="bg-slate-900 border border-slate-850 rounded-xl p-6">
                        <h3 className="text-md font-bold text-white mb-4 flex items-center gap-2">
                          <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
                          Mapping & Lookup Issues ({execErrors.mapping_errors.length})
                        </h3>
                        {execErrors.mapping_errors.length > 0 ? (
                          <div className="overflow-hidden border border-slate-850 rounded-lg">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-slate-850/50 text-slate-400 font-semibold uppercase">
                                <tr>
                                  <th className="px-4 py-3">Row</th>
                                  <th className="px-4 py-3">Field</th>
                                  <th className="px-4 py-3">Input Code</th>
                                  <th className="px-4 py-3 text-rose-400">Problem</th>
                                  <th className="px-4 py-3">Suggested Action</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-850 text-slate-300">
                                {execErrors.mapping_errors.map((err: any) => (
                                  <tr key={err.id} className="hover:bg-slate-850/10">
                                    <td className="px-4 py-3 font-semibold">{err.source_row}</td>
                                    <td className="px-4 py-3 font-mono">{err.field}</td>
                                    <td className="px-4 py-3 font-semibold text-white">{err.input_value || "N/A"}</td>
                                    <td className="px-4 py-3 text-rose-300">{err.error_message}</td>
                                    <td className="px-4 py-3 text-slate-400">Ensure this master key exists in reference Excel downloads.</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500">No mapping or lookup resolution issues found in this run.</p>
                        )}
                      </div>

                      {/* Validation & Business Rule Errors */}
                      <div className="bg-slate-900 border border-slate-850 rounded-xl p-6">
                        <h3 className="text-md font-bold text-white mb-4 flex items-center gap-2">
                          <XCircle className="h-4.5 w-4.5 text-rose-500" />
                          Syntax & Validation Failures ({execErrors.validation_errors.length})
                        </h3>
                        {execErrors.validation_errors.length > 0 ? (
                          <div className="overflow-hidden border border-slate-850 rounded-lg">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-slate-850/50 text-slate-400 font-semibold uppercase">
                                <tr>
                                  <th className="px-4 py-3">Row</th>
                                  <th className="px-4 py-3">Field</th>
                                  <th className="px-4 py-3">Input Value</th>
                                  <th className="px-4 py-3 font-semibold text-rose-400">Failed Rule</th>
                                  <th className="px-4 py-3">Error Detail</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-850 text-slate-300">
                                {execErrors.validation_errors.map((err: any) => (
                                  <tr key={err.id} className="hover:bg-slate-850/10">
                                    <td className="px-4 py-3 font-semibold">{err.source_row}</td>
                                    <td className="px-4 py-3 font-mono">{err.field}</td>
                                    <td className="px-4 py-3 font-semibold text-white">{err.input_value || "N/A"}</td>
                                    <td className="px-4 py-3"><span className="bg-rose-950/30 border border-rose-900/30 px-2 py-0.5 rounded text-[10px] text-rose-300 uppercase tracking-wider">{err.rule}</span></td>
                                    <td className="px-4 py-3 text-rose-300">{err.error_message}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500">No syntax schema format errors found in this run.</p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-900 border border-slate-850 p-12 text-center rounded-xl">
                      <p className="text-sm text-slate-500">Select an execution ID from the selector above to audit row errors.</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-850 p-12 text-center rounded-xl">
                  <p className="text-sm text-slate-500">No pipeline executions have run yet. Manual runs will record errors here.</p>
                </div>
              )}
            </div>
          )}

          {/* VIEW: YAML CONFIG */}
          {activeTab === "config" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">Configure Rules Engine</h2>
                <p className="text-sm text-slate-400">Modify extraction queries, column aliases, business validation rules, and cron schedules directly.</p>
              </div>

              <div className="grid grid-cols-1 gap-6">
                <div className="bg-slate-900 border border-slate-850 rounded-xl overflow-hidden flex flex-col">
                  {/* Selector Tabs */}
                  <div className="bg-slate-850/50 border-b border-slate-850 px-4 py-2 flex items-center space-x-2">
                    <button
                      onClick={() => handleConfigKeyChange("field_mappings")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        selectedConfigKey === "field_mappings" ? "bg-sky-600 text-white" : "hover:bg-slate-850 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      1. Field Mappings & Aliases
                    </button>
                    <button
                      onClick={() => handleConfigKeyChange("validation_rules")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        selectedConfigKey === "validation_rules" ? "bg-sky-600 text-white" : "hover:bg-slate-850 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      2. Validation Rules
                    </button>
                    <button
                      onClick={() => handleConfigKeyChange("transformation_rules")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        selectedConfigKey === "transformation_rules" ? "bg-sky-600 text-white" : "hover:bg-slate-850 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      3. Transformation Operations
                    </button>
                    <button
                      onClick={() => handleConfigKeyChange("salesforce_objects")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        selectedConfigKey === "salesforce_objects" ? "bg-sky-600 text-white" : "hover:bg-slate-850 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      4. Salesforce Master SOQL
                    </button>
                    <button
                      onClick={() => handleConfigKeyChange("scheduler")}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                        selectedConfigKey === "scheduler" ? "bg-sky-600 text-white" : "hover:bg-slate-850 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      5. Scheduler Cron
                    </button>
                  </div>

                  {/* Textarea */}
                  <div className="p-6 space-y-4">
                    <textarea
                      value={configText}
                      onChange={(e) => setConfigText(e.target.value)}
                      rows={20}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-sm text-sky-400 focus:outline-none focus:border-sky-500 resize-none"
                    ></textarea>

                    {/* Status Alert */}
                    {configStatus && (
                      <div className={`p-4 rounded-lg text-xs font-semibold ${
                        configStatus.startsWith("Error:") ? "bg-rose-950/20 border border-rose-900/30 text-rose-300" : "bg-emerald-950/20 border border-emerald-900/30 text-emerald-300"
                      }`}>
                        {configStatus}
                      </div>
                    )}

                    <div className="flex justify-end pt-2">
                      <button
                        onClick={saveConfig}
                        className="bg-sky-600 hover:bg-sky-500 text-white font-semibold px-6 py-2 rounded-lg text-sm transition"
                      >
                        Save Configuration
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
