/// <reference path="../pb_data/types.d.ts" />

const PROVIDERS = ["github", "google", "discord"]
const NO_CLIENT_FIELDS =
  "@request.body.code:isset = false && @request.body.downloads:isset = false && @request.body.likes:isset = false && @request.body.hidden:isset = false && @request.body.author:isset = false"
const MAX_IMAGE_BYTES = 8 * 1024 * 1024
const IMAGE_TYPES = ["image/png", "image/jpeg"]

// Only providers whose id and secret are both set are enabled, since PocketBase rejects an empty credential.
function configuredProviders() {
  return PROVIDERS.map((name) => ({
    name,
    clientId: $os.getenv(`PB_OAUTH_${name.toUpperCase()}_CLIENT_ID`),
    clientSecret: $os.getenv(`PB_OAUTH_${name.toUpperCase()}_CLIENT_SECRET`),
  })).filter((provider) => provider.clientId && provider.clientSecret)
}

const timestamps = [
  { name: "created", type: "autodate", onCreate: true },
  { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
]

migrate(
  (app) => {
    const users = app.findCollectionByNameOrId("users")
    users.passwordAuth.enabled = false
    users.createRule = "@request.context = 'oauth2'"
    users.listRule = ""
    users.viewRule = ""
    users.oauth2.enabled = true
    users.oauth2.providers = configuredProviders()
    users.oauth2.mappedFields = { name: "name", avatarURL: "avatar" }
    app.save(users)

    const levels = new Collection({
      type: "base",
      name: "levels",
      listRule: "hidden = false",
      viewRule: "hidden = false",
      createRule: `@request.auth.id != '' && ${NO_CLIENT_FIELDS}`,
      updateRule: `author = @request.auth.id && ${NO_CLIENT_FIELDS}`,
      deleteRule: "author = @request.auth.id",
      fields: [
        { name: "title", type: "text", required: true, max: 200 },
        { name: "description", type: "text", max: 2000 },
        { name: "code", type: "text", required: true, pattern: "^[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}$" },
        { name: "author", type: "relation", required: true, collectionId: users.id, maxSelect: 1, cascadeDelete: true },
        { name: "level", type: "file", required: true, maxSelect: 1, maxSize: 1024 * 1024 },
        { name: "cover", type: "file", required: true, maxSelect: 1, maxSize: MAX_IMAGE_BYTES, mimeTypes: IMAGE_TYPES, thumbs: ["320x0", "640x0"] },
        { name: "biome", type: "file", maxSelect: 1, maxSize: MAX_IMAGE_BYTES, mimeTypes: IMAGE_TYPES },
        { name: "packs", type: "json", maxSize: 20000 },
        { name: "schemaVersion", type: "number", onlyInt: true, min: 1, max: 4 },
        { name: "gameBuildId", type: "text", max: 100 },
        { name: "map", type: "number", onlyInt: true },
        { name: "tags", type: "select", maxSelect: 6, values: ["Speedrun", "Platforming", "Survival", "Puzzle", "Showcase", "Short"] },
        { name: "downloads", type: "number", onlyInt: true, min: 0 },
        { name: "likes", type: "number", onlyInt: true, min: 0 },
        { name: "hidden", type: "bool" },
        ...timestamps,
      ],
      indexes: ["CREATE UNIQUE INDEX idx_levels_code ON levels (code)", "CREATE INDEX idx_levels_created ON levels (created)"],
    })
    app.save(levels)

    const likes = new Collection({
      type: "base",
      name: "likes",
      listRule: "user = @request.auth.id",
      viewRule: "user = @request.auth.id",
      createRule: "@request.auth.id != '' && @request.body.user = @request.auth.id",
      deleteRule: "user = @request.auth.id",
      fields: [
        { name: "user", type: "relation", required: true, collectionId: users.id, maxSelect: 1, cascadeDelete: true },
        { name: "level", type: "relation", required: true, collectionId: levels.id, maxSelect: 1, cascadeDelete: true },
        ...timestamps,
      ],
      indexes: ["CREATE UNIQUE INDEX idx_likes_user_level ON likes (user, level)", "CREATE INDEX idx_likes_level ON likes (level)"],
    })
    app.save(likes)

    const reports = new Collection({
      type: "base",
      name: "reports",
      createRule: "@request.auth.id != '' && @request.body.user = @request.auth.id",
      fields: [
        { name: "user", type: "relation", required: true, collectionId: users.id, maxSelect: 1, cascadeDelete: true },
        { name: "level", type: "relation", required: true, collectionId: levels.id, maxSelect: 1, cascadeDelete: true },
        { name: "reason", type: "text", required: true, max: 1000 },
        ...timestamps,
      ],
    })
    app.save(reports)
  },
  (app) => {
    for (const name of ["reports", "likes", "levels"]) {
      app.delete(app.findCollectionByNameOrId(name))
    }
  },
)
