const controller = ref<undefined | AbortController>()

export function useStep1(step: Ref<number>, handleStep1Next: () => void) {
  const writeStyle = ref('xinhua')
  const event = ref('')
  const eventTitle = ref('')
  const userTitle = ref('')
  const eventAbstract = ref('')
  const isEventError = ref(false)
  const currentUrl = ref('')

  function handleEventSelect(item: { title: string; abstract: string; url: string }) {
    eventTitle.value = item.title
    if (item.abstract.endsWith('...'))
      item.abstract = item.abstract.slice(0, -3)

    eventAbstract.value = item.abstract
    currentUrl.value = item.url
  }

  const userArguments = ref<(UserArgument & { key: number })[]>([
    {
      argument: '', // '好好学习天天向上'
      evidence: '',
      key: 1,
    },
  ])
  const eventPlaceholder = ref('')
  const argumentPlaceholder = ref('')
  const evidencePlaceholder = ref('')

  watch(event, (val) => {
    if (val.trim())
      isEventError.value = false
  })

  const isStep1Change = ref(true)
  watch([event, userArguments, userTitle], (val) => {
    isStep1Change.value = true
  }, { deep: true })

  watch(step, (value, oldValue) => {
    if (value === 2 && oldValue === 1 && isStep1Change.value) {
      isStep1Change.value = false
      handleStep1Next()
    }
  })

  onMounted(async () => {
    // const { data } = await useAiGenRecentEvent()
    // if (data.value) {
    //   eventPlaceholder.value = data.value.result.event_desc
    //   argumentPlaceholder.value = data.value.result.event_argument
    //   evidencePlaceholder.value = data.value.result.event_evidence
    // }
  })

  function clearStep1() {
    event.value = ''
    eventTitle.value = ''
    eventAbstract.value = ''
    userArguments.value = [
      {
        argument: '',
        evidence: '',
        key: 1,
      },
    ]
  }

  const eventCleared = computed(() => {
    if (event.value.endsWith('...'))
      return event.value.slice(0, -3)

    return event.value
  })

  return {
    event,
    eventCleared,
    eventTitle,
    eventAbstract,
    eventPlaceholder,
    isEventError,
    writeStyle,
    userArguments,
    argumentPlaceholder,
    evidencePlaceholder,
    handleEventSelect,
    clearStep1,
    controller,
    isStep1Change,
    userTitle,
    currentUrl,
  }
}

export interface UserArgument { argument: string; evidence: string }

export interface GeneralArgumentType { text: string; isUp: boolean; isDown: boolean; originText: string }

