/**
 * Generate RS256 key pair for JWT signing (dev / first-time setup).
 * Uses OpenSSL when available; otherwise Node crypto (Windows-friendly).
 */
const { execSync } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const keysDir = path.join(__dirname, "..", "keys");
const privatePath = path.join(keysDir, "private.pem");
const publicPath = path.join(keysDir, "public.pem");

if (!fs.existsSync(keysDir)) {
  fs.mkdirSync(keysDir, { recursive: true });
}

if (fs.existsSync(privatePath)) {
  console.log("Keys already exist:", privatePath);
  process.exit(0);
}

function generateWithNode() {
  const { privateKey, publicKey } = crypto.generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  fs.writeFileSync(privatePath, privateKey, "utf8");
  fs.writeFileSync(publicPath, publicKey, "utf8");
}

function generateWithOpenSSL() {
  execSync(`openssl genrsa -out "${privatePath}" 2048`, { stdio: "inherit" });
  execSync(`openssl rsa -in "${privatePath}" -pubout -out "${publicPath}"`, {
    stdio: "inherit",
  });
}

console.log("Generating RSA 2048 key pair...");
try {
  execSync("openssl version", { stdio: "ignore" });
  generateWithOpenSSL();
  console.log("(via OpenSSL)");
} catch {
  generateWithNode();
  console.log("(via Node crypto)");
}

console.log("Done.");
console.log("  Private:", privatePath);
console.log("  Public: ", publicPath);
console.log("\nRun: npm run keys:sync-python");
