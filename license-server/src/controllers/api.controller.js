/**
 * POST /api/activate — called by the Python desktop app.
 * Binds raw JWT to device_hash and returns activated JWT.
 */
const { prisma } = require("../config/database");
const {
  generateActivatedLicenseJWT,
  verifyJWT,
} = require("../services/jwt.service");
const { sanitizeString } = require("../utils/helpers");

async function activate(req, res) {
  try {
    const raw_jwt = sanitizeString(req.body.raw_jwt, 8192);
    const device_hash = sanitizeString(req.body.device_hash, 128);
    const device_info = req.body.device_info || null;

    if (!raw_jwt || !device_hash) {
      return res.status(400).json({
        error: "raw_jwt and device_hash are required.",
      });
    }

    let payload;
    try {
      payload = verifyJWT(raw_jwt);
    } catch (err) {
      return res.status(400).json({ error: `Invalid license key: ${err.message}` });
    }

    if (payload.device_hash) {
      return res.status(400).json({
        error: "This key is already activated. Use your activated license file.",
      });
    }

    const jti = payload.jti;
    if (!jti) {
      return res.status(400).json({ error: "License missing jti claim." });
    }

    const license = await prisma.license.findUnique({
      where: { jti },
      include: { devices: true },
    });

    if (!license) {
      return res.status(404).json({ error: "License not found." });
    }

    if (license.revoked) {
      return res.status(403).json({ error: "License has been revoked." });
    }

    if (!payload.lifetime) {
      const expMs = payload.exp ? payload.exp * 1000 : null;
      if (expMs && Date.now() > expMs) {
        return res.status(403).json({ error: "License has expired." });
      }
      if (license.expiresAt && new Date() > license.expiresAt) {
        return res.status(403).json({ error: "License has expired." });
      }
    }

    const existingByHash = await prisma.device.findUnique({
      where: { deviceHash: device_hash },
      include: { license: true },
    });

    if (existingByHash) {
      if (existingByHash.licenseId === license.id) {
        const activated_jwt = generateActivatedLicenseJWT(payload, device_hash);
        return res.json({ activated_jwt });
      }
      return res.status(409).json({
        error: "This device is already bound to another license.",
      });
    }

    const otherDevice = license.devices.find((d) => d.deviceHash !== device_hash);
    if (otherDevice) {
      return res.status(409).json({
        error:
          "License is already activated on another device. Ask admin to unbind first.",
      });
    }

    await prisma.device.create({
      data: {
        licenseId: license.id,
        deviceHash: device_hash,
        deviceInfo: device_info,
      },
    });

    const activated_jwt = generateActivatedLicenseJWT(payload, device_hash);
    return res.json({ activated_jwt });
  } catch (err) {
    console.error("[api/activate]", err);
    return res.status(500).json({ error: "Internal server error." });
  }
}

module.exports = { activate };
