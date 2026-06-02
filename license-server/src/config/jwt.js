const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

function readKey(filePath, label) {
  const resolved = path.resolve(process.cwd(), filePath);
  if (!fs.existsSync(resolved)) {
    throw new Error(
      `${label} not found at ${resolved}. Run: npm run keys:generate`
    );
  }
  return fs.readFileSync(resolved, "utf8");
}

function readAsymmetricKey(filePath, label, createKey) {
  const key = readKey(filePath, label);
  try {
    const keyObject = createKey(key);
    if (keyObject.asymmetricKeyType !== "rsa") {
      throw new Error(`expected RSA key, got ${keyObject.asymmetricKeyType}`);
    }
  } catch (err) {
    throw new Error(
      `${label} at ${path.resolve(
        process.cwd(),
        filePath
      )} is not a valid RSA PEM key. Run: npm run keys:generate. Details: ${err.message}`
    );
  }
  return key;
}

let _privateKey;
let _publicKey;

function getPrivateKey() {
  if (!_privateKey) {
    _privateKey = readAsymmetricKey(
      process.env.PRIVATE_KEY_PATH || "./keys/private.pem",
      "Private key",
      crypto.createPrivateKey
    );
  }
  return _privateKey;
}

function getPublicKey() {
  if (!_publicKey) {
    _publicKey = readAsymmetricKey(
      process.env.PUBLIC_KEY_PATH || "./keys/public.pem",
      "Public key",
      crypto.createPublicKey
    );
  }
  return _publicKey;
}

module.exports = { getPrivateKey, getPublicKey };
