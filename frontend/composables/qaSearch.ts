import type { UploadUserFile } from 'element-plus'
import { QaMode, useQaStore } from '~/store/qa'

function useQaSearch(searchMode: Ref<string>, fileList: Ref<UploadUserFile[]>) {
  const search = ref('')
  const recomData = ref<{ id: string; type: 'history' | 'recom'; value: string }[]>([])
  const fullScreen = ref(false)
  const filterrecomData = computed(() => {
    if (search.value.trim().length > 50)
      return []

    return recomData.value.slice(0, 6)
  })
  const searchState = ref<'normal' | 'error' | 'empty'>('empty')

  watch(search, (value) => {
    if (value.trim().length > 10000)
      searchState.value = 'error'
    else if (value.trim().length === 0)
      searchState.value = 'empty'
    else if (value.trim().length <= 10000)
      searchState.value = 'normal'
  })

  function handleDeleteRecomItem(id: string) {
    recomData.value = recomData.value.filter(item => item.id !== id)
    useDeleteQaSearchHistory(id)
  }

  function handleClearAllRecom() {
    recomData.value = []
    useDeleteQaSearchHistories()
  }

  const handleSearch = useDebounceFn(async (value: string) => {
    if (searchMode.value !== QaMode.WEB)
      return
    if (value.trim().length === 0)
      return
    if (value.trim().length > 50)
      return
    const { data, error } = await useGetQaSearchCompletion(value)
    if (error.value || !data.value?.results)
      return
    recomData.value = data.value?.results.map((i, index) => ({
      id: `${index}`,
      type: 'recom',
      value: i,
    }))
  }, 300)

  function handleOutside() {
    if (search.value.trim().length === 0)
      recomData.value = []
  }

  async function handleFocus() {
    if (search.value.trim().length > 0)
      return
    if (recomData.value.length > 0)
      return

    if (QaMode.WEB !== searchMode.value)
      return

    const { data, error } = await useGetQaSearchHistory()
    if (error.value || !data.value?.results)
      return

    data.value.results.sort((x, y) => {
      return new Date(y.create_time).getTime() - new Date(x.create_time).getTime()
    })
    recomData.value = data.value?.results.map(i => ({
      id: i._id,
      type: 'history',
      value: i.title,
    }))
  }

  const { data: bestRecomOrigindata, error: bestRecomError } = useGetQaSearchRecom()

  const bestRecomdata = computed(() => {
    if (bestRecomError.value)
      return []

    return bestRecomOrigindata.value?.results || []
  })

  const store = useQaStore()
  const { setFirstQuery } = store
  const router = useRouter()
  async function handleAsk() {
    if (search.value.trim().length === 0)
      return
    if (search.value.trim().length > 10000)
      return

    if (searchMode.value === QaMode.DOC) {
      if (fileList.value.length === 0) {
        const dom = document.getElementById('search-container') as HTMLElement
        ElMessage({
          type: 'error',
          message: '请上传文件',
          appendTo: dom,
          customClass: '!absolute',
        })
        return
      }

      const isLoading = fileList.value.some((i: any) => i.status === 'uploading')
      if (isLoading) {
        const dom = document.getElementById('search-container') as HTMLElement
        ElMessage({
          type: 'error',
          message: '文件未上传完毕，暂不可发起搜索',
          appendTo: dom,
          customClass: '!absolute',
        })
        return
      }
    }

    if (searchMode.value === QaMode.WEB)
      setFirstQuery(search.value, QaMode.WEB)
    else
      setFirstQuery(search.value, QaMode.DOC, fileList.value.map((i: any) => i.response.doc_id))

    await new Promise(resolve => setTimeout(resolve, 100))
    router.push('/qa')
  }

  function handleRecomSelect(value: string) {
    search.value = value
    handleAsk()
  }
  watch(searchMode, (val) => {
    search.value = ''
  })

  return {
    search,
    recomData,
    fullScreen,
    filterrecomData,
    searchState,
    handleDeleteRecomItem,
    handleClearAllRecom,
    handleSearch,
    handleOutside,
    handleFocus,
    bestRecomdata,
    handleRecomSelect,
    handleAsk,
  }
}

export {
  useQaSearch,
}
