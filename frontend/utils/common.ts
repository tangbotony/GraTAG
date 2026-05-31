import { v4 as uuidv4 } from 'uuid'

export function isWindows() {
  return navigator.platform.toUpperCase().includes('WIN')
}

export function isMac() {
  return navigator.platform.toUpperCase().includes('MAC')
}

export function searchAll(query: string, text: string) {
  const query_ = escapeRegexSpecial(query)
  const regex = new RegExp(query_, 'gi')
  const matches = [...text.matchAll(regex)]
  const results = matches.map((match) => {
    if (match.index !== undefined)
      return match.index + query.length

    return undefined
  }).filter(i => i !== undefined)
  return results as number[]
}

export function removeDuplicatesByProperty(array: { [key: string]: any }[], property: string) {
  const uniqueValues = new Map()
  return array.filter((item) => {
    const value = item[property]
    if (!uniqueValues.has(value)) {
      uniqueValues.set(value, true)
      return true
    }
    return false
  })
}
export function getRandomString() {
  return uuidv4()
}

function escapeRegexSpecial(str: string) {
  return str.replace(/[.+*?^${}()|[\]\\]/g, '\\$&')
}

export function typewriter(text: string, cb: (val: string) => void, speed = 50) {
  if (text.length === 0)
    return

  const start = 0
  let end = speed
  return new Promise((resolve) => {
    const id = setInterval(async () => {
      await cb(text.slice(start, end))
      if (end >= text.length) {
        clearInterval(id)
        resolve(true)
        return
      }
      end += speed
    }, 100)
  })
}

export function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function countdown(callback: (second: number) => void, duration = 2 * 60) {
  const startTime = Date.now()
  const endTime = startTime + duration * 1000
  let close = false

  const updateProgress = () => {
    const now = Date.now()
    const elapsed = endTime - now
    let second = Math.floor(elapsed / 1000)
    if (second < 2)
      second = 2

    callback(second)

    if ((now < endTime) && !close)
      requestAnimationFrame(updateProgress)
  }

  requestAnimationFrame(updateProgress)

  // return a function to stop the progress simulation
  return () => {
    close = true
  }
}

function escapeRegExp(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function safeReplace(content: string, target: string, replacement: string) {
  const escapedTarget = escapeRegExp(target)
  const regex = new RegExp(escapedTarget)
  return content.replace(regex, replacement)
}
