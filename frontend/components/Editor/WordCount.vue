<script setup lang="ts">
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{
  editor: Editor | undefined
}>()

const items = computed(() => {
  return [
    { label: '字数', type: 'words', value: countWords(props.editor?.getText()) },
    { label: '字+空格', type: 'wordsSpace', value: countWordsWithSpaces(props.editor?.getText()) },
    { label: '单词数', type: 'wordCE', value: countWordsDistinguishCE(props.editor?.getText()) },
    { label: '段落数', type: 'wordP', value: countParagraphs(props.editor?.getText()) },
  ]
})

const currentWordType = ref('words')
const currentWords = computed(() => {
  return items.value.find(item => item.type === currentWordType.value)?.value
})
</script>

<template>
  <el-dropdown>
    <button
      class="cursor-pointer flex items-center text-gray-lighter-color"
    >
      <div class="text-normal">
        {{ currentWords }} {{ currentWordType !== 'wordP' ? '字' : '段' }}
      </div>
      <div class="ml-[4px] i-ll-triangle text-[6px] -rotate-180" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in items"
          :key="item.type"
          :command="item.type"
        >
          <div
            class="flex items-center justify-between text-black-color w-[140px]"
            :class="{
              'is-menu-selected': currentWordType === item.type,
            }"
            @click="currentWordType = item.type"
          >
            <span>{{ item.label }}</span>
            <span>{{ item.value }}</span>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
.is-menu-selected {
    color: var(--c-text-normal)
}

.text-normal {
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
}
</style>
