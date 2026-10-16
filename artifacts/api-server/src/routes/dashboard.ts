import { Router, type IRouter } from "express";
import { and, desc, eq, gte } from "drizzle-orm";
import { GetDashboardStatsQueryParams, GetDashboardStatsResponse } from "@workspace/api-zod";
import { db, scansTable } from "@workspace/db";
import { getSessionUser } from "../lib/auth";

const router: IRouter = Router();

router.get("/dashboard/stats", async (req, res): Promise<void> => {
  const query = GetDashboardStatsQueryParams.safeParse(req.query);
  if (!query.success) {
    res.status(400).json({ error: "Invalid analytics date range." });
    return;
  }
  const days = query.data.days;
  const end = new Date();
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - days + 1);
  start.setUTCHours(0, 0, 0, 0);

  const user = await getSessionUser(req);
  const rows = user
    ? await db
        .select({
          verdict: scansTable.verdict,
          createdAt: scansTable.createdAt,
        })
        .from(scansTable)
        .where(
          and(eq(scansTable.userId, user.id), gte(scansTable.createdAt, start)),
        )
    : [];

  const recentRows = user
    ? await db
        .select()
        .from(scansTable)
        .where(eq(scansTable.userId, user.id))
        .orderBy(desc(scansTable.createdAt))
        .limit(5)
    : [];
  const daily = new Map<string, number>();
  for (let offset = 0; offset < days; offset += 1) {
    const date = new Date(start);
    date.setUTCDate(start.getUTCDate() + offset);
    daily.set(date.toISOString().slice(0, 10), 0);
  }
  for (const row of rows) {
    const date = row.createdAt.toISOString().slice(0, 10);
    daily.set(date, (daily.get(date) ?? 0) + 1);
  }
  const stats = {
    total: rows.length,
    highRisk: rows.filter((row) => row.verdict === "high-risk").length,
    suspicious: rows.filter((row) => row.verdict === "suspicious").length,
    lowerRisk: rows.filter((row) => row.verdict === "lower-risk").length,
    uncertain: rows.filter((row) => row.verdict === "uncertain").length,
    trend: [...daily.entries()].map(([date, count]) => ({ date, count })),
    recent: recentRows.map((row) => ({
      ...row,
      createdAt: row.createdAt.toISOString(),
    })),
  };
  res.json(GetDashboardStatsResponse.parse(stats));
});

export default router;
