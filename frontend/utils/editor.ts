import type { Editor } from '@tiptap/vue-3'
import { TextSelection } from '@tiptap/pm/state'
import type { Node as PNode } from '@tiptap/pm/model'
import {
  posToDOMRect,
} from '@tiptap/core'

export function getSelectionPostion(editor: Editor) {
  const rect = posToDOMRect(editor.view, editor.state.selection.from, editor.state.selection.to)
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  }
}

export function clearSpecifiedText(editor: Editor, from: number, to: number, target_text: string) {
  const text = catchTextBetweenError(editor, from, to)
  if (text === target_text) {
    const selection = TextSelection.create(editor.state.doc, from, to)
    const tr = editor.state.tr.setSelection(
      selection,
    ).deleteSelection()

    let beforeFrom, beforeTo
    if (!editor.state.selection.empty) {
      beforeFrom = editor.state.selection.from
      beforeTo = editor.state.selection.to

      beforeFrom = tr.mapping.map(beforeFrom)
      beforeTo = tr.mapping.map(beforeTo)
    }

    editor.chain().focus().setTextSelection(selection).deleteSelection().run()

    if (beforeFrom && beforeTo && beforeFrom !== from && beforeTo !== to)
      selectByFromTo(editor, beforeFrom, beforeTo)
  }
}

export function catchTextBetweenError(editor: Editor, from: number, to: number) {
  try {
    return editor.state.doc.textBetween(from, to)
  }
  catch (e) {
    return null
  }
}

export function selectByFromTo(editor: Editor, from: number, to: number) {
  editor.chain().focus().setTextSelection(TextSelection.create(editor.state.doc, from, to)).run()
}

export function getSelectionContext(editor: Editor) {
  const selection = editor.state.selection
  const text = catchTextBetweenError(editor, selection.from, selection.to) || ''
  const beforeTexts = catchTextBetweenError(editor, 0, selection.from)?.split(/[。；！？;!?]/g) || []
  const afterTexts = catchTextBetweenError(editor, selection.to, editor.state.doc.content.size)?.split(/[。；！？;!?]/g) || []
  let beforeText = ''
  for (let i = beforeTexts.length - 1; i >= 0; i--) {
    if (beforeTexts[i] !== '') {
      beforeText = beforeTexts[i]
      break
    }
  }

  const afterText = afterTexts[0] || ''

  return {
    text,
    beforeText,
    afterText,
  }
}

const splitRegex = /[。；！？;!?]/g
export function selectCurrentSelectionSentence(editor: Editor) {
  const selection = editor.state.selection

  let from = selection.from
  let to = selection.to
  const text = catchTextBetweenError(editor, selection.from, selection.to) || ''
  if (text.length === 0)
    return

  let firstBlock: PNode | undefined
  let firstBlockIndex: number | undefined
  let lastBlock: PNode | undefined
  let lastBlockIndex: number | undefined
  editor.state.doc.nodesBetween(selection.from, selection.to, (node, pos) => {
    let hasText = false
    node.content.forEach((n) => {
      if (n.isText)
        hasText = true
    })
    if (node.isBlock && hasText && !firstBlock) {
      firstBlock = node
      firstBlockIndex = pos
    }

    if (node.isBlock) {
      lastBlock = node
      lastBlockIndex = pos
    }
  })

  let fromRest = false
  firstBlock?.descendants((node, pos) => {
    if (node.isText && node.text && node.text?.length > 0) {
      const text = node.text
      const matches = [...text.matchAll(splitRegex)]
      matches.forEach((match) => {
        if (match.index !== undefined && ((match.index + pos + firstBlockIndex! + 1) < selection.from)) {
          from = match.index + pos + firstBlockIndex! + 2
          fromRest = true
        }
      })
    }
  })

  if (!fromRest)
    from = firstBlockIndex! + 1

  // deal with the quote and "
  let from_ = from
  let to_ = from_ + 1
  let condition = true
  while (condition) {
    const text = catchTextBetweenError(editor, from_, to_)
    if ((text?.length === 0 || text === ' ' || text === '“' || text === '”' || text === '"') && (from_ < selection.from)) {
      ++from_
      ++to_
    }
    else {
      condition = false
    }
  }

  from = from_

  let toRest = false

  if (editor.state.doc.nodeAt(to - 1)?.type.name === 'quote')
    toRest = true

  if (!toRest) {
    lastBlock?.descendants((node, pos) => {
      if (node.isText && node.text && node.text?.length > 0 && !toRest) {
        const text = node.text
        const matches = [...text.matchAll(splitRegex)]

        for (let i = 0; i < matches.length; i++) {
          const match = matches[i]
          if (match.index !== undefined && ((match.index + pos + lastBlockIndex! + 2) >= selection.to)) {
            to = match.index + pos + lastBlockIndex! + 2
            toRest = true
            break
          }
        }
      }
    })
  }

  if (!toRest)
    to = lastBlockIndex! + lastBlock!.nodeSize - 1

  const selection2 = TextSelection.create(editor.state.doc, from, to)
  editor.chain().setTextSelection(selection2).run()
}

