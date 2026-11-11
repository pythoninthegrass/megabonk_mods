// Settings live in the database, so the schedule is re-applied from the environment on every start.
onBootstrap((e) => {
  e.next()
  const settings = e.app.settings()
  settings.backups.cron = $os.getenv("PB_BACKUP_CRON") || "0 3 * * *"
  settings.backups.cronMaxKeep = parseInt($os.getenv("PB_BACKUP_KEEP"), 10) || 7
  e.app.save(settings)
})
