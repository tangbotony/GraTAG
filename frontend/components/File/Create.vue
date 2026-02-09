<script setup lang="ts">
const props = defineProps<{
  parentId: string
}>()

const emit = defineEmits<{
  (e: 'created', type: string): void
}>()

function handleCreate(val: string) {
  switch (val) {
    case 'document':
      createDocument()
      break
    case 'folder':
      createFold()
      break
  }
}

async function createDocument() {
  const { error, data } = await useFileCreate({
    name: '',
    parent_id: props.parentId,
    text: '',
    plain_text: '',
  })
  if (!error.value && data.value?.doc_id)
    navigateTo(`/document/${data.value.doc_id}`)
}

const dialogVisible = ref(false)
const foldTitle = ref('')
function createFold() {
  dialogVisible.value = true
}

const isLoadingFold = ref(false)
async function addFold() {
  try {
    isLoadingFold.value = true
    await useFolderCreate({
      name: foldTitle.value,
      parent_id: props.parentId || '-1',
    })

    emit('created', 'folder')
  }
  catch (error) {

  }
  finally {
    isLoadingFold.value = false
    dialogVisible.value = false
    foldTitle.value = ''
  }
}
</script>

<template>
  <div class="w-full flex items-center">
    <div class="card" :style="{ background: 'linear-gradient(180deg, #D9DAFF 0%, #FCFCFF 100%)' }" @click="handleCreate('document')">
      <div class="i-ll-file text-normal-color w-[36px] h-[36px] mb-[6px]" />
      <div class="title">
        开始写作
      </div>
    </div>
    <div class="card ml-[20px]" :style="{ background: 'linear-gradient(180deg, #CEE0FF 0%, #F9FCFF 100%)' }" @click="handleCreate('folder')">
      <img src="~/assets/images/doc/folder.svg" class="w-[36px] h-[36px] mb-[6px]">
      <div class="title">
        新建文件夹
      </div>
    </div>
    <!-- <el-dropdown @command="handleCreate">
      <el-button>
        <div class="flex items-center">
          <span>新建</span>
          <div class="i-ll-arrow-bottom ml-[4px] text-[16px]" />
        </div>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="folder">
            新建文件夹
          </el-dropdown-item>
          <el-dropdown-item command="document">
            新建稿件
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown> -->
    <el-dialog
      v-model="dialogVisible"
      title="新建文件夹"
      :width="425"
      append-to-body
    >
      <div class="w-full h-[40px]">
        <div class="w-full">
          <el-input
            v-model="foldTitle"
            maxlength="20"
            show-word-limit
            type="text"
            placeholder="请输入文件夹名称"
          />
        </div>
      </div>
      <template #footer>
        <div class="flex items-center justify-end">
          <el-button :loading="isLoadingFold" :disabled="foldTitle.length === 0" @click="addFold">
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.card {
  width: 200px;
  height: 107px;
  border-radius: 8px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  cursor: pointer;
  box-sizing: border-box;
  border: 1px solid #EEEEEE;
}

.title {
  font-size: 18px;
  font-weight: 500;
  line-height: 25px;
  color: rgba(0, 0, 0, 0.9);
}
</style>
