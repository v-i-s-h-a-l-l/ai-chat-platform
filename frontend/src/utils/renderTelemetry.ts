/**
 * Rendering Telemetry
 *
 * Captures markdown-repair events so malformed LLM output is debuggable.
 * In development, logs to the console with a collapsible group. In production,
 * events can be forwarded to an analytics sink via `configureRenderTelemetry`.
 */

import { setTableRepairTelemetry, type TableRepairEvent } from './markdownTableRepair'

const isDev = import.meta.env?.DEV ?? false

let externalSink: ((event: TableRepairEvent) => void) | null = null

export function configureRenderTelemetry(sink: ((event: TableRepairEvent) => void) | null): void {
  externalSink = sink
}

let installed = false

/** Install the telemetry hook once (idempotent). */
export function installRenderTelemetry(): void {
  if (installed) return
  installed = true

  setTableRepairTelemetry((event: TableRepairEvent) => {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.groupCollapsed(
        `%c[markdown-repair]%c ${event.reason}`,
        'color:#a855f7;font-weight:bold',
        'color:inherit',
      )
      // eslint-disable-next-line no-console
      console.log('original:\n' + event.original)
      // eslint-disable-next-line no-console
      console.log('repaired:\n' + event.repaired)
      // eslint-disable-next-line no-console
      console.groupEnd()
    }

    externalSink?.(event)
  })
}
