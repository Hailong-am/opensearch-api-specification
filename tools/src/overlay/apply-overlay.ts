/*
* Copyright OpenSearch Contributors
* SPDX-License-Identifier: Apache-2.0
*
* The OpenSearch Contributors require contributions made to
* this file be licensed under the Apache-2.0 license or a
* compatible open source license.
*/

/**
 * Applies an OpenAPI Overlay file to the merged spec using the
 * openapi-overlays-js library (official OAI Overlay implementation).
 *
 * Supports the full Overlay 1.0.0 spec: remove and update actions
 * with RFC 9535 JSONPath targeting.
 *
 * Usage:
 *   ts-node tools/src/overlay/apply-overlay.ts -s <spec> -o <overlay> --output <out>
 */

import { Command, Option } from '@commander-js/extra-typings'
import { resolve } from 'path'
import { Logger, LogLevel } from '../Logger'
import { write_yaml } from '../helpers'
import { applyOverlay } from 'openapi-overlays-js/src/overlay'
import _ from 'lodash'
import fs from 'fs'
import YAML from 'yaml'

export interface OverlayAction {
  target: string
  remove?: boolean
  update?: unknown
  description?: string
}

export interface OverlayDocument {
  overlay: string
  info: { title: string; version: string }
  actions: OverlayAction[]
}

export function load_overlay(overlay_path: string): OverlayDocument {
  const content = fs.readFileSync(overlay_path, 'utf8')
  return YAML.parse(content) as OverlayDocument
}

export function apply_overlay(spec: Record<string, any>, overlay: OverlayDocument, logger: Logger): Record<string, any> {
  const input = _.cloneDeep(spec)
  logger.info(`Applying overlay: ${overlay.info.title} (${overlay.actions.length} actions) ...`)
  const result = applyOverlay(input, overlay) as Record<string, any>
  logger.log(`Applied ${overlay.actions.length} overlay actions.`)
  return result
}

// CLI entry point
if (require.main === module) {
  const command = new Command()
    .description('Apply an OpenAPI Overlay to a merged spec.')
    .addOption(new Option('-s, --spec <path>', 'path to the merged OpenAPI spec').makeOptionMandatory())
    .addOption(new Option('-o, --overlay <path>', 'path to the overlay file').makeOptionMandatory())
    .addOption(new Option('--output <path>', 'output file path').makeOptionMandatory())
    .addOption(new Option('--verbose', 'show details').default(false))
    .allowExcessArguments(false)
    .parse()

  const opts = command.opts()
  const logger = new Logger(opts.verbose ? LogLevel.info : LogLevel.warn)

  logger.log(`Loading spec from ${opts.spec} ...`)
  const spec = YAML.parse(fs.readFileSync(resolve(opts.spec), 'utf8')) as Record<string, any>

  logger.log(`Loading overlay from ${opts.overlay} ...`)
  const overlay = load_overlay(resolve(opts.overlay))

  const result = apply_overlay(spec, overlay, logger)

  logger.log(`Writing ${opts.output} ...`)
  write_yaml(resolve(opts.output), result)
  logger.log('Done.')
}
