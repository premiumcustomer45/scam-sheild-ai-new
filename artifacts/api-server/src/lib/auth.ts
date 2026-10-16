import {
  createHmac,
  timingSafeEqual,
} from "node:crypto";
import type { Request, Response } from "express";
import { eq } from "drizzle-orm";
import { db, usersTable, type User } from "@workspace/db";

export const SESSION_COOKIE = "scamshield_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;

function sessionSecret(): string {
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error("SESSION_SECRET must contain at least 32 characters.");
  }
  return secret;
}

export function createSessionToken(userId: string): string {
  const payload = Buffer.from(
    JSON.stringify({
      sub: userId,
      exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
    }),
  ).toString("base64url");
  const signature = createHmac("sha256", sessionSecret())
    .update(payload)
    .digest("base64url");
  return `${payload}.${signature}`;
}

export function readSessionUserId(req: Request): string | null {
  const token = req.cookies?.[SESSION_COOKIE];
  if (typeof token !== "string") return null;
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra) return null;
  try {
    const expected = createHmac("sha256", sessionSecret())
      .update(payload)
      .digest();
    const supplied = Buffer.from(signature, "base64url");
    if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
      return null;
    }
    const decoded: unknown = JSON.parse(Buffer.from(payload, "base64url").toString());
    if (
      !decoded ||
      typeof decoded !== "object" ||
      !("sub" in decoded) ||
      typeof decoded.sub !== "string" ||
      !("exp" in decoded) ||
      typeof decoded.exp !== "number" ||
      decoded.exp <= Math.floor(Date.now() / 1000)
    ) {
      return null;
    }
    return decoded.sub;
  } catch {
    return null;
  }
}

export async function getSessionUser(req: Request): Promise<User | null> {
  const userId = readSessionUserId(req);
  if (!userId) return null;
  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId)).limit(1);
  return user ?? null;
}

export function setSessionCookie(res: Response, userId: string): void {
  res.cookie(SESSION_COOKIE, createSessionToken(userId), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS * 1000,
  });
}

export function clearSessionCookie(res: Response): void {
  res.clearCookie(SESSION_COOKIE, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
  });
}

export function toPublicUser(user: User) {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    createdAt: user.createdAt.toISOString(),
  };
}
