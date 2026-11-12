// PocketBase already sends nosniff, X-Frame-Options and COOP; these are the headers it leaves out.
routerUse((e) => {
  const header = e.response.header()
  header.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
  header.set("Referrer-Policy", "strict-origin-when-cross-origin")
  header.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
  // The site on the apex loads gallery images from this host, which is the same site but another origin.
  header.set("Cross-Origin-Resource-Policy", "same-site")
  return e.next()
})
