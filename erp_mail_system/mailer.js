const nodemailer = require("nodemailer");
require("dotenv").config();

if (!process.env.EMAIL || !process.env.PASS) {
    throw new Error("Missing EMAIL or PASS in .env");
}

const transporter = nodemailer.createTransport({
    service: "gmail",
    auth: {
        user: process.env.EMAIL,
        pass: process.env.PASS,
    },
});

/**
 * Send a vendor order email listing all shortage items.
 * @param {Array<{item_code, description, uom, required, available, shortage}>} shortages
 * @param {string} vendorEmail
 * @param {string} [bomName]   - Optional BOM name that triggered the shortage
 */
async function sendVendorMail(shortages, vendorEmail, bomName = "") {
    const date    = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
    const subject = bomName
        ? `Purchase Order Request — ${bomName} (${shortages.length} item(s))`
        : `Stock Replenishment Order — ${shortages.length} item(s) required`;

    // Plain-text fallback
    const textLines = shortages
        .map(s =>
            `  ${s.item_code} | ${s.description}\n` +
            `    Required: ${s.required} ${s.uom}  |  In Stock: ${s.available} ${s.uom}  |  Order: ${s.shortage} ${s.uom}`
        )
        .join("\n\n");

    const textBody = [
        `Dear Vendor,`,
        ``,
        bomName ? `We are placing a purchase order triggered by production plan: ${bomName}` : `We require the following items to be restocked:`,
        `Date: ${date}`,
        ``,
        `Items Required:`,
        `──────────────────────────────────`,
        textLines,
        `──────────────────────────────────`,
        ``,
        `Please confirm receipt of this order and provide an estimated delivery date.`,
        ``,
        `Regards,`,
        `ERP System — Luminus`,
    ].join("\n");

    // HTML version
    const tableRows = shortages
        .map(s => `
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;font-family:monospace">${s.item_code}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0">${s.description}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center">${s.required} ${s.uom}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center">${s.available} ${s.uom}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:center;color:#e53e3e;font-weight:bold">${s.shortage} ${s.uom}</td>
            </tr>`)
        .join("");

    const htmlBody = `
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f7fafc;font-family:Arial,sans-serif">
      <div style="max-width:680px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

        <!-- Header -->
        <div style="background:#1a202c;padding:24px 32px">
          <h1 style="margin:0;color:#fff;font-size:20px">Purchase Order Request</h1>
          ${bomName ? `<p style="margin:6px 0 0;color:#a0aec0;font-size:13px">Production Plan: <strong style="color:#90cdf4">${bomName}</strong></p>` : ""}
          <p style="margin:4px 0 0;color:#718096;font-size:12px">Generated: ${date}</p>
        </div>

        <!-- Body -->
        <div style="padding:24px 32px">
          <p style="color:#2d3748;margin-top:0">
            ${bomName
                ? `We are unable to fulfil the production run for <strong>${bomName}</strong> due to insufficient stock. Please supply the following items at the earliest.`
                : `Please arrange delivery of the following items to replenish our inventory.`}
          </p>

          <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden">
            <thead>
              <tr style="background:#edf2f7">
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#718096;text-transform:uppercase">Item Code</th>
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#718096;text-transform:uppercase">Description</th>
                <th style="padding:10px 12px;text-align:center;font-size:12px;color:#718096;text-transform:uppercase">Required</th>
                <th style="padding:10px 12px;text-align:center;font-size:12px;color:#718096;text-transform:uppercase">In Stock</th>
                <th style="padding:10px 12px;text-align:center;font-size:12px;color:#e53e3e;text-transform:uppercase">Order Qty</th>
              </tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>

          <p style="color:#4a5568;font-size:13px;margin-top:20px">
            Please confirm receipt and provide an estimated delivery date.<br>
            For queries, reply to this email.
          </p>
        </div>

        <!-- Footer -->
        <div style="background:#f7fafc;padding:16px 32px;border-top:1px solid #e2e8f0">
          <p style="margin:0;color:#a0aec0;font-size:11px">Sent automatically by Luminus ERP System</p>
        </div>
      </div>
    </body>
    </html>`;

    await transporter.sendMail({
        from:    `"Luminus ERP" <${process.env.EMAIL}>`,
        to:      vendorEmail,
        subject,
        text:    textBody,
        html:    htmlBody,
    });

    console.log(`[mailer] Order email sent to ${vendorEmail} | BOM: ${bomName || "N/A"} | ${shortages.length} item(s)`);
}