export function useStep2(step: Ref<number>, eventId: Ref<string>, event: Ref<string>, title: Ref<string>, abstract: Ref<string>, userArguments: Ref<UserArgument[]>, userTitle: Ref<string>, next: () => void) {
  const generalArgument = ref({
    // argument: '近期，\"三好学生\"一词再次登上了热搜，对于如何定义一名三好学生，网友们众说纷纭。其实，优秀的三好学生定义很简单，就是要做到德智体全面发展。',
    // argumentFix: '近期，\"三好学生\"一词再次登上了热搜，对于如何定义一名三好学生，网友们众说纷纭。其实，优秀的三好学生定义很简单，就是要做到德智体全面发展。',
    argument: '',
    argumentFix: '',
  })
  provide('generalArgument', generalArgument)
  const structrue = ref('并列式')
  const generalArguments = ref<GeneralArgumentType[][]>([])
  const currentGeneralIndex = ref(-1)
  const currentGeneralSelectedIndex = ref('')
  provide('currentGeneralIndex', currentGeneralIndex)
  provide('currentGeneralSelectedIndex', currentGeneralSelectedIndex)
  const isLoadingGeneralArgument = ref(false)
  provide('isLoadingGeneralArgument', isLoadingGeneralArgument)

  watch(currentGeneralSelectedIndex, (val1) => {
    if (!val1)
      return
    const pos = val1.split(',').map(item => Number(item))
    generalArgument.value.argument = generalArguments.value[pos[0]][pos[1]]?.originText || ''
    generalArgument.value.argumentFix = generalArguments.value[pos[0]][pos[1]]?.text || ''
  })

  async function handleGeneralArgumentRefresh(
    required?: string,
  ) {
    if (generalArguments.value.length >= 5)
      return

    if (isLoadingGeneralArgument.value)
      return
    isLoadingGeneralArgument.value = true
    controller.value?.abort()
    controller.value = new AbortController()
    const res = await useAiGenGeneralArgument({
      event_id: eventId.value,
      event: event.value,
      title: title.value,
      abstract: abstract.value,
      require: required || '',
      user_title: userTitle.value,
      arguments: userArguments.value.map(item => ({ opinion: item.argument, evidence: item.evidence })),
    }, controller.value)

    // const res = {
    //   data: {
    //     value: {
    //       result: [
    //         '总论点1',
    //         '总论点2',
    //         '总论点3',
    //       ],
    //     },
    //   },
    // }
    isLoadingGeneralArgument.value = false
    controller.value = undefined
    if (res.data.value?.result && res.data.value.result.length > 0) {
      const result = res.data.value.result
      generalArguments.value = generalArguments.value.concat([result.map((i) => {
        return {
          text: i,
          isUp: false,
          isDown: false,
          originText: i,
        }
      }).slice(0, 3)])
      currentGeneralIndex.value = generalArguments.value.length - 1
      if (!currentGeneralSelectedIndex.value)
        currentGeneralSelectedIndex.value = `${currentGeneralIndex.value},0`

      return true
    }
    else {
      if (res.error.value?.message.includes('aborted'))
        return false

      ElMessage.error('生成总论点失败，请重新生成')
      return false
    }
  }

  const isStep2Change = ref(true)
  provide('isStep2Change', isStep2Change)
  watch([generalArgument, structrue], () => {
    isStep2Change.value = true
  }, { deep: true })
  watch(step, (value, oldValue) => {
    if (value === 3 && oldValue === 2 && isStep2Change.value) {
      // gen arguments
      if (generalArgument.value.argument.trim() === '' || generalArgument.value.argumentFix.trim() === '') {
        ElMessage.error('请填写总论点')
        return
      }
      isStep2Change.value = false
      next()
    }
  })

  function clearStep2() {
    structrue.value = '并列式'
    currentGeneralIndex.value = -1
    currentGeneralSelectedIndex.value = ''
    generalArgument.value.argument = ''
    generalArgument.value.argumentFix = ''
    generalArguments.value = []
  }

  return {
    generalArgument,
    structrue,
    generalArguments,
    isLoadingGeneralArgument,
    currentGeneralIndex,
    currentGeneralSelectedIndex,
    handleGeneralArgumentRefresh,
    clearStep2,
    controller,
    isStep2Change,
  }
}

export interface ArgumentType { argument: string; isArgumentUp: boolean; isArgumentDown: boolean; evidence: { text: string; isDown: boolean; isUp: boolean }[]; evidenceIndex: number; isUser: boolean; reference_index: number }

