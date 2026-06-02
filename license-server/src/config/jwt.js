const fs = require("fs");
const path = require("path");

function readKey(filePath, label) {
  const resolved = path.resolve(process.cwd(), filePath);
  if (!fs.existsSync(resolved)) {
    throw new Error(
      `${label} not found at ${resolved}. Run: npm run keys:generate`
    );
  }
  return fs.readFileSync(resolved, "utf8");
}

let _privateKey;
let _publicKey;

function getPrivateKey() {
  if (!_privateKey) {
    _privateKey = readKey(
      process.env.PRIVATE_KEY_PATH || "./keys/private.pem",
      "Private key"
    );
  }
  return _privateKey;
}

function getPublicKey() {
  if (!_publicKey) {
    _publicKey = readKey(
      process.env.PUBLIC_KEY_PATH || "./keys/public.pem",
      "Public key"
    );
  }
  return _publicKey;
}

module.exports = { getPrivateKey, getPublicKey };
