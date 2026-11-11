// Migrations run once, so credentials set or rotated after the first start are copied from the environment on every start.
onBootstrap((e) => {
  e.next()
  const providers = ["github", "google", "discord"]
    .map((name) => ({
      name,
      clientId: $os.getenv(`PB_OAUTH_${name.toUpperCase()}_CLIENT_ID`),
      clientSecret: $os.getenv(`PB_OAUTH_${name.toUpperCase()}_CLIENT_SECRET`),
    }))
    .filter((provider) => provider.clientId && provider.clientSecret)
  if (providers.length > 0) {
    const users = e.app.findCollectionByNameOrId("users")
    users.oauth2.providers = providers
    e.app.save(users)
  }
})
