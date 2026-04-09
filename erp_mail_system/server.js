const express = require("express");
const cors    = require("cors");
const { sendVendorMail, sendCustomerMail } = require("./mailer");

const app = express();
app.use(cors());
app.use(express.json());

// GET /health
app.get("/health", (_req, res) => res.json({ status: "ok" }));

/**
 * POST /send-vendor-email
 * Body: {
 *   shortages:    [{item_code, description, uom, required, available, shortage}],
 *   vendor_email: string,
 *   bom_name:     string  (optional — included in subject & body when provided)
 * }
 */
app.post("/send-vendor-email", async (req, res) => {
    const { shortages, vendor_email, bom_name = "" } = req.body;

    if (!Array.isArray(shortages) || shortages.length === 0) {
        return res.status(400).json({ error: "shortages must be a non-empty array." });
    }
    if (!vendor_email) {
        return res.status(400).json({ error: "vendor_email is required." });
    }

    try {
        await sendVendorMail(shortages, vendor_email, bom_name);
        res.json({
            success: true,
            message: `Order email sent to ${vendor_email} for ${shortages.length} item(s).`,
        });
    } catch (err) {
        console.error("[server] Mail error:", err.message);
        res.status(500).json({ error: err.message });
    }
});

/**
 * POST /send-customer-confirmation
 * Body: {
 *   bom_name:       string,
 *   lead_time_days: number,
 *   customer_email: string,
 *   quantity:       number  (optional, default 1)
 * }
 */
app.post("/send-customer-confirmation", async (req, res) => {
    const { bom_name, lead_time_days, customer_email, quantity = 1 } = req.body;

    if (!bom_name)       return res.status(400).json({ error: "bom_name is required." });
    if (!customer_email) return res.status(400).json({ error: "customer_email is required." });
    if (!lead_time_days) return res.status(400).json({ error: "lead_time_days is required." });

    try {
        await sendCustomerMail(bom_name, lead_time_days, customer_email, quantity);
        res.json({
            success: true,
            message: `Confirmation email sent to ${customer_email} for ${bom_name} × ${quantity}.`,
        });
    } catch (err) {
        console.error("[server] Customer mail error:", err.message);
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Mailer service running on port ${PORT}`));
