import { and, eq } from "drizzle-orm";
import { Router, type IRouter } from "express";
import { CreateFeedbackBody, CreateFeedbackResponse } from "@workspace/api-zod";
import { db, feedbackTable, scansTable } from "@workspace/db";
import { getSessionUser } from "../lib/auth";

const router: IRouter = Router();
const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

router.post("/feedback", async (req, res): Promise<void> => {
  const input = CreateFeedbackBody.safeParse(req.body);
  if (!input.success) {
    res.status(400).json({ error: "Select a valid feedback category." });
    return;
  }
  if (!uuidPattern.test(input.data.scanId)) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  const user = await getSessionUser(req);
  if (!user) {
    res.status(401).json({ error: "Sign in to send feedback." });
    return;
  }
  const [scan] = await db
    .select({ id: scansTable.id })
    .from(scansTable)
    .where(and(eq(scansTable.id, input.data.scanId), eq(scansTable.userId, user.id)))
    .limit(1);
  if (!scan) {
    res.status(404).json({ error: "Scan not found." });
    return;
  }
  await db.insert(feedbackTable).values({
    scanId: scan.id,
    userId: user.id,
    category: input.data.category,
  });
  res.status(201).json(CreateFeedbackResponse.parse({ success: true }));
});

export default router;
