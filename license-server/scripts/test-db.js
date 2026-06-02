require("dotenv").config();
const { prisma } = require("../src/config/database");

async function main() {
  await prisma.$connect();
  const rows = await prisma.$queryRaw`SELECT 1 AS ok`;
  console.log("CONNECTED OK", rows);
  const users = await prisma.user.count().catch(() => null);
  if (users !== null) {
    console.log("User table exists, count:", users);
  }
}

main()
  .catch((e) => {
    console.error("FAIL:", e.name);
    console.error((e.message || "").split("\n").slice(0, 4).join("\n"));
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
