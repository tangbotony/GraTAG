import * as htmlparser2 from 'htmlparser2'

function ParsedHtml(props: { content: string }) {
  const { content } = props

  const doc = htmlparser2.parseDocument(content)
  const hElements = htmlToNodes(doc.children as any)

  return h('div', { }, hElements)
}

function getAttrs(node: HTMLElement) {
  const attrs: Record<string, string> = {}
  for (const attr of node.attributes)
    attrs[attr.name] = attr.value
  return attrs
}

function htmlToNodes(nodes: HTMLElement[]): VNode[] {
  return nodes.map((element: HTMLElement) => {
    // 3 is #text, not sure how else to build this one
    if (element.nodeType === 3)
      return h('span', element.nodeValue || '')

    if (element.childNodes.length) {
      const childNodes = Array.from(element.childNodes) as HTMLElement[]
      return h(element.tagName, getAttrs(element), htmlToNodes(childNodes))
    }

    return h(element.tagName, getAttrs(element), element.innerHTML)
  })
}

ParsedHtml.props = ['content']

export default ParsedHtml
