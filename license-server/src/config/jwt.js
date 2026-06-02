const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

/** Repo root (license-server/), stable in local dev and Vercel /var/task. */
const PROJECT_ROOT = path.join(__dirname, "..", "..");

function resolveKeyPath(filePath) {
  if (!filePath) return null;
  if (path.isAbsolute(filePath)) return filePath;
  return path.join(PROJECT_ROOT, filePath.replace(/^\.\//, ""));
}

function readKeyFromEnv(envVarName) {
  const raw = process.env[envVarName];
  if (!raw) return null;
  return raw.replace(/\\n/g, "\n").trim();
}

function readKey(filePath, label, envPemVar) {
  const fromEnv = readKeyFromEnv(envPemVar);
  if (fromEnv) return fromEnv;

  const resolved = resolveKeyPath(filePath);
  if (!resolved || !fs.existsSync(resolved)) {
    throw new Error(
      `${label} not found. Set ${envPemVar} in Vercel env, or place the key at ${resolved || filePath}. Local: npm run keys:generate`
    );
  }
  return fs.readFileSync(resolved, "utf8");
}

function readAsymmetricKey(filePath, label, createKey, envPemVar) {
  const key = readKey(filePath, label, envPemVar);
  const resolved = resolveKeyPath(filePath);
  try {
    const keyObject = createKey(key);
    if (keyObject.asymmetricKeyType !== "rsa") {
      throw new Error(`expected RSA key, got ${keyObject.asymmetricKeyType}`);
    }
  } catch (err) {
    const location = readKeyFromEnv(envPemVar)
      ? `${envPemVar} (environment)`
      : resolved;
    throw new Error(
      `${label} at ${location} is not a valid RSA PEM key. Run: npm run keys:generate. Details: ${err.message}`
    );
  }
  return key;
}

let _privateKey;
let _publicKey;

function getPrivateKey() {
  if (!_privateKey) {
    _privateKey = readAsymmetricKey(
      process.env.PRIVATE_KEY_PATH || "keys/private.pem",
      "Private key",
      crypto.createPrivateKey,
      "PRIVATE_KEY"
    );
  }
  return _privateKey;
}

function getPublicKey() {
  if (!_publicKey) {
    _publicKey = readAsymmetricKey(
      process.env.PUBLIC_KEY_PATH || "keys/public.pem",
      "Public key",
      crypto.createPublicKey,
      "PUBLIC_KEY"
    );
  }
  return _publicKey;
}

module.exports = { getPrivateKey, getPublicKey };
