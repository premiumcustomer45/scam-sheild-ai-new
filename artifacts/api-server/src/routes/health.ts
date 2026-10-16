import { Router, type IRouter } from "express";
import { sql } from "drizzle-orm";
import { db } from "@workspace/db";
import { HealthCheckResponse } from "@workspace/api-zod";
import { checkMlReadiness } from "../lib/ml-client";

const router: IRouter = Router();

router.get("/health", (_req, res) => {
  res.json(HealthCheckResponse.parse({ status: "ok" }));
});

router.get("/ready", async (req, res): Promise<void> => {
  try {
    await db.execute(sql`select 1`);
    const mlReady = await checkMlReadiness();
    if (!mlReady) {
      res.status(503).json({ error: "A required service is not ready." });
      return;
    }
    res.json(HealthCheckResponse.parse({ status: "ready" }));
  } catch (error) {
    req.log.error({ err: error }, "Readiness check failed");
    res.status(503).json({ error: "A required service is not ready." });
  }
});

router.get("/healthz", (_req, res) => {
  const data = HealthCheckResponse.parse({ status: "ok" });
  res.json(data);
});

export default router;
