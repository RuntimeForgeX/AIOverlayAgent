const { PrismaClient } = require("@prisma/client");

function getDatabaseUrl() {
  if (!process.env.DATABASE_URL) return undefined;

  const dbUrl = new URL(process.env.DATABASE_URL);
  if (!dbUrl.searchParams.has("connection_limit")) {
    dbUrl.searchParams.set("connection_limit", "2");
  }
  if (!dbUrl.searchParams.has("pool_timeout")) {
    dbUrl.searchParams.set("pool_timeout", "20");
  }

  return dbUrl.toString();
}

const databaseUrl = getDatabaseUrl();

const prisma = new PrismaClient({
  datasources: databaseUrl
    ? {
        db: {
          url: databaseUrl,
        },
      }
    : undefined,
  log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
});

module.exports = { prisma };