export function useStep3(
  step: Ref<number>,
  eventId: Ref<string>,
  body: ComputedRef<{
    event: string
    title: string
    abstract: string
    generalArgument: string
    generalArgumentFix: string
    user_title: string
    arguments: {
      opinion: string
      evidence: string
    }[]
  }>,
) {
  const structrue3 = ref('并列式')
  const generateArguments3 = ref<Record<string, { data: ArgumentType[][]; state: { currentIndex: number; selectedIndex: string[] } }>>({
    并列式: {
      data: [
      ],
      state: {
        currentIndex: -1,
        selectedIndex: [],

      },
    },
    对比式: {
      data: [],
      state: {
        currentIndex: -1,
        selectedIndex: [],

      },
    },
    递进式: {
      data: [],
      state: {
        currentIndex: -1,
        selectedIndex: [],

      },
    },
  })
  const generateArguments = computed(() => {
    return generateArguments3.value[structrue3.value].data
  })

  const argumentsState = computed(() => {
    return generateArguments3.value[structrue3.value].state
  })

  watch(generateArguments, (val) => {
    // if (val.length === 0)
    //   handleGenerateArgumentRefresh()
  })

  function clearStep3() {
    structrue3.value = '并列式'
    generateArguments3.value = {
      并列式: {
        data: [],
        state: {
          currentIndex: -1,
          selectedIndex: [],
        },
      },
      对比式: {
        data: [],
        state: {
          currentIndex: -1,
          selectedIndex: [],
        },
      },
      递进式: {
        data: [],
        state: {
          currentIndex: -1,
          selectedIndex: [],
        },
      },
    }
  }

  const generateArgumentsBody = computed(() => {
    const generate_arguments: any = {}
    let count = 1
    generateArguments.value.forEach((item, i) => {
      item.forEach((item_, j) => {
        generate_arguments[`sub_opinion_${count}`] = {
          opinion: item_.argument,
          evidence: item_.evidence[item_.evidenceIndex]?.text || '',
          status: generateArguments3.value[structrue3.value].state.selectedIndex.includes(`${i},${j}`),
          reference_index: item_.reference_index,
        }
        count += 1
      })
    })
    return generate_arguments
  })

  function genArgumentHistory(generateArguments: ArgumentType[][]) {
    if (generateArguments.length === 0)
      return null

    const history: any = {}

    generateArguments.forEach((item, i) => {
      history[`page_${i + 1}`] = {}

      item.forEach((item_, j) => {
        history[`page_${i + 1}`][`sub_opinion_${j + 1}`] = {
          opinion: item_.argument,
          evidence: item_.evidence[item_.evidenceIndex]?.text || '',
          evidence_history: item_.evidence.map(e => e.text),
          reference_index: item_.reference_index,
          status: generateArguments3.value[structrue3.value].state.selectedIndex.includes(`${i},${j}`),
        }
      })
    })
    return history
  }

  const loadingEvidenceSelectedIndex = ref<string[]>([])
  const controllerEvidence: Ref<{ control: AbortController; index: string }[]> = ref([])
  provide('controllerEvidence', controllerEvidence)
  const isLoadingGenerateArguments = ref<boolean>(false)
  provide('isLoadingGenerateArguments', isLoadingGenerateArguments)

  const isLoadingGenerateArgumentsIndex = ref(-1)
  provide('isLoadingGenerateArgumentsIndex', isLoadingGenerateArgumentsIndex)

  const generateArgumentRequestList = ref<number[]>([])
  async function handleGenerateArgumentRefresh(required?: string) {
    if (isLoadingGenerateArguments.value)
      return

    isLoadingGenerateArgumentsIndex.value = generateArguments.value.length
    isLoadingGenerateArguments.value = true
    controller.value?.abort()
    controller.value = new AbortController()
    const res = await useAiGenArgumentEvidence({
      ...body.value,
      structrue: structrue3.value,
      generate_arguments: generateArgumentsBody.value,
      event_id: eventId.value,
      require: required || '以新华社风格生成',
      argument_history: genArgumentHistory(generateArguments.value),
      current_page: `page_${generateArguments.value.length + 1}`,
    }, controller.value)
    // const res = {
    //   data: {
    //     value: {
    //       result: [
    //         {
    //           opinion: '以色列会胜利吗',
    //           evidence: '',
    //           reference_index: -1,
    //         },
    //         {
    //           opinion: '巴勒斯坦会胜利吗',
    //           evidence: '',
    //           reference_index: -1,
    //         },
    //         {
    //           opinion: '美国会胜利吗',
    //           evidence: '',
    //           reference_index: -1,
    //         },
    //       ],
    //     },
    //   },
    // }
    controller.value = undefined

    if (res.data.value && res.data.value.result.length > 0) {
      let result = res.data.value.result
      const data = generateArguments3.value[structrue3.value].data
      let oldData: ArgumentType[] = []
      generateArguments3.value[structrue3.value].data.forEach((item) => {
        oldData = oldData.concat(item)
      })
      result = result.filter((j) => {
        return !oldData.some(item => item.argument === j.opinion && item.evidence[item.evidenceIndex]?.text === j.evidence)
      })
      generateArguments3.value[structrue3.value].data = data.concat([
        result.map((i) => {
          return {
            argument: i.opinion,
            evidence: i.evidence
              ? [{
                  text: i.evidence, isDown: false, isUp: false,
                }]
              : [],
            evidenceIndex: i.evidence ? 0 : -1,
            isArgumentUp: false,
            isArgumentDown: false,
            isUser: false,
            reference_index: i.reference_index,
          }
        }),
      ])
      const allRes = []
      generateArgumentRequestList.value = []
      for (let i = 0; i < result.length; i++) {
        if (result[i].evidence.length === 0)
          generateArgumentRequestList.value.push(i)
      }

      let isError = false
      while (generateArgumentRequestList.value.length > 0 && !isError) {
        const currentIndex = generateArgumentRequestList.value.shift()!
        const res = await generateEvidence([generateArguments3.value[structrue3.value].data.length - 1, currentIndex])
        isError = !res

        allRes.push(res)
        if (res)
          generateArguments3.value[structrue3.value].state.currentIndex = generateArguments3.value[structrue3.value].data.length - 1
      }

      isLoadingGenerateArguments.value = false
      if (!allRes.every(item => item))
        return false

      generateArguments3.value[structrue3.value].state.currentIndex = generateArguments3.value[structrue3.value].data.length - 1
      return true
    }
    else {
      isLoadingGenerateArguments.value = false
      if (res.error.value?.message.includes('The user aborted a request'))
        return false
      ElMessage.error('生成论点论据失败，请重新生成')
      return false
    }
  }

  provide('loadingEvidenceSelectedIndex', loadingEvidenceSelectedIndex)
  async function generateEvidence(value: [number, number] | [number, number, number]): Promise<boolean> {
    // -1 是手动新增，自动加入
    if (value[2] === -1)
      argumentsState.value.selectedIndex.push(`${value[0]},${value[1]}`)

    loadingEvidenceSelectedIndex.value.push(`${value[0]},${value[1]}`)

    const currentArgument_ = generateArguments.value[value[0]][value[1]]
    const currentArgument = {
      opinion: currentArgument_.argument,
      evidence: currentArgument_.evidence[currentArgument_.evidenceIndex]?.text || '',
      status: generateArguments3.value[structrue3.value].state.selectedIndex.includes(`${value[0]},${value[1]}`),
      reference_index: currentArgument_.reference_index,
      index: `sub_opinion_${value[1] + 1}`,
    }

    const controller = new AbortController()
    controllerEvidence.value.push({ control: controller, index: `${value[0]},${value[1]}` })

    const res = await useAiGenEvidence({
      ...body.value,
      structrue: structrue3.value,
      generate_arguments: generateArgumentsBody.value,
      event_id: eventId.value,
      currentArgument,
      argument_history: genArgumentHistory(generateArguments.value),
      current_page: `page_${value[0] + 1}`,
    }, controller)
    // let res = {
    //   data: {
    //     value: {
    //       result: '',
    //     },
    //   },
    //   error: {
    //     value: null,
    //   },
    // }
    // if (Math.random() > 0.5) {
    //   res = {
    //     data: {
    //       value: {
    //         result: '123',
    //       },
    //     },
    //     error: {
    //       value: null,
    //     },
    //   }
    // }

    loadingEvidenceSelectedIndex.value = loadingEvidenceSelectedIndex.value.filter(item => item !== `${value[0]},${value[1]}`)
    controllerEvidence.value = controllerEvidence.value.filter(item => item.index !== `${value[0]},${value[1]}`)

    if (res.data.value?.result.trim()) {
      currentArgument_.evidence.push({
        text: res.data.value.result,
        isDown: false,
        isUp: false,
      })
      currentArgument_.evidenceIndex = currentArgument_.evidence.length - 1
      return true
    }
    else if (res.data.value?.result.trim() === '' && !res.error.value) {
      const res = await generateEvidence(value)
      return res
    }
    else {
      // if (currentArgument_.evidence.length === 0)
      //   generateArguments.value[value[0]].splice(value[1], 1)

      if (res.error.value?.message.includes('The user aborted a request'))
        return false

      return false
      // const res_ = await generateEvidence(value)
      // return res_
    }
  }

  const isStep3Change = ref(true)
  provide('isStep3Change', isStep3Change)
  watch([structrue3, generateArguments3], () => {
    isStep3Change.value = true
  })

  function generateArticle() {
    if (argumentsState.value.selectedIndex.length === 0) {
      ElMessage.error('请至少选择一个论点')
      return false
    }
    isStep3Change.value = false
    return true
  }

  const isInit = computed(() => {
    if (!generateArguments.value[0])
      return false
    const res = generateArguments.value[0].some((item) => {
      if (item.evidence.length === 0 && !item.isUser)
        return true
      return false
    })
    return !res
  })

  provide('isStep3Init', isInit)

  function clearEmptyEvidence() {
    generateArguments3.value[structrue3.value].data = generateArguments3.value[structrue3.value].data.filter((item) => {
      return !item.some(i => i.evidence.length === 0 && !i.isUser)
    })
  }

  return {
    isLoadingGenerateArguments,
    loadingEvidenceSelectedIndex,
    structrue3,
    generateArguments,
    generateArguments3,
    argumentsState,
    handleGenerateArgumentRefresh,
    generateEvidence,
    clearStep3,
    generateArgumentsBody,
    generateArticle,
    controller,
    controllerEvidence,
    isInit,
    clearEmptyEvidence,
    generateArgumentRequestList,
    genArgumentHistory,
  }
}
