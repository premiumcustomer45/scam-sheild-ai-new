import axios, { type AxiosError } from "axios";

export type MlIndicator = {
  code: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "high";
};

export type MlUrlAssessment = {
  url: string;
  verdict: "lower-risk" | "suspicious" | "high-risk" | "uncertain";
  riskScore: number;
  indicators: MlIndicator[];
};

export type MlPrediction = {
  verdict: "lower-risk" | "suspicious" | "high-risk" | "uncertain";
  riskScore: number;
  model_probability: number | null;
  indicators: MlIndicator[];
  recommendations: string[];
  model_version: string;
  limitations: string[];
  urls: MlUrlAssessment[];
};

export class MlServiceError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "MlServiceError";
  }
}

// A serverless ML service can take several seconds to cold start, so the
// default timeout leaves room for that; override with ML_SERVICE_TIMEOUT_MS.
const timeoutMs = Number(process.env.ML_SERVICE_TIMEOUT_MS) || 25_000;
const serviceToken = process.env.ML_SERVICE_TOKEN;

const client = axios.create({
  baseURL: process.env.ML_SERVICE_URL ?? "http://127.0.0.1:8000",
  timeout: timeoutMs,
  headers: serviceToken ? { "x-ml-service-token": serviceToken } : undefined,
  maxContentLength: 64 * 1024,
  maxBodyLength: 64 * 1024,
});

export async function requestPrediction(
  endpoint: "/predict/url" | "/predict/text" | "/predict/combined",
  payload: { url: string } | { text: string },
): Promise<MlPrediction> {
  try {
    const response = await client.post<MlPrediction>(endpoint, payload);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      if (axiosError.response?.status === 422) {
        throw new MlServiceError(400, "The input could not be analyzed.");
      }
    }
    throw new MlServiceError(
      503,
      "The scanner is temporarily unavailable. Please try again shortly.",
    );
  }
}

export async function checkMlReadiness(): Promise<boolean> {
  try {
    await client.get("/ready", { timeout: 10_000 });
    return true;
  } catch {
    return false;
  }
}
