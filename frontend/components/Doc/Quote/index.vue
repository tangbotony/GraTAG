<script setup lang="ts">
function spanLinkClick(hrefdata: string) {
  if (!hrefdata.includes('http') && hrefdata.includes('sourceid')) {
    const sourceidstr = getHrefParam('sourceid', hrefdata)
    const fileext = getHrefParam('ext', hrefdata)
    window.open(`/filePreview?pdfid=${sourceidstr}&fileext=${fileext}`, '_blank')
  }
}
function getHrefParam(txt: string, params: string) {
  const paramsArray = params.split('&')
  let str = ''
  paramsArray.forEach((item: string) => {
    const [key, value] = item.split(':')
    if (key === txt)
      str = value
  })
  return str
}
</script>

<template>
  <div v-if="quoteState.quotes.length > 0" class="quote-container">
    <div class="title">
      引证来源
    </div>
    <div v-for="(item, index) in quoteState.quotes" :key="item.key" class="item">
      <div v-if="item.href && item.href.indexOf('http') === -1 && item.href.indexOf('sourceid') > -1" class="item-title">
        {{ index + 1 }}. <span class="link" :hrefdata="item.href" @click="spanLinkClick(item.href ? item.href : '')">{{ item.title }}</span>
      </div>
      <div v-else class="item-title">
        {{ index + 1 }}. <NuxtLink class="link" :href="item.href" target="__blank">
          {{ item.title }}
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

  <style lang="scss" scoped>
  .quote-container {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 12px;
    padding-bottom: 0px;
    background: #F8F8F8;
    border-radius: 8px;
    margin-bottom: 53px;
    margin-top: 60px;
    width: 100%;

    .title {
      font-size: 13px;
      font-weight: 600;
      line-height: normal;
      letter-spacing: 0.015em;
      color: #4044ED;
      margin-bottom: 12px;
    }

    .item {
      margin-bottom: 5px;

      &-title {
        font-size: 12px;
        font-weight: normal;
        line-height: normal;
        letter-spacing: 0.015em;
        color: rgba(0, 0, 0, 0.9);
        margin-bottom: 4px;
      }
    }
  }

  .link {
    cursor: pointer;
    &:hover {
      color: #4044ED;
      text-decoration: none;
    }
  }
  </style>
