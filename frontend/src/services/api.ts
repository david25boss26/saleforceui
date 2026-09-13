import axios from "axios";
import type { Pipeline, ETLExecution, ConfigData, SOQLQueryResponse, SOQLExportResponse } from "../types";

const API_BASE_URL = "http://localhost:8000/api";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  getHealth: async () => {
    const res = await client.get("/health");
    return res.data;
  },

  getPipelines: async (): Promise<Pipeline[]> => {
    const res = await client.get("/pipelines");
    return res.data;
  },

  runPipeline: async (name: string, filepath: string): Promise<any> => {
    const res = await client.post(`/pipelines/${name}/run`, { filepath });
    return res.data;
  },

  dryRunPipeline: async (name: string, filepath: string): Promise<any> => {
    const res = await client.post(`/pipelines/${name}/dry-run`, { filepath });
    return res.data;
  },

  pausePipeline: async (name: string): Promise<any> => {
    const res = await client.post(`/pipelines/${name}/pause`);
    return res.data;
  },

  resumePipeline: async (name: string): Promise<any> => {
    const res = await client.post(`/pipelines/${name}/resume`);
    return res.data;
  },

  getExecutions: async (): Promise<ETLExecution[]> => {
    const res = await client.get("/executions");
    return res.data;
  },

  getExecutionDetails: async (id: string): Promise<{ summary: ETLExecution; logs: any[] }> => {
    const res = await client.get(`/executions/${id}`);
    return res.data;
  },

  getExecutionErrors: async (id: string): Promise<{ mapping_errors: any[]; validation_errors: any[] }> => {
    const res = await client.get(`/executions/${id}/errors`);
    return res.data;
  },

  uploadFile: async (file: File): Promise<{ filepath: string; filename: string; hash: string; is_duplicate: boolean }> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await client.post("/files/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return res.data;
  },

  getConfig: async (): Promise<ConfigData> => {
    const res = await client.get("/config");
    return res.data;
  },

  updateConfig: async (key: string, value: string): Promise<any> => {
    const res = await client.put("/config", { key, value });
    return res.data;
  },

  executeSOQLQuery: async (payload: {
    query: string;
    username?: string;
    password?: string;
    security_token?: string;
    domain?: string;
    limit?: number;
  }): Promise<SOQLQueryResponse> => {
    const res = await client.post("/salesforce/query", payload);
    return res.data;
  },

  exportSOQLQuery: async (payload: {
    query: string;
    output_filename?: string;
    export_format?: string;
    sheet_name?: string;
    username?: string;
    password?: string;
    security_token?: string;
    domain?: string;
  }): Promise<SOQLExportResponse> => {
    const res = await client.post("/salesforce/query/export", payload);
    return res.data;
  },

  getDownloadUrl: (id: string, type: string) => {
    return `${API_BASE_URL}/executions/${id}/download?type=${type}`;
  },

  getExportDownloadUrl: (filepath: string) => {
    return `${API_BASE_URL}/files/download?filepath=${encodeURIComponent(filepath)}`;
  },
};
export default apiService;

