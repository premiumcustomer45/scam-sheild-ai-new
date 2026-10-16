import { randomUUID } from "node:crypto";
import { Router, type IRouter, type Request, type Response } from "express";
import { rateLimit } from "express-rate-limit";
import { and, count, desc, eq } from "drizzle-orm";
import {
  CreateCombinedScanBody,
  CreateCombinedScanResponse,
  CreateTextScanBody,
  CreateTextScanResponse,
  CreateUrlScanBody,
  CreateUrlScanResponse,
  DeleteScanParams,
  DeleteScanResponse,
  GetScanParams,
  GetScanResponse,
  ListScansQueryParams,
  ListScansResponse,
} from "@workspace/api-zod";
import { db, scansTable } from "@workspace/db";
import { getSessionUser } from "../lib/auth";
import {
  MlServiceError,
  requestPrediction,
  type MlPrediction,
} from "../lib/ml-client";

const router: IRouter = Router();
const scanLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 30,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many scan requests. Try again later." },
});
const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function toScan(
  scan: typeof scansTable.$inferSelect | null,
  prediction: MlPrediction,
  inputType: "url" | "text" | "combined",
  redactedPreview: string | null,
) {
  return {
    id: scan?.id ?? randomUUID(),
    inputType,
    verdict: prediction.verdict,
    riskScore: prediction.riskScore,
    indicators: prediction.indicators,
    recommendations: prediction.recommendations,
    urls: prediction.urls,
    modelVersion: prediction.model_version,
    limitations: prediction.limitations,
    redactedPreview,
    createdAt: scan?.createdAt.toISOString() ?? new Date().toISOString(),
  };
}

async function saveIfSignedIn(
  req: Request,
  prediction: MlPrediction,
  inputType: "url" | "text" | "combined",
  redactedPreview: string | null,
) {
  const user = await getSessionUser(req);
  if (!user) return null;
  const [scan] = await db
    .insert(scansTable)
    .values({
      userId: user.id,
      inputType,
      verdict: prediction.verdict,
      riskScore: prediction.riskScore,
      indicators: prediction.indicators,
      recommendations: prediction.recommendations,
      urls: prediction.urls,
      modelVersion: prediction.model_version,
      limitations: prediction.limitations,
      redactedPreview,
    })
    .returning();
  return scan ?? null;
}

function respondWithMlError(
  error: unknown,
  res: Response,
): boolean {
  if (!(error instanceof MlServiceError)) return false;
  res.status(error.statusCode).json({ error: error.message });
  return true;
}

router.post("/scans/url", scanLimiter, async (req, res): Promise<void> => {
  const input = CreateUrlScanBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Enter a valid HTTP or HTTPS URL." });
    return;
  }
  try {
    const prediction = await requestPrediction("/predict/url", { url: input.data.url });
    const preview = prediction.urls[0]?.url ?? null;
    const saved = await saveIfSignedIn(req, prediction, "url", preview);
    res
      .status(201)
      .json(
        CreateUrlScanResponse.parse(
          toScan(saved, prediction, "url", preview),
        ),
      );
  } catch (error) {
    if (respondWithMlError(error, res)) return;
    req.log.error({ err: error }, "URL assessment failed");
    res.status(500).json({ error: "Could not complete the URL assessment." });
  }
});

router.post("/scans/text", scanLimiter, async (req, res): Promise<void> => {
  const input = CreateTextScanBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Enter a message of 1–20,000 characters." });
    return;
  }
  try {
    const prediction = await requestPrediction("/predict/text", { text: input.data.text });
    const saved = await saveIfSignedIn(req, prediction, "text", null);
    res
      .status(201)
      .json(
        CreateTextScanResponse.parse(
          toScan(saved, prediction, "text", null),
        ),
      );
  } catch (error) {
    if (respondWithMlError(error, res)) return;
    req.log.error({ err: error }, "Message assessment failed");
    res.status(500).json({ error: "Could not complete the message assessment." });
  }
});

router.post("/scans/combined", scanLimiter, async (req, res): Promise<void> => {
  const input = CreateCombinedScanBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Enter a message of 1–20,000 characters." });
    return;
  }
  try {
    const prediction = await requestPrediction("/predict/combined", {
      text: input.data.text,
    });
    const saved = await saveIfSignedIn(req, prediction, "combined", null);
    res
      .status(201)
      .json(
        CreateCombinedScanResponse.parse(
          toScan(saved, prediction, "combined", null),
        ),
      );
  } catch (error) {
    if (respondWithMlError(error, res)) return;
    req.log.error({ err: error }, "Combined assessment failed");
    res.status(500).json({ error: "Could not complete the combined assessment." });
  }
});

router.get("/scans", async (req, res): Promise<void> => {
  const query = ListScansQueryParams.safeParse(req.query);
  if (!query.success) {
    res.status(400).json({ error: "Invalid history page or page size." });
    return;
  }
  const user = await getSessionUser(req);
  if (!user) {
    res.json(ListScansResponse.parse({ items: [], page: query.data.page, limit: query.data.limit, total: 0 }));
    return;
  }

  const [totalRow] = await db
    .select({ value: count() })
    .from(scansTable)
    .where(eq(scansTable.userId, user.id));
  const rows = await db
    .select()
    .from(scansTable)
    .where(eq(scansTable.userId, user.id))
    .orderBy(desc(scansTable.createdAt))
    .limit(query.data.limit)
    .offset((query.data.page - 1) * query.data.limit);

  const items = rows.map((row) => ({
    ...row,
    createdAt: row.createdAt.toISOString(),
  }));
  res.json(
    ListScansResponse.parse({
      items,
      page: query.data.page,
      limit: query.data.limit,
      total: totalRow?.value ?? 0,
    }),
  );
});

router.get("/scans/:id", async (req, res): Promise<void> => {
  const params = GetScanParams.safeParse(req.params);
  const user = await getSessionUser(req);
  if (!params.success || !uuidPattern.test(params.data.id) || !user) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  const [scan] = await db
    .select()
    .from(scansTable)
    .where(and(eq(scansTable.id, params.data.id), eq(scansTable.userId, user.id)))
    .limit(1);
  if (!scan) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  res.json(GetScanResponse.parse({ ...scan, createdAt: scan.createdAt.toISOString() }));
});

router.delete("/scans/:id", async (req, res): Promise<void> => {
  const params = DeleteScanParams.safeParse(req.params);
  const user = await getSessionUser(req);
  if (!params.success || !uuidPattern.test(params.data.id) || !user) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  const [deleted] = await db
    .delete(scansTable)
    .where(and(eq(scansTable.id, params.data.id), eq(scansTable.userId, user.id)))
    .returning({ id: scansTable.id });
  if (!deleted) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  res.json(DeleteScanResponse.parse({ success: true }));
});

export default router;
