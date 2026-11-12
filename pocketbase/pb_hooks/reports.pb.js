onRecordCreate((e) => {
  require(`${__hooks}/report_lib.js`).prepareReport(e.app, e.record)
  e.next()
}, "reports")

onRecordUpdate((e) => {
  const lib = require(`${__hooks}/report_lib.js`)
  const target = lib.prepareReport(e.app, e.record)
  const becomesValid = e.record.getString("status") === "valid" && e.record.original().getString("status") !== "valid"
  e.next()
  if (becomesValid) lib.hideAndNotify(e.app, e.record, target)
}, "reports")
