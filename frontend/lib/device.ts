const COOKIE_KEY = "ysat_device_id";

function generateId(): string {
  return crypto.randomUUID();
}

export function getDeviceId(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_KEY}=([^;]+)`));
  if (match) return match[1];
  const id = generateId();
  document.cookie = `${COOKIE_KEY}=${id}; max-age=31536000; path=/; SameSite=Lax`;
  return id;
}
