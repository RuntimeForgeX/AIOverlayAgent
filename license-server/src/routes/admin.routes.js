const express = require("express");
const admin = require("../controllers/admin.controller");
const { requireAdmin } = require("../middleware/isAdmin");

const router = express.Router();

router.get("/admin", requireAdmin, admin.dashboard);
router.get("/admin/licenses", requireAdmin, admin.licensesPage);
router.post("/admin/requests/:id/approve", requireAdmin, admin.approveRequest);
router.post("/admin/requests/:id/reject", requireAdmin, admin.rejectRequest);
router.post("/admin/licenses/:id/revoke", requireAdmin, admin.revokeLicense);
router.post("/admin/devices/:id/unbind", requireAdmin, admin.unbindDevice);

module.exports = router;
