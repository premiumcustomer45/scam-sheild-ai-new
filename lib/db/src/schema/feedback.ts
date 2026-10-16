import { index, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { scansTable } from "./scans";
import { usersTable } from "./users";

export const feedbackTable = pgTable(
  "scamshield_feedback",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    scanId: uuid("scan_id")
      .notNull()
      .references(() => scansTable.id, { onDelete: "cascade" }),
    userId: uuid("user_id")
      .notNull()
      .references(() => usersTable.id, { onDelete: "cascade" }),
    category: text("category").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => [index("scamshield_feedback_scan_idx").on(table.scanId)],
);
