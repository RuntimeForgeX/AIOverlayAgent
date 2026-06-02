/**
 * Copy keys/public.pem into Python src/licensing/public_key.py
 */
const fs = require("fs");
const path = require("path");

const publicPath = path.join(__dirname, "..", "keys", "public.pem");
const pyPath = path.join(
  __dirname,
  "..",
  "..",
  "src",
  "licensing",
  "public_key.py"
);

if (!fs.existsSync(publicPath)) {
  console.error("Run npm run keys:generate first.");
  process.exit(1);
}

const pem = fs.readFileSync(publicPath, "utf8").trim();
const content = `"""
RS256 public key for offline JWT verification.
Auto-synced from license-server/keys/public.pem — run: npm run keys:sync-python
"""

LICENSE_PUBLIC_KEY_PEM = """${pem}"""


def get_license_public_key():
    pem = (LICENSE_PUBLIC_KEY_PEM or "").strip()
    if "REPLACE_WITH" in pem:
        return None
    return pem
`;

fs.writeFileSync(pyPath, content, "utf8");
console.log("Updated:", pyPath);
