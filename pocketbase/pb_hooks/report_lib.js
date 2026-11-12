const COPYRIGHT = "copyright"

const linkNames = (record, target) =>
  record.getString("level") ? `/l/${target.getString("code")}` : `/p/${target.getString("packId")}`

// Lists the parts of a copyright report that are absent or invalid; an empty list means the report is complete.
function missingCopyrightItems(record, target) {
  const missing = []
  if (!["contactEmail", "contactAddress", "contactPhone"].some((name) => record.getString(name).trim())) missing.push("contact")
  if (!record.getString("work").trim()) missing.push("work")
  const link = record.getString("itemUrl").toLowerCase()
  const needle = linkNames(record, target).toLowerCase()
  const at = link.indexOf(needle)
  const after = at < 0 ? "" : link.charAt(at + needle.length)
  if (at < 0 || !(after === "" || "/?#".includes(after))) missing.push("itemUrl")
  for (const name of ["goodFaith", "accurate", "fairUseConsidered"]) {
    if (!record.getBool(name)) missing.push(name)
  }
  if (!record.getString("signature").trim()) missing.push("signature")
  return missing
}

function reportTarget(app, record) {
  const levelId = record.getString("level")
  const packId = record.getString("pack")
  if (Boolean(levelId) === Boolean(packId)) {
    const message = "A report names exactly one level or pack."
    throw new BadRequestError("Invalid report.", { level: new ValidationError("validation_one_target", message) })
  }
  return levelId ? app.findRecordById("levels", levelId) : app.findRecordById("packs", packId)
}

// Fills in the category and status, records what a copyright report lacks, and refuses to call an incomplete one valid.
function prepareReport(app, record) {
  if (!record.getString("category")) record.set("category", "other")
  const target = reportTarget(app, record)
  const copyright = record.getString("category") === COPYRIGHT
  if (!copyright && !record.getString("reason").trim()) {
    throw new BadRequestError("Invalid report.", { reason: new ValidationError("validation_required", "Say what is wrong.") })
  }
  const missing = copyright ? missingCopyrightItems(record, target) : []
  record.set("missing", missing)
  const status = record.getString("status")
  if (status === "valid" && missing.length) {
    const message = `A copyright report cannot be marked valid while it lacks: ${missing.join(", ")}.`
    throw new BadRequestError("Invalid report.", { status: new ValidationError("validation_incomplete_report", message) })
  }
  if (!status || status === "new" || status === "incomplete") record.set("status", missing.length ? "incomplete" : "new")
  return target
}

function noticeText(record, target) {
  const kind = record.getString("level") ? "level" : "pack"
  const title = kind === "level" ? target.getString("title") : target.getString("packId")
  if (record.getString("category") !== COPYRIGHT) {
    return {
      subject: `Your ${kind} "${title}" was hidden`,
      text: `Your ${kind} "${title}" was hidden after a report.\n\nWhat was reported:\n${record.getString("reason")}\n`,
    }
  }
  const contact = [record.getString("signature").trim(), record.getString("contactEmail").trim()].filter(Boolean).join(", ")
  return {
    subject: `Your ${kind} "${title}" was hidden after a copyright report`,
    text:
      `Your ${kind} "${title}" was hidden after a copyright report.\n\n` +
      `The work the reporter says was copied:\n${record.getString("work")}\n\n` +
      `Reporter: ${contact}\n\n` +
      "The reporter's postal address and phone number are not shared.\n",
  }
}

// Hides the reported item and mails its uploader; a failed mail leaves notifiedAt empty so an owner can see it.
function hideAndNotify(app, record, target) {
  target.set("hidden", true)
  app.save(target)
  const { subject, text } = noticeText(record, target)
  try {
    const uploader = app.findRecordById("users", target.getString("author"))
    const meta = app.settings().meta
    app.newMailClient().send(
      new MailerMessage({
        from: { address: meta.senderAddress, name: meta.senderName },
        to: [{ address: uploader.email() }],
        subject,
        text,
      }),
    )
    const now = new DateTime()
    app.db().newQuery("UPDATE reports SET notifiedAt = {:now} WHERE id = {:id}").bind({ now: now.string(), id: record.id }).execute()
    record.set("notifiedAt", now)
  } catch (error) {
    app.logger().error("Could not notify the uploader of a hidden item", "report", record.id, "error", String(error))
  }
}

module.exports = { prepareReport, hideAndNotify }
