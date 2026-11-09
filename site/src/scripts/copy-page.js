/** @param {string} url @param {{clipboard?: Pick<Clipboard, 'writeText'>, document: Document, fetcher?: typeof fetch}} options */
export async function copyPage(url, { clipboard, document, fetcher = fetch }) {
  const response = await fetcher(url);
  if (!response.ok) throw new Error(`Markdown answered ${response.status}`);
  const text = await response.text();
  if (clipboard?.writeText) {
    try {
      await clipboard.writeText(text);
      return;
    } catch { /* Fall back when clipboard permissions are denied. */ }
  }
  const previous = document.activeElement;
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.cssText = 'position:fixed;top:-1000px;opacity:0';
  document.body.appendChild(textarea);
  try {
    textarea.focus();
    textarea.select();
    if (!document.execCommand('copy')) throw new Error('Clipboard unavailable');
  } finally {
    textarea.remove();
    if (previous && 'focus' in previous && typeof previous.focus === 'function') previous.focus();
  }
}
