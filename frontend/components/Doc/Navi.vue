<script setup lang="ts">
import { WRITE_KIND, WRITE_STYLE_LIST } from '~/consts/editor'

const props = defineProps<{
  currentArticle: Article
  currentAI: string
  isInit: boolean
}>()

const $emit = defineEmits<{
  (e: 'currentAiChange', value: string, style?: string): void
}>()

const route = useRoute()

const { currentArticle } = toRefs(props)

function handleCurrentAi(kind: string, style?: string) {
  $emit('currentAiChange', kind, style)
}
</script>

<template>
  <div class="flex items-center justify-between px-[24px] pt-[12px] pb-[8px] border-solid border-[rgba(0,0,0,0.05)] border-b-1 h-[42px]">
    <div>
      <DocPath :path="currentArticle.path" :title="currentArticle.title" />
    </div>
    <div class="flex items-center">
      <DocAutoSave v-if="isInit" :id="route.params.id as string" :content="currentArticle.content" :title="currentArticle.title" :plain-text="currentArticle.plainText" />
      <DocDelete :id="route.params.id as string" />
      <span class="pl-[12px] pr-[8px] text-[14px] leading-[14px]">|</span>
      <div class="btn-ai" :class="{ 'is-active': currentAI === WRITE_KIND.Generate }" data-stats data-type="text-generate" @click="handleCurrentAi(WRITE_KIND.Generate)">
        <div class="i-custom:ai-ring w-[20px] h-[20px]" />
        <span class="text ">AI全文写作</span>
      </div>
      <el-dropdown @command="(val) => handleCurrentAi(WRITE_KIND.Polish, val)">
        <div class="btn-ai" :class="{ 'is-active': currentAI === WRITE_KIND.Polish }">
          <div class="i-ll-edit-polish-writing text-[14px]" />
          <span class="text ">润色</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in WRITE_STYLE_LIST"
              :key="item.type"
              :command="item.type"
            >
              <div class="flex items-center justify-center w-full" data-stats :data-type="`text-polish-${item.type}`">
                <span class="dropdown-item-text">
                  {{ item.title }}
                </span>
              </div>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown @command="(val) => handleCurrentAi(val)">
        <div class="btn-ai" :class="{ 'is-active': currentAI === WRITE_KIND.Continue || currentAI === WRITE_KIND.ContinuePro }">
          <div class="i-ll-edit-continue-writing text-[14px]" />
          <span class="text ">续写</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <div class="flex items-center justify-center w-full pt-[8px]">
              <el-switch v-model="currentArticle.isQuote" :width="48" size="small" inline-prompt active-text="引证" inactive-text="引证" />
            </div>
            <el-dropdown-item :command="WRITE_KIND.Continue">
              <div class="flex items-center justify-center w-full" data-stats data-type="text-continue">
                <span class="dropdown-item-text">
                  通用模式
                </span>
              </div>
            </el-dropdown-item>
            <el-dropdown-item :command="WRITE_KIND.ContinuePro">
              <div class="flex items-center justify-center w-full" data-stats data-type="text-continue_profession">
                <span class="dropdown-item-text">
                  专业模式
                </span>
              </div>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <div class="btn-ai" :class="{ 'is-active': currentAI === WRITE_KIND.Expand }" data-stats data-type="text-expand" @click="handleCurrentAi(WRITE_KIND.Expand)">
        <div class="i-ll-edit-continue-writing text-[14px]" />
        <span class="text ">扩写</span>
      </div>
      <el-dropdown @command="(val) => handleCurrentAi(WRITE_KIND.Title, val)">
        <div class="btn-ai" :class="{ 'is-active': currentAI === WRITE_KIND.Title }">
          <div class="i-ll-edit-h text-[14px]" />
          <span class="text ">标题生成</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in WRITE_STYLE_LIST"
              :key="item.type"
              :command="item.type"
            >
              <div class="flex items-center justify-center w-full" data-stats :data-type="`text-title-${item.type}`">
                <span class="dropdown-item-text">
                  {{ item.title }}
                </span>
              </div>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.btn-ai {
  cursor: pointer;
  display: flex;
  height: 22px;
  padding: 0px 12px;
  align-items: center;
  border-radius: 8px;
  background: white;
  color: #4044ED;
  outline: none;

  &:hover {
    background: #E5E6FF;

    .text {
      color: var(--N1, #19222E);
    }
  }

  &.is-active {
    background: #E5E6FF;
  }

  .text {
    font-size: 12px;
    font-style: normal;
    font-weight: 600;
    line-height: normal;
    margin-left: 4px;
  }
}

.dropdown-item-text {
  font-size: 14px;
  font-weight: normal;
  line-height: 22px;
  letter-spacing: 0em;
  color: rgba(0, 0, 0, 0.88);
}
</style>
