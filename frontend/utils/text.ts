import markdownit from 'markdown-it'
import { convert } from 'html-to-text'

export function fullAngle2halfAngle(str: string) {
  let result = ''
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i)
    // 全角数字和小数点的 Unicode 编码范围是 65296-65305 和 65294
    // 对应的半角数字和小数点的 Unicode 编码范围是 48-57 和 46
    if ((code >= 65296 && code <= 65305) || code === 65294)
      result += String.fromCharCode(code - 65248)

    else
      result += str[i]
  }
  return result
}
const md = markdownit()
const illegalCode = /\[[a-zA-Z0-9]+\]/g
const illegalImg = /\!\([^)]+\)/g

export function md2Text(text: string) {
  text = text.replaceAll(/<xinyu[^>]*\/>/g, '')
  text = text.replace(illegalCode, '')
  const html = md.render(text)
  let txt = convert(html)
  txt = txt.replaceAll(illegalImg, '')
  return txt
}

export function addSpaceToMarkdown(text: string) {
  // 加粗文本，例如 **bold**
  text = text.replace(/(\*\*[^*]+\*\*)/g, ' $1 ')

  // 斜体文本，例如 *italic*
  text = text.replace(/(?<!\*)\*[^*]+\*(?!\*)/g, ' $1 ')

  // 高亮文本，例如 `highlight`
  text = text.replace(/(`[^`]+`)/g, ' $1 ')
  return text
}
