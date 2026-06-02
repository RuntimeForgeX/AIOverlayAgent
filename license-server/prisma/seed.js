require("dotenv").config();
const bcrypt = require("bcryptjs");
const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

async function main() {
  const email = (process.env.SEED_ADMIN_EMAIL || "admin@localhost").toLowerCase();
  const password = process.env.SEED_ADMIN_PASSWORD || "admin123";
  const name = process.env.SEED_ADMIN_NAME || "Admin";

  const hash = await bcrypt.hash(password, 12);
  const user = await prisma.user.upsert({
    where: { email },
    update: { password: hash, role: "admin", name },
    create: { email, password: hash, role: "admin", name },
  });

  console.log("Admin user ready:");
  console.log("  Email:   ", email);
  console.log("  Password:", password);
  console.log("  Id:      ", user.id);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
