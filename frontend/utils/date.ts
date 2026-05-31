export function getTimeStatus(date: Date) {
  const now = new Date()
  const year = date.getFullYear()
  const month = date.getMonth()
  const day = date.getDate()

  if (year === now.getFullYear()) {
    if (month === now.getMonth() && day === now.getDate())
      return 'today'

    else
      return 'currentyear'
  }
  else {
    return 'beforeyear'
  }
}

export function formatDateNumber(value: number) {
  return String(value).padStart(2, '0')
}

export function time2String(date: string) {
  const obj = time2Object(date)
  const year = obj.year
  const month = obj.month ? `.${obj.month}` : ''
  const day = obj.day ? `.${obj.day}` : ''

  return `${year}${month}${day}`
}

export function time2Object(date: string) {
  const isBC = date.startsWith('-')
  if (isBC)
    date = date.substring(1)

  date = date.trim()
  const dates = date.split('-')
  const d = new Date(date)
  let year = dates[0] ? `${d.getFullYear()}` : ''
  if (isBC)
    year = `公元前${year}`
  const month = dates[1] ? `${formatDateNumber(d.getMonth() + 1)}` : ''
  const day = dates[2] ? `${formatDateNumber(d.getDate())}` : ''
  return {
    year,
    month,
    day,
  }
}

export function timeStamp2String(time: string) {
  const date = new Date(Number(time))
  return `${date.getFullYear()}-${formatDateNumber(date.getMonth() + 1)}-${formatDateNumber(date.getDate())} ${formatDateNumber(date.getHours())}:${formatDateNumber(date.getMinutes())}:${formatDateNumber(date.getSeconds())}`
}
