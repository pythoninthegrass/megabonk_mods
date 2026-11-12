// Site owners are the accounts whose email is in PB_ADMIN_EMAILS; the flag is recomputed on every start and on every account creation.
onBootstrap((e) => {
  e.next()
  const lib = require(`${__hooks}/admins_lib.js`)
  const emails = lib.parseAdminEmails($os.getenv("PB_ADMIN_EMAILS"))
  for (const user of e.app.findAllRecords("users")) {
    const admin = lib.isAdminEmail(emails, user.email())
    if (user.getBool("admin") !== admin) {
      user.set("admin", admin)
      e.app.saveNoValidate(user)
    }
  }
})

onRecordCreate((e) => {
  const lib = require(`${__hooks}/admins_lib.js`)
  e.record.set("admin", lib.isAdminEmail(lib.parseAdminEmails($os.getenv("PB_ADMIN_EMAILS")), e.record.email()))
  e.next()
}, "users")
