import { defineNitroPlugin } from 'nitropack/dist/runtime/plugin'

// Make vite-legacy build operational.
// See https://github.com/nuxt/nuxt/issues/15464
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('render:response', (response) => {
    // Mark legacy chunks as nomodule (prevents modern browsers from loading them).
    // At the same time, unmark them as defer (otherwise System.register() in the legacy entry doesn't actually execute the code).
    response.body = response.body?.replace(
      /(<script src="[^"]+-legacy\.[^>]+") defer/g,
      '$1 nomodule',
    )

    // Remove legacy chunks preload (fixes warnings in modern browsers).
    // Note that different versions of Nuxt emit slightly different HTML.
    response.body = response.body?.replace(
      /<link rel="preload"[^>]+ href="[^"]+-legacy\.\w+\.js".*?>/g,
      '',
    )

    // The other option would be NOT to remove defer from legacy chunks,
    // but start them from a nomodule HTML script:
    //
    // response.body += `<script nomodule>document.querySelector("script[src*='/entry-legacy.']").onload=function(){System.import(this.src)}</script>`
    //
    // This is similar to what vite-legacy-plugin does in vanilla vite.
  })
})
