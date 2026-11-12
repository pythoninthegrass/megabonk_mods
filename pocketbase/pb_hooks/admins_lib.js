// Parses a comma separated email list into lowercase addresses.
function parseAdminEmails(text) {
  return (text || "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean)
}

function isAdminEmail(emails, email) {
  return emails.includes((email || "").trim().toLowerCase())
}

module.exports = { parseAdminEmails, isAdminEmail }
