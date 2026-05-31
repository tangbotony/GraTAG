<script setup lang="ts">
const props = defineProps<{
  path: [string, string][]
  title: string
}>()

const path = computed(() => {
  if (props.path.length > 0) {
    let path = props.path
    if (path.length > 2) {
      const textLength = path.map(p => p[1]).slice(1, -1).join('')
      if (textLength.length > 10)
        path = [path[0], [path[path.length - 2][0], '...'], path[path.length - 1]]
    }
    path[path.length - 1][1] = props.title
    return path
  }

  return [['-1', 'root']]
})

function go(to: [string, string]) {
  moveFilePath(props.path, to, false)
  navigateTo('/file')
}
</script>

<template>
  <div class="flex items-center justify-between text-gray-lighter-color text-path">
    <div v-for="(p, index) in path" :key="p[0]" class="flex items-center">
      <template v-if="p[1] === 'root'">
        <el-tooltip
          content="返回主页"
        >
          <div class="flex items-center path-segment" @click="go(p)">
            <div class="i-ll-edit-home mr-[4px]" />
            <span>主页</span>
          </div>
        </el-tooltip>
      </template>
      <template v-else-if="index === (path.length - 1)">
        <div class="px-[8px] ">
          /
        </div>
        <div class="i-ll-edit-article" />
        <span class="max-w-[100px] truncate">{{ p[1] }}</span>
      </template>
      <template v-else-if="p[0] === ''">
        <div class="px-[8px] ">
          /
        </div>
        <span>
          ...
        </span>
      </template>
      <template v-else-if="p[1] === '...'">
        <div class="px-[8px] ">
          /
        </div>
        <span class="cursor-pointer" @click="go(p)">
          ...
        </span>
      </template>
      <template v-else>
        <div class="px-[8px] ">
          /
        </div>
        <el-tooltip
          :content="`返回${p[1]}`"
        >
          <div class="flex items-center path-segment" @click="go(p)">
            <div class="i-ll-edit-folder mr-[4px]" />
            <span class="max-w-[100px] truncate">{{ p[1] }}</span>
          </div>
        </el-tooltip>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.path-segment {
    padding: 4px 2px;
    cursor: pointer;
    &:hover {
        border-radius: 4px;
        background: #F0F0F0;
        color: black;
    }
}

.text-path {
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
}
</style>
