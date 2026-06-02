const express = require("express");
const admin = require("../controllers/admin.controller");
const { requireAdmin } = require("../middleware/isAdmin");
const { asyncHandler } = require("../utils/asyncHandler");

const router = express.Router();

router.get("/admin", requireAdmin, asyncHandler(admin.dashboard));
router.get("/admin/licenses", requireAdmin, asyncHandler(admin.licensesPage));
router.post("/admin/requests/:id/approve", requireAdmin, asyncHandler(admin.approveRequest));
router.post("/admin/requests/:id/reject", requireAdmin, asyncHandler(admin.rejectRequest));
router.post("/admin/licenses/:id/revoke", requireAdmin, asyncHandler(admin.revokeLicense));
router.post("/admin/devices/:id/unbind", requireAdmin, asyncHandler(admin.unbindDevice));

module.exports = router;
