const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      try {
        detail = await res.text()
      } catch {
        // ignore
      }
    }
    throw new Error(detail || `API ${res.status}: ${path}`)
  }
  return res.json() as Promise<T>
}
