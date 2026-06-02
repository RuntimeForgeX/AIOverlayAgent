require("dotenv").config();
const { Client } = require("pg");

const connectionString = process.env.DATABASE_URL;

function getPgConfig() {
  if (!connectionString) return undefined;
  const dbUrl = new URL(connectionString);
  const sslmode = dbUrl.searchParams.get("sslmode");
  const sslaccept = dbUrl.searchParams.get("sslaccept");
  const ssl =
    sslmode && sslmode !== "disable"
      ? { rejectUnauthorized: sslaccept !== "accept_invalid_certs" }
      : undefined;
  dbUrl.searchParams.delete("sslmode");
  dbUrl.searchParams.delete("sslaccept");
  dbUrl.searchParams.delete("sslcert");
  dbUrl.searchParams.delete("sslrootcert");

  return {
    connectionString: dbUrl.toString(),
    ssl,
  };
}

async function main() {
  const client = new Client({
    ...getPgConfig(),
    connectionTimeoutMillis: 15000,
  });
  await client.connect();
  const res = await client.query("SELECT 1 AS ok");
  console.log("PG CONNECTED OK", res.rows);
  await client.end();
}

main().catch((e) => {
  console.error("PG FAIL:", e.message);
  process.exit(1);
});
