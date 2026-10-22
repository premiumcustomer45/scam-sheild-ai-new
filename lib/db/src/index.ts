import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "./schema";

const { Pool } = pg;

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Serverless functions run many short-lived instances, so keep each pool small
// to avoid exhausting the database's connection limit (override with DB_POOL_MAX).
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: Number(process.env.DB_POOL_MAX) || (process.env.VERCEL ? 3 : 10),
  idleTimeoutMillis: 10_000,
});
export const db = drizzle(pool, { schema });

export * from "./schema";
