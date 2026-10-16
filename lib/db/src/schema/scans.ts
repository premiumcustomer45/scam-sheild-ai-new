import { index, integer, jsonb, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { usersTable } from "./users";

type ScanIndicator = {
  code: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "high";
};

type UrlAssessmentRecord = {
  url: string;
  verdict: "lower-risk" | "suspicious" | "high-risk" | "uncertain";
  riskScore: number;
  indicators: ScanIndicator[];
};

export const scansTable = pgTable(
  "scamshield_scans",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    userId: uuid("user_id").references(() => usersTable.id, {
      onDelete: "cascade",
    }),
    inputType: text("input_type").notNull(),
    verdict: text("verdict").notNull(),
    riskScore: integer("risk_score").notNull(),
    indicators: jsonb("indicators").$type<ScanIndicator[]>().notNull(),
    recommendations: jsonb("recommendations").$type<string[]>().notNull(),
    urls: jsonb("urls").$type<UrlAssessmentRecord[]>().notNull(),
    modelVersion: text("model_version").notNull(),
    limitations: jsonb("limitations").$type<string[]>().notNull(),
    redactedPreview: text("redacted_preview"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => [
    index("scamshield_scans_owner_created_idx").on(
      table.userId,
      table.createdAt,
    ),
    index("scamshield_scans_owner_verdict_idx").on(
      table.userId,
      table.verdict,
    ),
  ],
);

export type Scan = typeof scansTable.$inferSelect;
