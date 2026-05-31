import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

async function enableMocking() {
  const worker = setupWorker(...handlers)
  return worker.start({
    onUnhandledRequest: 'bypass',
  })
}

export {
  enableMocking,
}
