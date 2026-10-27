// OWNER: A (potencialbg). Low-data mode (Tier 2 item 11, D36): for capped or slow connections. On, it plays the
// commentary from the 32 kbps copies (audio/<lang>/radio-lo/), fetches each line only shortly before it is needed
// instead of the whole track at Start, and loads one recording of each crowd reaction instead of up to six.
// Automatic when the browser says so (Save-Data, or a 2G/3G connection); the Setup switch overrides it.
export interface ConnectionLike { saveData?: boolean; effectiveType?: string }

export function autoLowData(conn: ConnectionLike | undefined =
  (typeof navigator !== 'undefined' ? (navigator as Navigator & { connection?: ConnectionLike }).connection : undefined)): boolean {
  return !!conn && (conn.saveData === true || ['slow-2g', '2g', '3g'].includes(conn.effectiveType ?? ''));
}

/** The fan's choice wins; with none (null), the browser's hint decides. */
export const lowDataOn = (choice: boolean | null, conn?: ConnectionLike): boolean => choice ?? autoLowData(conn);

/** "audio/en/radio/<sha>.mp3" -> "audio/en/radio-lo/<sha>.mp3" (same name, smaller file). */
export const lowUrl = (url: string): string => url.replace(/\/radio\//, '/radio-lo/');