let latestArticle = ''
let latestArticleCount = 0

let latestArticleWithSpaces = ''
let latestArticleCountWithSpaces = 0

let latestArticleDistinguishCE = ''
let latestArticleCountDistinguishCE = 0

let latestArticleParagraphs = ''
let latestArticleCountParagraphs = 0

const chineseRegex = /[\u4E00-\u9FA5]/
const englishRegex = /[a-zA-Z]/
const numberRegex = /\d/
const spaceRegex = /\s/

export function countWords(article?: string) {
  if (!article)
    return 0

  if (article === latestArticle)
    return latestArticleCount

  let count = 0
  for (let i = 0; i < article.length; i++) {
    const currentChar = article[i]

    // 检查当前字符是否是中英文字符
    if (chineseRegex.test(currentChar) || englishRegex.test(currentChar) || numberRegex.test(currentChar))
      count++
  }

  latestArticleCount = count || 0
  latestArticle = article
  return latestArticleCount
}

export function countWordsDistinguishCE(article?: string) {
  if (!article)
    return 0
  if (article === latestArticleDistinguishCE)
    return latestArticleCountDistinguishCE

  let count = 0
  let currentChar
  let prevChar

  for (let i = 0; i < article.length; i++) {
    currentChar = article[i]

    if (chineseRegex.test(currentChar) || numberRegex.test(currentChar))
      count++

    if (englishRegex.test(currentChar)) {
      if (prevChar && englishRegex.test(prevChar)) {
        continue
      }
      else {
        // 如果前一个字符不是数字，则根据数字长度增加计数
        count++
      }
    }

    prevChar = currentChar
  }

  // 返回匹配结果数组的长度，即为文章中的字数（不包括空格）
  latestArticleCountDistinguishCE = count
  latestArticleDistinguishCE = article
  return latestArticleCountDistinguishCE
}

export function countParagraphs(article?: string) {
  if (!article)
    return 0

  if (article === latestArticleParagraphs)
    return latestArticleCountParagraphs
  // 使用正则表达式匹配段落分隔符
  // 在这个示例中，我们假设段落之间是通过换行符或连续的换行符分隔的
  // 如果有其他段落分隔符，请相应地修改正则表达式
  const paragraphSeparatorRegex = /[\r\n]+/

  // 使用段落分隔符将文章拆分成段落数组
  const paragraphs = article.split(paragraphSeparatorRegex)

  // 过滤掉空段落
  const nonEmptyParagraphs = paragraphs.filter(paragraph => paragraph.trim() !== '')

  // 返回非空段落数量
  latestArticleCountParagraphs = nonEmptyParagraphs.length
  latestArticleParagraphs = article
  return latestArticleCountWithSpaces
}

export function countWordsWithSpaces(article?: string) {
  if (!article)
    return 0

  if (article === latestArticleWithSpaces)
    return latestArticleCountWithSpaces

  let count = 0
  for (let i = 0; i < article.length; i++) {
    const currentChar = article[i]

    // 检查当前字符是否是中英文字符
    if (chineseRegex.test(currentChar) || englishRegex.test(currentChar)
    || numberRegex.test(currentChar) || spaceRegex.test(currentChar))
      count++
  }

  // 返回匹配结果数组的长度，即为文章中的字数（包括空格）
  latestArticleCountWithSpaces = count
  latestArticleWithSpaces = article
  return latestArticleCountWithSpaces
}
