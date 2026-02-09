export function isEmail(value: string) {
  value = value.trim()
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return regex.test(value)
}