/**
 * Send a BOM-ready confirmation email to the customer.
 * @param {string} bomName         - BOM that was successfully run
 * @param {number} leadTimeDays    - Expected production lead time
 * @param {string} customerEmail
 * @param {number} quantity        - Number of units ordered
 */
async function sendCustomerMail(bomName, leadTimeDays, customerEmail, quantity = 1) {
    const date    = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
    const weeks   = (leadTimeDays / 7).toFixed(1);
    const subject = `Order Confirmed — ${bomName} is ready for production`;

    const textBody = [
        `Dear Customer,`,
        ``,
        `Great news! Your order for ${bomName} × ${quantity} unit(s) has been confirmed.`,
        ``,
        `All required components are available in our inventory.`,
        `Estimated completion: ${leadTimeDays} days (~${weeks} weeks).`,
        ``,
        `Order details:`,
        `  Product   : ${bomName}`,
        `  Quantity  : ${quantity}`,
        `  Lead time : ${leadTimeDays} days (~${weeks} weeks)`,
        `  Confirmed : ${date}`,
        ``,
        `We will notify you once production is complete and the order is ready to ship.`,
        ``,
        `Regards,`,
        `Luminus ERP`,
    ].join("\n");

    const htmlBody = `
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f0fdf4;font-family:Arial,sans-serif">
      <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">

        <!-- Header -->
        <div style="background:#065f46;padding:24px 32px">
          <h1 style="margin:0;color:#fff;font-size:20px">Order Confirmed ✓</h1>
          <p style="margin:6px 0 0;color:#6ee7b7;font-size:13px">Production plan: <strong>${bomName}</strong></p>
          <p style="margin:4px 0 0;color:#a7f3d0;font-size:12px">${date}</p>
        </div>

        <!-- Body -->
        <div style="padding:28px 32px">
          <p style="color:#1f2937;font-size:15px;margin-top:0">
            Your order for <strong>${bomName}</strong> × <strong>${quantity}</strong> unit(s)
            has been <span style="color:#059669;font-weight:bold">confirmed</span>.
            All required components are available in inventory and production has started.
          </p>

          <!-- Info card -->
          <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:20px;margin:20px 0">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:6px 0;color:#374151;font-size:14px;width:40%">Product</td>
                <td style="padding:6px 0;color:#111827;font-weight:bold;font-size:14px">${bomName}</td>
              </tr>
              <tr>
                <td style="padding:6px 0;color:#374151;font-size:14px">Quantity</td>
                <td style="padding:6px 0;color:#111827;font-weight:bold;font-size:14px">${quantity} unit(s)</td>
              </tr>
              <tr>
                <td style="padding:6px 0;color:#374151;font-size:14px">Estimated Lead Time</td>
                <td style="padding:6px 0;color:#059669;font-weight:bold;font-size:14px">${leadTimeDays} days (~${weeks} weeks)</td>
              </tr>
              <tr>
                <td style="padding:6px 0;color:#374151;font-size:14px">Status</td>
                <td style="padding:6px 0">
                  <span style="background:#d1fae5;color:#065f46;font-size:12px;font-weight:bold;padding:3px 10px;border-radius:99px">In Production</span>
                </td>
              </tr>
            </table>
          </div>

          <p style="color:#6b7280;font-size:13px">
            You will receive another email once production is complete and the order is ready to ship.<br>
            For queries, reply to this email.
          </p>
        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb">
          <p style="margin:0;color:#9ca3af;font-size:11px">Sent automatically by Luminus ERP System</p>
        </div>
      </div>
    </body>
    </html>`;

    await transporter.sendMail({
        from:    `"Luminus ERP" <${process.env.EMAIL}>`,
        to:      customerEmail,
        subject,
        text:    textBody,
        html:    htmlBody,
    });

    console.log(`[mailer] Customer confirmation sent to ${customerEmail} | BOM: ${bomName} × ${quantity} | Lead: ${leadTimeDays}d`);
}

module.exports = { sendVendorMail, sendCustomerMail };
