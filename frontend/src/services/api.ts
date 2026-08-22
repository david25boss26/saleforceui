import axios from "axios";
import type { Pipeline, ETLExecution, ConfigData } from "../types";

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

  getDownloadUrl: (id: string, type: string) => {
    return `${API_BASE_URL}/executions/${id}/download?type=${type}`;
  },
};
export default apiService;
