export function getDistanceToFirstScrollYParent(element: HTMLElement) {
  let parent = element.offsetParent as HTMLElement
  let left = element.offsetLeft
  let top = element.offsetTop
  while (parent && parent !== document.body) {
    if (window.getComputedStyle(parent).overflowY !== 'scroll' && window.getComputedStyle(parent).overflowY !== 'auto') {
      left += parent.offsetLeft
      top += parent.offsetTop

      parent = parent.offsetParent as HTMLElement
    }
    else {
      break
    }
  }

  return { left, top }
}

export function getDomHeight(element: HTMLElement) {
  const style = window.getComputedStyle(element)
  const height = element.clientHeight - Number.parseFloat(style.paddingTop) - Number.parseFloat(style.paddingBottom)
  return height
}
