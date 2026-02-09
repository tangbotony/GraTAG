function number2txt(number: number, unit: number) {
  if (number <= unit)
    return number

  const num = Math.floor(number / unit)
  const unitText: Record<number, string> = {
    100000000: '亿',
    10000: '万',
    1000: '千',
    100: '百',
    10: '十',
  }
  return num + unitText[unit]
}

export { number2txt }
