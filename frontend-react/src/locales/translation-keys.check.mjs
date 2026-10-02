import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import i18next from 'i18next';
import ts from 'typescript';

const localeDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.dirname(localeDir);
const locales = Object.fromEntries(['en', 'zh-CN'].map(language => [
  language, JSON.parse(fs.readFileSync(path.join(localeDir, `${language}.json`), 'utf8')),
]));

function staticReferences(dir, refs = new Map()) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!/^(?:__tests__|tests|__mocks__)$/.test(entry.name)) staticReferences(file, refs);
      continue;
    }
    if (!/\.[cm]?[jt]sx?$/.test(file) || /\.(test|spec)\./.test(file)) continue;
    const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
    function visit(node) {
      if (ts.isCallExpression(node)) {
        const expression = node.expression;
        const isTranslation = ts.isIdentifier(expression)
          ? expression.text === 't'
          : ts.isPropertyAccessExpression(expression) && expression.name.text === 't';
        const key = node.arguments[0];
        if (isTranslation && key && (ts.isStringLiteral(key) || ts.isNoSubstitutionTemplateLiteral(key))) {
          refs.set(key.text, path.relative(srcDir, file));
        }
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
  return refs;
}

test('production static translation keys resolve in both languages', async () => {
  const refs = staticReferences(srcDir);
  assert.ok(refs.size > 0);
  const instances = {};
  for (const [language, translation] of Object.entries(locales)) {
    const instance = i18next.createInstance();
    await instance.init({ lng: language, fallbackLng: false, resources: { [language]: { translation } } });
    instances[language] = instance;
  }
  const failures = [];
  for (const [key, file] of refs) {
    const values = Object.entries(instances).map(([language, instance]) => {
      const value = instance.getResource(language, 'translation', key);
      if (typeof value !== 'string' || !value.trim()) failures.push(`${language}: ${key} (${file})`);
      return value;
    });
    if (values.every(value => typeof value === 'string')) {
      const placeholders = value => [...value.matchAll(/{{\s*([^}]+?)\s*}}/g)].map(match => match[1]).sort();
      assert.deepEqual(placeholders(values[0]), placeholders(values[1]), `Interpolation mismatch: ${key}`);
    }
  }
  assert.deepEqual(failures, [], failures.join('\n'));
   console.log(`Checked ${refs.size} production static keys in en and zh-CN`);
});
