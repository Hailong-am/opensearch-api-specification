/*
* Copyright OpenSearch Contributors
* SPDX-License-Identifier: Apache-2.0
*
* The OpenSearch Contributors require contributions made to
* this file be licensed under the Apache-2.0 license or a
* compatible open source license.
*/

import { apply_overlay, load_overlay } from 'overlay/apply-overlay'
import { Logger, LogLevel } from '../../../tools/src/Logger'
import tmp from 'tmp'
import fs from 'fs'
import YAML from 'yaml'

const logger = new Logger(LogLevel.warn)

describe('apply_overlay', () => {
  const base_spec: Record<string, any> = {
    openapi: '3.1.0',
    info: { title: 'Test', version: '1.0.0' },
    paths: {
      '/healthy': {
        get: { operationId: 'health.0', description: 'Health check' },
      },
      '/removed-path': {
        get: { operationId: 'removed.0', description: 'To be removed' },
        post: { operationId: 'removed.1', description: 'Also removed' },
      },
      '/partial': {
        get: { operationId: 'partial.get.0', description: 'Stays' },
        delete: { operationId: 'partial.delete.0', description: 'Removed' },
      },
    },
  }

  test('removes entire path', () => {
    const overlay = {
      overlay: '1.0.0',
      info: { title: 'Test', version: '1.0.0' },
      actions: [
        { target: "$.paths['/removed-path']", remove: true as const },
      ],
    }

    const result = apply_overlay(base_spec, overlay, logger)
    expect(result.paths['/removed-path']).toBeUndefined()
    expect(result.paths['/healthy']).toBeDefined()
    expect(result.paths['/partial']).toBeDefined()
  })

  test('removes single method from path', () => {
    const overlay = {
      overlay: '1.0.0',
      info: { title: 'Test', version: '1.0.0' },
      actions: [
        { target: "$.paths['/partial'].delete", remove: true as const },
      ],
    }

    const result = apply_overlay(base_spec, overlay, logger)
    expect(result.paths['/partial'].get).toBeDefined()
    expect(result.paths['/partial'].delete).toBeUndefined()
  })

  test('does not modify original spec', () => {
    const overlay = {
      overlay: '1.0.0',
      info: { title: 'Test', version: '1.0.0' },
      actions: [
        { target: "$.paths['/removed-path']", remove: true as const },
      ],
    }

    apply_overlay(base_spec, overlay, logger)
    expect(base_spec.paths['/removed-path']).toBeDefined()
  })

  test('update action adds new content', () => {
    const overlay = {
      overlay: '1.0.0',
      info: { title: 'Test', version: '1.0.0' },
      actions: [
        {
          target: "$.paths['/healthy'].get",
          update: { 'x-custom-tag': 'added-by-overlay' },
        },
      ],
    }

    const result = apply_overlay(base_spec, overlay, logger)
    expect(result.paths['/healthy'].get['x-custom-tag']).toBe('added-by-overlay')
    expect(result.paths['/healthy'].get.operationId).toBe('health.0')
  })

  test('handles multiple actions', () => {
    const overlay = {
      overlay: '1.0.0',
      info: { title: 'Test', version: '1.0.0' },
      actions: [
        { target: "$.paths['/removed-path']", remove: true as const },
        { target: "$.paths['/partial'].delete", remove: true as const },
      ],
    }

    const result = apply_overlay(base_spec, overlay, logger)
    expect(result.paths['/removed-path']).toBeUndefined()
    expect(result.paths['/partial'].get).toBeDefined()
    expect(result.paths['/partial'].delete).toBeUndefined()
    expect(result.paths['/healthy']).toBeDefined()
  })
})

describe('load_overlay', () => {
  test('loads a YAML overlay file', () => {
    const temp = tmp.fileSync({ postfix: '.yaml' })
    const content = {
      overlay: '1.0.0',
      info: { title: 'Test Overlay', version: '2026.08.31' },
      actions: [
        { target: "$.paths['/test']", remove: true },
      ],
    }
    fs.writeFileSync(temp.name, YAML.stringify(content))

    const loaded = load_overlay(temp.name)
    expect(loaded.overlay).toBe('1.0.0')
    expect(loaded.info.title).toBe('Test Overlay')
    expect(loaded.actions).toHaveLength(1)
    expect(loaded.actions[0].target).toBe("$.paths['/test']")

    temp.removeCallback()
  })
})
