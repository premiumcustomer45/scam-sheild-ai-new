import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "./schema";

const { Pool } = pg;

// Vercel's Neon integration provides POSTGRES_URL as well as DATABASE_URL.
const connectionString = process.env.DATABASE_URL ?? process.env.POSTGRES_URL;

// Fail per query rather than at import, so URL and message scans (which need
// no database) keep working while the database is not yet provisioned.
if (!connectionString) {
  console.error(
    "DATABASE_URL is not set; sign-in and scan history are unavailable until a database is provisioned.",
  );
}

// Serverless functions run many short-lived instances, so keep each pool small
// to avoid exhausting the database's connection limit (override with DB_POOL_MAX).
export const pool = new Pool({
  connectionString,
  max: Number(process.env.DB_POOL_MAX) || (process.env.VERCEL ? 3 : 10),
  idleTimeoutMillis: 10_000,
});
export const db = drizzle(pool, { schema });

export * from "./schema";
