const FINGERPRINT_KEY = 'resurag_browser_fingerprint';
export const FINGERPRINT_HEADER = 'X-Browser-Fingerprint';

export function getBrowserFingerprint(): string {
  let fingerprint = localStorage.getItem(FINGERPRINT_KEY);
  if (!fingerprint) {
    fingerprint = crypto.randomUUID();
    localStorage.setItem(FINGERPRINT_KEY, fingerprint);
  }
  return fingerprint;
}

export function withFingerprintHeaders(headers?: HeadersInit): HeadersInit {
  const next = new Headers(headers ?? undefined);
  next.set(FINGERPRINT_HEADER, getBrowserFingerprint());
  return next;
}
