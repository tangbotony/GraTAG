<script setup lang="ts">
import { QaMode } from '~/store/qa'

const type = defineModel()
function handleClick(value: string) {
  type.value = value
}
</script>

<template>
  <div class="container">
    <button
      class="btn" :class="{
        'is-active': type === QaMode.WEB,
      }"
      @click="handleClick(QaMode.WEB)"
    >
      <span class="text">全网搜索</span>
    </button>
    <button
      class="btn" :class="{
        'is-active': type === QaMode.DOC,
      }"
      @click="handleClick(QaMode.DOC)"
    >
      <span class="text">文件搜索</span>
    </button>
  </div>
</template>

<style lang="scss" scoped>
.container {
    width: 204px;
    height: 40px;
    border-radius: 4px;
    display: flex;
    padding: 2px;
    gap: 4px;
    background-color: #F2F3FF;
}

.btn {
    width: 98px;
    height: 36px;
    border-radius: 4px;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: white;
    padding: 0px;
    cursor: pointer;

    .text {
        font-size: 16px;
        font-weight: normal;
        line-height: 24px;
        color: rgba(0, 0, 0, 0.6);
    }

    &.is-active {
        background: #4044ED;
    }

    &.is-active .text {
        color: white;
    }
}
</style>
