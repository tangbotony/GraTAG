<script setup lang="ts">
const props = defineProps<{
  argumentPlaceholder?: string
  evidencePlaceholder?: string
  value: { argument: string; evidence: string; key: number }[]
}>()

let count = 1

const { value, argumentPlaceholder = '', evidencePlaceholder = '' } = toRefs(props)

function addArgument() {
  if (value.value.length === 5) {
    ElMessage({
      message: '最多设置5个参考论点哦～',
      type: 'warning',
    })
    return
  }
  count += 1
  value.value.push({
    argument: '',
    evidence: '',
    key: count,
  })
}

function deleteArgument(key: number) {
  const index = value.value.findIndex(item => item.key === key)
  value.value.splice(index, 1)
}
</script>

<template>
  <div>
    <div
      v-for="(item, index) in value"
      :id="index === 0 ? 'generate-first-argument' : ''"
      :key="item.key"
      class="item"
    >
      <DocGenerateArgumentListItem
        :index="index"
        :value="item"
        :argument-placeholder="argumentPlaceholder"
        :evidence-placeholder="evidencePlaceholder"
        @delete="deleteArgument"
      />
    </div>
    <div class="flex items-center justify-center mt-[3px] mb-[48px]">
      <div id="generate-add-argument"  class="flex items-center cursor-pointer inline-block" @click="addArgument">
        <div class="i-ll-plus-sign text-[#4044ED] text-[10px] mr-[7px]" />
        <span class="text2">增加更多参考论点</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.text2 {
    color: #4044ED;
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 21px; /* 150% */
}

.item:not(:last-child) {
  margin-bottom: 16px;
}
</style>
