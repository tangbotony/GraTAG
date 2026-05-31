import { useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import FontFamily from '@tiptap/extension-font-family'
import Underline from '@tiptap/extension-underline'
import { Color } from '@tiptap/extension-color'
import TextAlign from '@tiptap/extension-text-align'
import TextStyle from '@tiptap/extension-text-style'
import Link from '@tiptap/extension-link'
import Highlight from '@tiptap/extension-highlight'
import type { EditorOptions } from '@tiptap/vue-3'
import {
  CorrectBoundary,
  FontSize,
  FormatPainter,
  History,
  Image,
  type ImageInfo,
  LeadingAdjust,
  ListBehavor,
  Quote,
  Selection,
  Tab,
} from '@xinyu/editor-extensions'

import { IMAGE_LIMIT_SIZE } from '~/consts/editor'

export interface UseTiptapOptions {
  initContent?: string
  onUpdate?: (value: {
    html: string
    text: string
  }) => void
}

async function upload(file: File): Promise<ImageInfo> {
  const { data } = await useImageUpload(file)
  if (data.value?.image_url) {
    return {
      src: data.value?.image_url,
    }
  }
  else {
    return {
      src: '',
    }
  }
}

export function useTiptap(options?: Partial<EditorOptions>) {
  const editor = useEditor({
    autofocus: 'start',
    ...options,
    extensions: [
      StarterKit.configure({
        history: false,
      }),
      Placeholder.configure({
        placeholder: '请输入正文，您的文档将自动保存',
      }),
      FontFamily,
      Underline,
      Color,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      TextStyle,
      Link.configure({
        openOnClick: false,
      }),
      Image.configure({
        upload,
        sizeLimit: IMAGE_LIMIT_SIZE,
      }),
      CorrectBoundary,
      Quote,
      Tab,
      Selection,
      History,
      FontSize,
      ListBehavor,
      FormatPainter,
      LeadingAdjust,
      Highlight.configure({
        multicolor: true,
      }),
    ],
  })
  return {
    editor,
  }
}
