/** @param {string} command @param {{writeText: (text: string) => Promise<void>} | undefined} clipboard */
export async function copyCommand(command, clipboard) {
  try {
    if (!clipboard) throw new Error('Clipboard unavailable');
    await clipboard.writeText(command);
    return { ok: true, message: 'Copied' };
  } catch {
    return { ok: false, message: 'Select the command to copy it manually.' };
  }
}
