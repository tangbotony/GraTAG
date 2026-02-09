import { addServerPlugin, createResolver, defineNuxtModule } from '@nuxt/kit'
import legacy from '@vitejs/plugin-legacy'

export default defineNuxtModule({
  meta: {
    name: 'nuxt-vite-legacy',
    configKey: 'legacy',
  },
  async setup(options, nuxt) {
    nuxt.options.vite ??= {}
    nuxt.options.vite.plugins ??= []
    nuxt.options.vite.plugins.unshift(legacy(options))

    // Move polyfills to the top of the manifest, and remove module attribute from legacy chunks.
    // See https://github.com/nuxt/nuxt/issues/15464
    nuxt.hook('build:manifest', (manifest) => {
      /** Copy of manifest. */
      const manifestCopy: typeof manifest = { ...manifest }

      /** Subset of manifest with polyfill chunks. */
      const polyfillManifest = Object.fromEntries(
        Object.entries(manifest).filter(
          ([key]) =>
            key.endsWith('/legacy-polyfills')
            || key.endsWith('/legacy-polyfills-legacy'),
        ),
      )

      // Clear manifest in-place.
      for (const key of Object.keys(manifest))
        delete manifest[key]

      // Fill manifest again from the copy, but put polyfill chunks first.
      Object.assign(manifest, polyfillManifest, manifestCopy)

      // Remove module attribute from legacy chunks.
      for (const key of Object.keys(manifest)) {
        if (key.match(/-legacy(\.|$)/)) {
          manifest[key].module = false
          manifest[key].preload = false
        }
      }
    })

    if (
      options.renderLegacyChunks === undefined
      || options.renderLegacyChunks
    ) {
      // Post-process HTML (mark legacy chunks as nomodule).
      const { resolve } = createResolver(import.meta.url)
      addServerPlugin(resolve('./server-plugin'))
    }
  },
})
