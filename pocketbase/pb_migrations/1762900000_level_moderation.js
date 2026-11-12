/// <reference path="../pb_data/types.d.ts" />

const ADMIN = "@request.auth.admin = true"
const NO_SERVER_FIELDS =
  "@request.body.code:isset = false && @request.body.downloads:isset = false && @request.body.likes:isset = false && @request.body.author:isset = false"
const NO_MODERATION_FIELDS =
  "@request.body.hidden:isset = false && @request.body.viewers:isset = false && @request.body.blocked:isset = false"
const NOT_BLOCKED = "(@request.auth.id = '' || blocked.id != @request.auth.id)"
const CAN_VIEW = `${ADMIN} || author = @request.auth.id || (hidden = false && ${NOT_BLOCKED}) || (hidden = true && @request.auth.id != '' && viewers.id ?= @request.auth.id)`

migrate(
  (app) => {
    const users = app.findCollectionByNameOrId("users")
    users.fields.add(new BoolField({ name: "admin" }))
    users.updateRule = "id = @request.auth.id && @request.body.admin:isset = false"
    app.save(users)

    // The admins hook runs before migrations on the start that adds the field, so existing owners are flagged here.
    const emails = ($os.getenv("PB_ADMIN_EMAILS") || "").split(",").map((email) => email.trim().toLowerCase())
    for (const user of app.findAllRecords("users")) {
      if (emails.includes(user.email().toLowerCase())) {
        user.set("admin", true)
        app.saveNoValidate(user)
      }
    }

    const levels = app.findCollectionByNameOrId("levels")
    for (const name of ["viewers", "blocked"]) {
      levels.fields.add(new RelationField({ name, collectionId: users.id, maxSelect: 100 }))
    }
    levels.listRule = CAN_VIEW
    levels.viewRule = CAN_VIEW
    levels.updateRule = `(author = @request.auth.id && ${NO_SERVER_FIELDS} && ${NO_MODERATION_FIELDS}) || (${ADMIN} && ${NO_SERVER_FIELDS})`
    levels.deleteRule = `author = @request.auth.id || ${ADMIN}`
    app.save(levels)
  },
  (app) => {
    const levels = app.findCollectionByNameOrId("levels")
    levels.listRule = "hidden = false"
    levels.viewRule = "hidden = false"
    levels.updateRule = `author = @request.auth.id && ${NO_SERVER_FIELDS} && ${NO_MODERATION_FIELDS}`
    levels.deleteRule = "author = @request.auth.id"
    levels.fields.removeByName("viewers")
    levels.fields.removeByName("blocked")
    app.save(levels)

    const users = app.findCollectionByNameOrId("users")
    users.updateRule = "id = @request.auth.id"
    users.fields.removeByName("admin")
    app.save(users)
  },
)
