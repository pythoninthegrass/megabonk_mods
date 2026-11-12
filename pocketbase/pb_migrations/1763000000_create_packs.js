/// <reference path="../pb_data/types.d.ts" />

const ADMIN = "@request.auth.admin = true"
const NO_SERVER_FIELDS =
  "@request.body.downloads:isset = false && @request.body.hidden:isset = false && @request.body.viewers:isset = false && @request.body.blocked:isset = false && @request.body.author:isset = false && @request.body.sizeWindows:isset = false && @request.body.sizeLinux:isset = false"
const NOT_BLOCKED = "(@request.auth.id = '' || blocked.id != @request.auth.id)"
const CAN_VIEW = `${ADMIN} || author = @request.auth.id || (hidden = false && ${NOT_BLOCKED}) || (hidden = true && @request.auth.id != '' && viewers.id ?= @request.auth.id)`
const MAX_JSON_BYTES = 256 * 1024
const MAX_PACK_BYTES = 30 * 1024 * 1024

const timestamps = [
  { name: "created", type: "autodate", onCreate: true },
  { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
]

migrate(
  (app) => {
    const users = app.findCollectionByNameOrId("users")
    const packs = new Collection({
      type: "base",
      name: "packs",
      listRule: CAN_VIEW,
      viewRule: CAN_VIEW,
      createRule: `@request.auth.id != '' && @request.body.attested = true && ${NO_SERVER_FIELDS}`,
      updateRule: `${ADMIN} && @request.body.downloads:isset = false && @request.body.author:isset = false && @request.body.sizeWindows:isset = false && @request.body.sizeLinux:isset = false`,
      deleteRule: `author = @request.auth.id || ${ADMIN}`,
      fields: [
        { name: "packId", type: "text", required: true, pattern: "^[a-z0-9][a-z0-9_-]{0,63}$" },
        { name: "version", type: "text", required: true, max: 100 },
        { name: "name", type: "text", max: 200 },
        { name: "description", type: "text", max: 2000 },
        { name: "author", type: "relation", required: true, collectionId: users.id, maxSelect: 1, cascadeDelete: true },
        { name: "manifest", type: "file", required: true, maxSelect: 1, maxSize: MAX_JSON_BYTES },
        { name: "attachments", type: "file", required: true, maxSelect: 1, maxSize: MAX_JSON_BYTES },
        { name: "bundleWindows", type: "file", maxSelect: 1, maxSize: MAX_PACK_BYTES },
        { name: "bundleLinux", type: "file", maxSelect: 1, maxSize: MAX_PACK_BYTES },
        { name: "sizeWindows", type: "number", onlyInt: true, min: 0 },
        { name: "sizeLinux", type: "number", onlyInt: true, min: 0 },
        { name: "assetCount", type: "number", onlyInt: true, min: 0 },
        { name: "attested", type: "bool" },
        { name: "downloads", type: "number", onlyInt: true, min: 0 },
        { name: "hidden", type: "bool" },
        { name: "viewers", type: "relation", collectionId: users.id, maxSelect: 100 },
        { name: "blocked", type: "relation", collectionId: users.id, maxSelect: 100 },
        ...timestamps,
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_packs_id_version ON packs (packId, version)",
        "CREATE INDEX idx_packs_created ON packs (created)",
      ],
    })
    app.save(packs)
  },
  (app) => {
    app.delete(app.findCollectionByNameOrId("packs"))
  },
)
