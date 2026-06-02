const crypto = require("crypto");
const jwt = require("jsonwebtoken");
const { getPrivateKey, getPublicKey } = require("../config/jwt");

const ISSUER = process.env.JWT_ISSUER || "overlay-agent.local";

/**
 * Compute license expiry from plan name.
 * @returns {{ lifetime: boolean, expiresAt: Date|null }}
 */
function planToExpiry(plan) {
  const now = new Date();
  if (plan === "lifetime") {
    return { lifetime: true, expiresAt: null };
  }
  const days = plan === "15days" ? 15 : plan === "30days" ? 30 : 30;
  const expiresAt = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
  return { lifetime: false, expiresAt };
}

/**
 * Raw JWT — issued after admin approval; no device_hash yet.
 */
function generateRawLicenseJWT({ userId, plan, jti }) {
  const { lifetime, expiresAt } = planToExpiry(plan);
  const payload = {
    sub: userId,
    plan,
    jti,
    iss: ISSUER,
    iat: Math.floor(Date.now() / 1000),
  };
  if (lifetime) {
    payload.lifetime = true;
  } else {
    payload.exp = Math.floor(expiresAt.getTime() / 1000);
  }
  return jwt.sign(payload, getPrivateKey(), { algorithm: "RS256" });
}

/**
 * Activated JWT — same claims plus device_hash (Python offline verify).
 */
function generateActivatedLicenseJWT(rawPayload, deviceHash) {
  const payload = {
    sub: rawPayload.sub,
    plan: rawPayload.plan,
    jti: rawPayload.jti,
    iss: rawPayload.iss || ISSUER,
    iat: rawPayload.iat,
    device_hash: deviceHash,
  };
  if (rawPayload.lifetime) {
    payload.lifetime = true;
  } else if (rawPayload.exp) {
    payload.exp = rawPayload.exp;
  }
  return jwt.sign(payload, getPrivateKey(), { algorithm: "RS256" });
}

function verifyJWT(token) {
  return jwt.verify(token, getPublicKey(), {
    algorithms: ["RS256"],
    issuer: ISSUER,
  });
}

function newJti() {
  return crypto.randomUUID();
}

module.exports = {
  ISSUER,
  planToExpiry,
  generateRawLicenseJWT,
  generateActivatedLicenseJWT,
  verifyJWT,
  newJti,
};
