# Round 11：成熟 Agent 前端的验收做法调研与本项目结项验收清单

- 日期：2026-09-26
- 角色：研究与文档执行者，只读 `/tmp/opencode/ref-repos`
- 目标：找出顶级开源 Agent 前端在「验收」维度的真实做法，给出可落地的本项目验收清单
- 写入范围：本文件 + `REFACTOR_50_TASKS_2026-09-26.md` 追加第 7 节
- 未修改 `frontend-react/src` 下任何产品源码；未 commit、未 push
- 证据规则：只采用具体配置文件与测试源文件，附绝对路径与行号。README、包描述、许可证正文不作为验收做法证据。

调研覆盖 6 个仓库：`danny-avila_LibreChat`、`cline_cline`、`CopilotKit_CopilotKit`、`All-Hands-AI_OpenHands`、`langgenius_dify`、`lobehub_lobe-chat`。LibreChat 提供了四个维度中三个的完整实现，本项目对照重点放在它身上。

---

## 1. 调研结论速览

| 维度 | 是否有可引用实现 | 代表证据 |
| --- | --- | --- |
| 视觉回归基线管理 | 有，且成熟 | LibreChat `e2e/specs/mock/message-visual.spec.ts`；CopilotKit `tests/visual/dashboard.spec.ts` |
| 性能预算 | 有，且成熟 | LibreChat `e2e/benchmarks/agent-startup.latency.spec.ts`、`e2e/benchmarks-reasoning/reasoning-stream.perf.spec.ts` |
| a11y 检查 | 有，且成熟 | LibreChat `e2e/specs/a11y.spec.ts` + 独立 `e2e/playwright.config.a11y.ts` |
| E2E 稳定性策略 | 有，跨仓库一致 | Cline `apps/vscode/playwright.config.ts`；LibreChat 各专用 config 的 `retries`/`fullyParallel` 分档 |

关键观察：LibreChat 把 a11y、性能基准、视觉回归各自拆成**独立的 Playwright config**，而不是塞进一个主配置。`testDir`、`retries`、`timeout`、`webServer` 全部不同档。这是本项目最值得直接照搬的一条结构性做法。

---

## 2. 视觉回归基线管理

### 2.1 LibreChat：双主题 × 双视口矩阵 + 显式比对参数 + 平台固定

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/specs/mock/message-visual.spec.ts`

```
22: const THEMES: VisualTheme[] = ['light', 'dark'];
23: const VIEWPORTS: VisualViewport[] = [
24:   { name: 'desktop', width: 1280, height: 900, snapshotSuffix: '' },
25:   { name: 'mobile', width: 390, height: 844, snapshotSuffix: '-mobile' },
26: ];
```

```
29: const VISUAL_OPTIONS = {
30:   animations: 'disabled' as const,
31:   caret: 'hide' as const,
32:   maxDiffPixels: 20,
33:   scale: 'css' as const,
34: };
```

```
36: /**
37:  * Pixel baselines only compare cleanly against the machine that produced them, and this
38:  * repository tracks none. Until baselines are generated on the runner image itself, the
39:  * flows below still run and assert their structure, while the screenshot comparison is
40:  * opt-in through `E2E_VISUAL_SNAPSHOTS=1 npx playwright test --config=e2e/playwright.config.mock.ts --update-snapshots`.
41:  */
42: const VISUAL_BASELINES_ENABLED = process.env.E2E_VISUAL_SNAPSHOTS === '1';
```

```
55: async function openChat(page: Page, theme: VisualTheme, viewport: VisualViewport) {
56:   await page.addInitScript((selectedTheme: VisualTheme) => {
57:     localStorage.setItem('color-theme', selectedTheme);
58:     localStorage.removeItem('theme-definition');
59:     localStorage.removeItem('theme-colors');
60:     localStorage.removeItem('theme-name');
61:     localStorage.removeItem('theme-source');
62:   }, theme);
63:   await page.setViewportSize({ width: viewport.width, height: viewport.height });
64:   await page.goto(NEW_CHAT_PATH, { timeout: 10000 });
65:   await expect(page.locator('html')).toHaveClass(new RegExp(`(^|\\s)${theme}(\\s|$)`));
66: }
```

```
71:   await locator.page().evaluate(async () => {
72:     await document.fonts.ready;
73:   });
```

```
91: test.skip(process.platform !== 'linux', 'Message visual baselines target the Linux CI runner');
```

可提取的五条做法：

1. **主题注入 + 主题落地断言**（56–65 行）。注入后断言 `<html>` 实际带上主题类（65 行），防止主题未生效时拍出一组「假双主题」基线。`localStorage.removeItem` 连续 5 次（58–61 行）用于清除可能覆盖主题的其他来源。
2. **快照前等字体就绪**（71–73 行）。`document.fonts.ready` 消除字体回退导致的字形差异。
3. **比对参数集中一处**（29–34 行）。四项各有明确作用，不是散落的魔法数字。
4. **平台固定**（91 行）。像素基线只在指定平台比对，理由写在 skip 消息里。
5. **基线未就绪时的降级路径**（36–42 行）。结构断言照常执行，像素比对由 `E2E_VISUAL_SNAPSHOTS=1` 显式开启。注释直接写明根因（37 行：像素基线只对产出它的机器干净比较）。

第 5 条对本项目尤其重要：Climber 的 `artifacts/ui-acceptance/*.png` 目前是无判读价值的空图。照搬这个降级结构，可以让结构断言先进门，像素比对在 Linux 镜像上一次性建立基线后开启。

### 2.2 CopilotKit：状态矩阵 × 路由拦截使基线与后端解耦

`/tmp/opencode/ref-repos/CopilotKit_CopilotKit/showcase/shell-dashboard/tests/visual/dashboard.spec.ts`

```
 9: type StateLabel = "all-green" | "mixed" | "all-unknown";
...
65: async function seedPb(
66:   page: import("@playwright/test").Page,
67:   label: StateLabel,
68: ): Promise<void> {
69:   await page.route(/\/api\/collections\/status\/records/, async (route) => {
70:     await route.fulfill({
71:       status: 200,
72:       contentType: "application/json",
73:       body: JSON.stringify({ ... }),
74:     });
75:   });
76:   await page.route(/\/api\/realtime/, async (route) => {
77:     await route.abort("blockedbyclient");
78:   });
79: }
```

```
87: for (const label of ["all-green", "mixed", "all-unknown"] as const) {
88:   test(`matrix-${label}`, async ({ page }) => {
89:     await seedPb(page, label);
90:     await page.goto("/");
91:     await page
92:       .locator('[data-testid="live-indicator"][data-status="error"]')
93:       .first()
94:       .waitFor({ state: "attached", timeout: 10000 });
95:     await expect(page).toHaveScreenshot(`matrix-${label}.png`, {
96:       fullPage: true,
97:       maxDiffPixelRatio: 0.02,
98:     });
99:   });
100: }
```

两条做法：

1. **API 用 `page.route` 固定**（69–75 行），实时通道用 `page.route` 主动失败（76–78 行）。断线态因此也是可复现的确定态，而非「碰巧断网」。
2. **先等一个确定的渲染标志再截图**（91–94 行）。等 `[data-status="error"]` 出现说明异步态已落位，避免拍到中间态。
3. `maxDiffPixelRatio: 0.02`（97 行）是比例容差，与 LibreChat 的 `maxDiffPixels: 20` 绝对容差形成两种口径。整页截图用比例更合理。

### 2.3 缺口：未发现基线差异的人工确认环节

两个仓库都只有自动比对，未找到「差异经人工确认后签收」的任何机制。本项目任务 46 明确要求这一点。做法：Playwright 失败时输出 diff 图到 `outputDir`，由人工在 `test-results/` 签收；`maxDiffPixels` 的调整需在账本记录理由。

---

## 3. 性能预算

### 3.1 LibreChat：p50/p95 采样 + 机器指纹 + JSON 报告落盘

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/benchmarks/agent-startup.latency.spec.ts`

```
42: const WARMUP_COUNT = parseCount('E2E_LATENCY_WARMUPS', 5);
43: const SAMPLE_COUNT = parseCount('E2E_LATENCY_SAMPLES', 30, 1);
```

```
87: function percentile(sortedValues: number[], percentileValue: number) {
88:   if (sortedValues.length === 1) {
89:     return sortedValues[0];
90:   }
91:   const position = (sortedValues.length - 1) * percentileValue;
92:   const lowerIndex = Math.floor(position);
93:   const upperIndex = Math.ceil(position);
94:   const weight = position - lowerIndex;
95:   return sortedValues[lowerIndex] * (1 - weight) + sortedValues[upperIndex] * weight;
96: }
97:
98: function summarize(values: number[]): Summary {
99:   const sortedValues = [...values].sort((left, right) => left - right);
100:   return {
101:     p50: round(percentile(sortedValues, 0.5)),
102:     p95: round(percentile(sortedValues, 0.95)),
103:     mean: round(values.reduce((total, value) => total + value, 0) / values.length),
104:     min: round(sortedValues[0]),
105:     max: round(sortedValues.at(-1)!),
106:   };
107: }
```

```
298: async function saveReport(report: object, testInfo: TestInfo) {
299:   const serialized = `${JSON.stringify(report, null, 2)}\n`;
300:   await testInfo.attach('agent-startup-latency.json', {
301:     body: Buffer.from(serialized),
302:     contentType: 'application/json',
303:   });
304:
305:   const outputPath = process.env.E2E_LATENCY_OUTPUT;
306:   if (outputPath) {
307:     await mkdir(dirname(outputPath), { recursive: true });
308:     await writeFile(outputPath, serialized, 'utf8');
309:   }
310: }
```

```
338:     const report = {
339:       label: process.env.E2E_LATENCY_LABEL ?? 'unlabeled',
340:       gitSha: process.env.E2E_LATENCY_GIT_SHA ?? 'unknown',
341:       streamMode: process.env.E2E_LATENCY_STREAM_MODE ?? 'in-memory',
342:       profile: BENCHMARK_PROFILE,
343:       turn: BENCHMARK_TURN,
344:       simulatedLatency: {
345:         mongoQueryMs: SIMULATED_MONGO_DELAY_MS,
346:       },
347:       cold,
348:       warmups: WARMUP_COUNT,
349:       samples: SAMPLE_COUNT,
350:       host: {
351:         logicalCpus: availableParallelism(),
352:         loadAverageBefore: hostLoadBefore,
353:         loadAverageAfter: loadavg(),
354:         cpuUtilizationPct: calculateCpuUtilization(hostCpuBefore, captureCpuSnapshot()),
355:       },
356:       raw: {
357:         submitToAckMs: samples.map((sample) => sample.submitToAckMs),
358:         submitToFirstContentMs: samples.map((sample) => sample.submitToFirstContentMs),
359:         ackToFirstContentMs: samples.map((sample) => sample.ackToFirstContentMs),
360:       },
361:       summary: summarizeSamples(samples),
362:     };
```

```
328:     const cold = await measureSample(page, agentName, token, 0);
329:     for (let index = 0; index < WARMUP_COUNT; index++) {
330:       await measureSample(page, agentName, token, index + 1);
331:     }
```

六条做法：

1. **冷样本单独记录**（328 行）。首样本受 JIT 与连接建立影响，混入会污染分位数。
2. **预热轮次可配且默认 5**（42、329–331 行）。预热样本不计入统计。
3. **p95 用线性插值**（91–96 行），不是取第 95 个元素。
4. **五个统计量齐备**（100–106 行）。只有 p95 会被单次异常值影响，mean/min/max 用于交叉判断。
5. **机器指纹进报告**（350–355 行）。`logicalCpus`、前后 `loadAverage`、`cpuUtilizationPct` 三个维度。缺 host 的性能数字无法跨机比较。
6. **`raw` 原始样本进报告**（356–360 行）。汇总值可被质疑，原始样本可复核。

### 3.2 LibreChat：渲染次数上界 + 长任务阈值（针对流式渲染）

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/benchmarks-reasoning/reasoning-stream.perf.spec.ts`

```
192:     expect(thinkingContentRenders).toBeLessThan(framesUpperBound);
195:     expect(thinkingContentRenders).toBeLessThan(thinkChunks / 4);
...
205:     expect(markdownBlockRenders).toBeLessThan(framesUpperBound);
206:     expect(markdownBlockRenders).toBeLessThan(textChunks / 4);
...
215:     expect(worstLongTask).toBeLessThan(250);
216:     expect(longTaskTotal).toBeLessThan(streamMs * 0.1);
217:     expect(streamTotals.time).toBeLessThan(streamMs * 0.25);
```

```
234:       expect(renders, `${component} re-rendered while typing`).toBeLessThanOrEqual(2);
```

```
248:     expect(typingWorstLongTask).toBeLessThan(150);
251:     expect(typingLongTaskTotal).toBeLessThan(300);
252:     expect(typingTotals.time).toBeLessThan(typing.elapsedMs * 0.25);
```

分片速率固定化的说明：

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/playwright.config.reasoning-perf.ts`

```
20: process.env.MOCK_LLM_REPLY = buildReasoningPayload();
21: /** Pinned, not defaulted: the render-count thresholds are calibrated against
22:  * this delivery rate, and a slower stream would loosen the frame-derived
23:  * bounds. */
24: process.env.MOCK_LLM_CHUNK_DELAY_MS = '1';
```

做法：

1. **渲染次数 / 分片数 < 1/4**（195、206 行）。这是最关键的一条：它把「每个分片触发一次 setState」这类模式直接量化成失败，无需人工观察卡顿。
2. **长任务三重阈值**（215–217 行）。单次最差、总时长占比、脚本总执行占比，三个角度同时设限。
3. **输入期渲染上界更严**（234 行 `≤ 2`）。输入时 UI 对延迟最敏感，允许的渲染次数远少于流式期。
4. **阈值与输入速率绑定并注明原因**（21–24 行）。分片变慢会让帧派生上界失效，所以速率必须钉死，且注释说明这是钉死而非取默认值。
5. 断言消息带组件名（234 行 `` `${component} re-rendered while typing` ``），失败时直接指出是哪个组件在重渲染。

### 3.3 基准套件的配置隔离

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/playwright.config.benchmark.ts`

```
20:   testDir: 'benchmarks',
21:   outputDir: 'benchmarks/.test-results',
22:   timeout: 20 * 60 * 1000,
23:   retries: 0,
24:   reporter: [['line']],
```

`retries: 0`（23 行）与 `timeout` 放大 40 倍（22 行，对比主配置的常规值）成对出现。原因与 3.2 的速率钉死同源：重试会掩盖真实回归，放宽超时是为了容纳冷启动。`outputDir` 独立（21 行），避免基准产物被主配置的清理逻辑删掉。

### 3.4 可注入的测量延迟

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/benchmarks/mongoose-latency-hook.cjs` + `playwright.config.benchmark.ts:8-16`：通过 `NODE_OPTIONS=--require=` 注入 mongoose 延迟钩子，用于在已知延迟下测量启动时序。这是「把不可控因素变成可控参数」的做法，本项目若需测量后端参与的开销可采用同思路。

### 3.5 缺口：未找到 bundle 体积预算

在全部 6 个仓库中未找到 bundlesize、bundlewatch、`size-limit` 或任何产物体积门槛的配置文件。本项目 46/48 的性能预算目前只能覆盖运行时指标，产物体积需自建门槛。

---

## 4. a11y 检查

### 4.1 LibreChat：整页扫描 + 区域扫描 + 交互态扫描

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/specs/a11y.spec.ts`

```
 3: import AxeBuilder from '@axe-core/playwright'; // 1
...
 9: /** A fresh e2e user has no conversations, so without seeding the sidebar renders no rows
10:  *  and no scan below reaches the conversation row markup. The pre-delete keeps the suite
11:  *  idempotent: the ids are fixed and conversations are uniquely indexed, so a run that
12:  *  dies before afterAll would otherwise leave the next one to fail on insert. */
13: test.beforeAll(async () => {
14:   await deleteConversations(SEEDED_IDS);
15:   await seedConversations(...);
16: });
...
25: test.afterAll(async () => {
26:   await deleteConversations(SEEDED_IDS);
27: });
```

```
29: /** Scanning straight after navigation catches a pre-render DOM with no main landmark and
30:  *  no composer, so waiting for the composer keeps every scan on the loaded app. Navigate
31:  *  relative to the config `baseURL` rather than a hardcoded port. */
32: async function loadApp(page: Page) {
33:   await page.goto('/', { timeout: 30000 });
34:   await page.getByTestId('text-input').waitFor({ state: 'visible', timeout: 30000 });
35: }
```

```
42:   const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
43:
44:   expect(accessibilityScanResults.violations).toEqual([]);
```

```
65:   const navAccessibilityScanResults = await new AxeBuilder({ page }).include('nav').analyze();
...
73:   const formAccessibilityScanResults = await new AxeBuilder({ page }).include('form').analyze();
```

```
78: /** Hovering reveals the row's options button, which is what makes the row an interactive
79:  *  control containing another interactive control. Wait on that button by id rather than
80:  *  on any button in the row: the row's title control is always present, so a role match
81:  *  would be satisfied with the options control still unmounted. */
82: test('Conversation list rows should be accessible with their controls revealed', async ({
83:   page,
84: }) => {
85:   await loadApp(page);
86:
87:   const row = page.getByTestId('convo-item').first();
88:   await expect(row).toBeVisible({ timeout: 15000 });
89:   await row.hover();
90:   await expect(row.locator('[id^="conversation-menu-"]')).toBeVisible();
91:
92:   const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
```

五条做法：

1. **零违规硬断言**（44、59、67、76、94、105 行）。统一 `expect(violations).toEqual([])`，不设容差、不按严重度过滤。
2. **等待应用真正加载后再扫**（29–34 行）。注释写明直接扫会命中无 main landmark 的预渲染 DOM。
3. **相对 `baseURL` 导航**（31 行），不硬编码端口。
4. **区域扫描**（65、73 行）。`include('nav')` / `include('form')` 定位到具体区域，失败信息更可读。
5. **悬停后才扫**（89–90 行）。hover 才出现的交互控件必须展开后再扫，否则等于没扫。等待条件用控件 id 前缀而非泛化的 role 匹配（80–81 行解释了泛化匹配会被常驻控件满足）。

第 5 条对本项目直接相关：`SessionSidebar` 的删除按钮在行内，`CommandBar` 的次要操作收在 More 弹层（`ROUND10_TASK_B` 记录 `ControlBar.tsx:174-194`），这些 hover/展开才出现的控件需要专门的扫描用例。

### 4.2 LibreChat：a11y 独立配置

`/tmp/opencode/ref-repos/danny-avila_LibreChat/e2e/playwright.config.a11y.ts`

```
10:   retries: 0,
11:   globalSetup: require.resolve('./setup/global-setup.local'),
12:   globalTeardown: require.resolve('./setup/global-teardown.local'),
...
53:   fullyParallel: false, // if you are on Windows, keep this as `false`. On a Mac, `true` could make tests faster (maybe on some Windows too, just try)
...
55:   testMatch: /a11y/,
```

`retries: 0`（10 行）与基准套件一致：a11y 违规是确定性的，重试无意义且会掩盖回归。`fullyParallel: false`（53 行）并附平台注记（Windows 稳定性问题）。`testMatch: /a11y/`（55 行）实现按需运行。

### 4.3 Dify：Cucumber + axe 步骤定义

`/tmp/opencode/ref-repos/langgenius_dify/e2e/features/step-definitions/accessibility/axe.steps.ts` + `e2e/package.json` 中的 `@axe-core` 依赖。Dify 走 BDD，把 a11y 检查写成 Given/When/Then 步骤。适合「同一批场景既要验业务又要验 a11y」的场景，可减少场景重复。

### 4.4 缺口：未找到对比度专项自动检查

`a11y.spec.ts` 使用 `@axe-core/playwright` 的默认规则集。axe-core 本身包含颜色对比度规则，因此对比度是被覆盖的，但两份配置中均未见 `withTags` 过滤或 `disableRules` 调整，说明采用全规则零豁免策略。本项目任务 46 的 4.5:1 / 3:1 要求需要区分字号档位（≥18.66px 或 ≥14px bold 走 3:1），axe 的默认判定已按此执行，可直接采信 axe 结果而不必自建对比度计算；但本项目令牌制（`src/index.css` 的 CSS 变量）需要 axe 解析出实际生效色，故仍建议在视觉套件中保留一条独立的令牌对测量作为交叉证据。

---

## 5. E2E 稳定性策略

### 5.1 Cline：主配置的稳定性基线

`/tmp/opencode/ref-repos/cline_cline/apps/vscode/playwright.config.ts`

```
 6: export default defineConfig({
 7: 	workers: 1,
 8: 	retries: 1,
 9: 	forbidOnly: isCI,
10: 	testDir: "src/test/e2e",
11: 	testMatch: /.*\.test\.ts/,
12: 	timeout: isCI || isWindow ? 60000 : 20000,
13: 	expect: {
14: 		timeout: isCI || isWindow ? 5000 : 2000,
15: 	},
16: 	fullyParallel: true,
17: 	reporter: isCI ? [["github"], ["list"]] : [["list"]],
18: 	use: {
19: 		video: "retain-on-failure",
20: 	},
21: 	projects: [
22: 		{
23: 			name: "setup test environment",
24: 			testMatch: /global\.setup\.ts/,
25: 		},
26: 		{
27: 			name: "e2e tests",
28: 			dependencies: ["setup test environment"],
29: 		},
30: 	],
31: })
```

六条做法：

1. **`workers: 1`**（7 行）配 **`fullyParallel: true`**（16 行）。这不矛盾：单进程内用例并行，跨文件不并行。对需要共享后端状态的套件是常见折中。
2. **CI 与本地分档超时**（12、14 行）。CI 慢，本地要快反馈。
3. **`forbidOnly: isCI`**（9 行）。本地允许 `test.only` 调试，CI 禁止。
4. **失败留证**（19 行 `retain-on-failure`）。
5. **环境准备作为独立 project + 依赖**（21–29 行）。`dependencies` 保证 setup project 先跑完，避免用例内自行准备环境导致的顺序耦合。
6. **多 reporter**（17 行）。CI 用 github reporter 注解 PR。

### 5.2 LibreChat：按套件性质分档

对照三份 config 的 `retries` 与并行设置：

| 套件 | retries | fullyParallel | 依据 |
| --- | --- | --- | --- |
| a11y | 0 | false | `playwright.config.a11y.ts:10,53` — 违规是确定性的 |
| benchmark | 0 | — | `playwright.config.benchmark.ts:23` — 重试污染基线 |
| 主套件 | 依赖默认 | — | `playwright.config.ts:12` 条件设置 |

**这是本项目最值得照搬的一条**：`retries` 不是全局一个值，而是按「结果是否确定性」分档。确定性检查（a11y、视觉、基准）`retries: 0`，随机性检查（业务流）才给重试。

### 5.3 LibreChat：幂等夹具

`a11y.spec.ts:9-27`（见 §4.1）的模式：固定 ID + `beforeAll` 先删后插 + `afterAll` 清理。注释（11–12 行）解释了两点：为什么必须先删（唯一索引，重复插入会失败），以及为什么 `afterAll` 不够（`afterAll` 前崩溃会留下脏数据给下一次）。这是「用例必须可重复执行」的具体落地。

### 5.4 本项目当前状态

`/workspace/climber/frontend-react/playwright.config.ts`

```
11:   forbidOnly: IS_CI,
12:   retries: IS_CI ? 2 : 0,
13:   workers: 1,
...
25:     trace: 'on-first-retry',
26:     screenshot: 'only-on-failure',
27:     video: 'retain-on-failure',
29:   projects: [
30:     {
31:       name: 'chromium',
32:       use: { ...devices['Desktop Chrome'] },
33:       testIgnore: /.*mobile\.spec\.ts/,
34:     },
35:     {
36:       name: 'mobile',
37:       use: { ...devices['Pixel 7'] },
38:       testMatch: /.*mobile\.spec\.ts/,
39:     },
40:   ],
```

已具备：`forbidOnly`（11 行）、`retries` 条件化（12 行）、`workers: 1`（13 行）、trace/screenshot/video 失败留证（25–27 行）、chromium/mobile 双 project（29–40 行）、`webServer` 同时拉起 uvicorn 与 vite（41–59 行）。

缺失：`dependencies` 型环境准备 project（Cline 5 条）、按套件分档的 `retries`（LibreChat §5.2）。

---

## 6. 本项目结项验收清单

以下清单以任务 50 的验收标准为骨架，把 §2–§5 的做法落为本项目可执行项。**每项的完成定义统一为：命令、退出码、计数、日志路径、时间、验收者六项齐备并写回账本。**

### 6.1 门槛项（缺一不可结项）

| 编号 | 项目 | 落地做法 | 完成定义 |
| --- | --- | --- | --- |
| G-1 | 当前快照构建 | `npm run build`（`package.json:8`） | 退出码 0；`dist/` mtime 晚于最后一次 `src/` 改动；产物清单与体积记入账本 |
| G-2 | 全量单元测试 | `npx vitest run` | 退出码 0；文件数与用例数按本次实测记录，不引用旧审计数字 |
| G-3 | 静态检查 | `npm run typecheck`、`npm run lint` | 均退出码 0；warnings 逐项登记 |
| G-4 | 翻译一致性 | 修正 `scripts/check-translations.py:12` 的目录后重跑 | 退出码 0；覆盖 `src/locales`（512 键）而非 `public/locales`（328 键） |
| G-5 | 业务 E2E | `npx playwright test` | 退出码 0；含本轮已修改的 `e2e/02-agents.spec.ts` 与 `e2e/helpers.ts` |
| G-6 | 视觉回归 | 新增 `e2e/playwright.config.visual.ts` + `*.visual.spec.ts` | 12 组（2 主题 × 6 场景）基线在 Linux 上建立；结构断言在无基线时仍可执行 |
| G-7 | 性能基线 | 新增 `e2e/playwright.config.bench.ts` + `benchmarks/*.spec.ts` | 报告含 `host` 与 `raw` 字段；四条上界断言（详见 §3.2）有通过/失败结论 |
| G-8 | a11y 扫描 | 新增 `e2e/playwright.config.a11y.ts` + `a11y.spec.ts` | 全规则零违规；含 hover 展开态与弹层展开态 |
| G-9 | 六页补测 | TerminalPage、WorkflowsPage、NotificationsPage、DoctorPage、EvalPage、CostPage | 每页至少一个行为测试文件并在 V3 式全量运行中通过 |
| G-10 | 串行联调 | 配置模型→建会话→发送/停止→工具/权限→产物/错误恢复 | 复用 `scripts/acceptance-session-sync.cjs` 的骨架扩展；后端在线；每步记响应体 |

### 6.2 视觉回归基线管理细则

| 编号 | 项 | 做法来源 | 落地 |
| --- | --- | --- | --- |
| V-1 | 主题注入 + 落地断言 | LibreChat `message-visual.spec.ts:56-65` | `localStorage['climber-theme']` 注入（`useTheme.tsx:47`）后断言 `<html data-theme>`（`useTheme.tsx:71`） |
| V-2 | 快照前等字体 | LibreChat `message-visual.spec.ts:71-73` | `document.fonts.ready` |
| V-3 | 比对参数集中 | LibreChat `message-visual.spec.ts:29-34` | `animations: 'disabled'`、`caret: 'hide'`、`maxDiffPixels: 20`、`scale: 'css'` |
| V-4 | 平台固定 | LibreChat `message-visual.spec.ts:91` | `test.skip(process.platform !== 'linux')` |
| V-5 | 基线未就绪的降级 | LibreChat `message-visual.spec.ts:36-42` | `VISUAL_BASELINES_ENABLED` 开关；结构断言先行 |
| V-6 | API 夹具解耦 | CopilotKit `dashboard.spec.ts:69-78` | `page.route` 固定 `/api/v1/sessions` 等；断线态用 `route.abort` |
| V-7 | 截图前等确定标志 | CopilotKit `dashboard.spec.ts:91-94` | 等具体 `[data-status]` 落位，不等固定时长 |
| V-8 | 整页截图用比例容差 | CopilotKit `dashboard.spec.ts:97` | `maxDiffPixelRatio: 0.02` |
| V-9 | 差异人工签收 | 本项目任务 46 要求 | 失败 diff 图落 `test-results/`，账本记录每次容差调整理由 |
| V-10 | 令牌对比度交叉证据 | §4.4 | 对 `index.css:12-192`（暗）与 `218-260`（亮）的令牌对独立测量并落 JSON |

### 6.3 性能预算细则

| 编号 | 项 | 做法来源 | 落地 |
| --- | --- | --- | --- |
| P-1 | 冷样本分离 | LibreChat `agent-startup.latency.spec.ts:328` | 首样本记为 `cold`，不混入分位数 |
| P-2 | 预热可配 | LibreChat `:42,329-331` | `E2E_LATENCY_WARMUPS` 默认 5 |
| P-3 | p95 线性插值 | LibreChat `:91-96` | 采用同算法 |
| P-4 | 五统计量 | LibreChat `:100-106` | p50 / p95 / mean / min / max |
| P-5 | 机器指纹 | LibreChat `:350-355` | `logicalCpus`、前后 `loadAverage`、`cpuUtilizationPct` |
| P-6 | 原始样本留存 | LibreChat `:356-360` | `raw` 字段 |
| P-7 | 报告双落盘 | LibreChat `:298-310` | `testInfo.attach` + `E2E_LATENCY_OUTPUT` 文件 |
| P-8 | 渲染次数上界 | LibreChat `reasoning-stream.perf.spec.ts:195,206` | `renders < chunks / 4`。当前 `useChat.ts:100-171` 必然失败，需先做分片节流 |
| P-9 | 长任务三重阈值 | LibreChat `reasoning-stream.perf.spec.ts:215-217` | 单次 < 250ms；总时长 < 流式窗口 10%；脚本总执行 < 25% |
| P-10 | 输入期更严上界 | LibreChat `reasoning-stream.perf.spec.ts:234` | 渲染次数 ≤ 2；长任务 < 150ms；总时长 < 300ms |
| P-11 | 速率钉死 | LibreChat `playwright.config.reasoning-perf.ts:21-24` | SSE `delta` 间隔固定并注释「钉死而非默认」 |
| P-12 | 基准配置隔离 | LibreChat `playwright.config.benchmark.ts:20-24` | 独立 `testDir`、`outputDir`、`retries: 0`、放大 timeout |
| P-13 | 产物体积预算 | §3.5 缺口，需自建 | 记录 `dist/assets` 各 chunk 体积并设上限；当前无先例 |
| P-14 | 泄漏观测 | 本项目自定义 | 20 轮面板开合后监听器数与请求数不得超线性增长 |

### 6.4 a11y 细则

| 编号 | 项 | 做法来源 | 落地 |
| --- | --- | --- | --- |
| A-1 | 全规则零违规 | LibreChat `a11y.spec.ts:44` | `@axe-core/playwright` 需新增 devDependency；`expect(violations).toEqual([])` |
| A-2 | 加载后再扫 | LibreChat `a11y.spec.ts:29-34` | 等 composer/主标题可见，不等固定时长 |
| A-3 | 相对 baseURL 导航 | LibreChat `a11y.spec.ts:31` | 用 `page.goto('/')` |
| A-4 | 区域扫描 | LibreChat `a11y.spec.ts:65,73` | `include('nav')`、`include('form')`、`include('[role="dialog"]')` |
| A-5 | 悬停/展开态扫描 | LibreChat `a11y.spec.ts:89-90` | 会话行删除按钮、右栏 More 弹层、命令面板、全局搜索均需展开后扫描 |
| A-6 | 幂等夹具 | LibreChat `a11y.spec.ts:9-27` | 固定 ID + `beforeAll` 先删后插 + `afterAll` 清理 |
| A-7 | 独立配置 | LibreChat `playwright.config.a11y.ts:10,53,55` | `retries: 0`、`fullyParallel: false`、`testMatch: /a11y/` |
| A-8 | 补齐 axe 无法覆盖的项 | 本项目要求 | 纯键盘全流程、200% 缩放、读屏名称（`aria-label`/`aria-current` 逐页核对）、44px 触屏目标、对比度分档 |

A-8 需特别说明：axe-core 检查的是 DOM 语义违规，键盘全流程可达性、缩放后可见性、读屏实际播报顺序、触屏目标尺寸都需要人工或自定义脚本验证，工具无法替代。

### 6.5 E2E 稳定性细则

| 编号 | 项 | 做法来源 | 落地 |
| --- | --- | --- | --- |
| E-1 | `retries` 按套件分档 | LibreChat §5.2 | 主套件保留 `IS_CI ? 2 : 0`（`playwright.config.ts:12`）；a11y/visual/bench 三个新 config 统一 `retries: 0` |
| E-2 | 环境准备独立 project | Cline `playwright.config.ts:21-29` | 增设 `setup test environment` project 承载 `global.setup.ts`，用例 project 用 `dependencies` 引用 |
| E-3 | CI/本地超时分档 | Cline `:12,14` | 当前 `timeout: 30_000`（`playwright.config.ts:17`）不分档；按 CI 条件放大 |
| E-4 | 失败留证 | Cline `:19` | 已有 trace/screenshot/video（`playwright.config.ts:25-27`），确认 `outputDir` 不被 `globalTimeout` 清理 |
| E-5 | `forbidOnly` | Cline `:9` | 已有（`playwright.config.ts:11`） |
| E-6 | 幂等数据准备 | LibreChat `a11y.spec.ts:9-27` | 会话/智能体夹具统一固定 ID + 前后双清 |
| E-7 | 限流退避 | 本项目已有 | `e2e/helpers.ts:23-30` 对 429 做 4 次递增退避；需在其他创建路径统一复用 |
| E-8 | 选择器稳定性 | 本项目本轮变更 | `e2e/02-agents.spec.ts` 从 `[data-dropdown-trigger]` 改为 `button[aria-label]`（`.last()`）；应统一约定优先用 role/label，避免结构类选择器 |

E-8 反映了一个真实问题：本轮 E2E 选择器适配说明现有选择器与 DOM 结构耦合较紧。验收前应把关键定位收敛到 role/label/testid 三类，否则每次 UI 调整都会引发 E2E 假失败。

### 6.6 结项判定规则

| 规则 | 内容 |
| --- | --- |
| R-1 | 单元测试通过不构成浏览器验收。涉及布局、对比度、按键、读屏、触屏的任务，在真实浏览器记录写入前保留「待浏览器验收」 |
| R-2 | 单元测试通过不构成后端联调。涉及真实 API 字段、会话关联、审批副作用、SSE 实际流的任务，在后端可用并记录响应前保留「待后端联调」 |
| R-3 | 确定性检查（a11y、视觉、性能）`retries: 0`；其失败一次即为回归，需修复而非重跑 |
| R-4 | 性能数字必须带 `host` 与 `raw`；缺任一字段的数字不作为基线 |
| R-5 | 视觉基线只在声明的平台生成；容差调整需在账本记录理由 |
| R-6 | 每个门槛项的证据六要素齐备（命令、退出码、计数、日志路径、时间、验收者）才可标完成 |
| R-7 | 需要用户模型凭据的链路缺凭据时标阻塞，不以 mock 结果替代 |

---

## 7. 证据索引

| 仓库 | 文件 | 关键行 |
| --- | --- | --- |
| danny-avila_LibreChat | `e2e/specs/mock/message-visual.spec.ts` | 22-26, 29-34, 36-42, 55-66, 71-78, 91 |
| danny-avila_LibreChat | `e2e/specs/a11y.spec.ts` | 3, 9-27, 29-35, 42-44, 65, 73, 78-95 |
| danny-avila_LibreChat | `e2e/playwright.config.a11y.ts` | 10, 53, 55 |
| danny-avila_LibreChat | `e2e/playwright.config.benchmark.ts` | 8-16, 20-24 |
| danny-avila_LibreChat | `e2e/playwright.config.reasoning-perf.ts` | 20-24 |
| danny-avila_LibreChat | `e2e/benchmarks/agent-startup.latency.spec.ts` | 42-44, 69-79, 87-107, 298-310, 312-362 |
| danny-avila_LibreChat | `e2e/benchmarks-reasoning/reasoning-stream.perf.spec.ts` | 25-70, 192-217, 234, 248-252 |
| cline_cline | `apps/vscode/playwright.config.ts` | 6-31 |
| CopilotKit_CopilotKit | `showcase/shell-dashboard/tests/visual/dashboard.spec.ts` | 9, 65-85, 87-100 |
| langgenius_dify | `e2e/features/step-definitions/accessibility/axe.steps.ts`、`e2e/package.json` | 存在性核对 |

Climber 侧对照文件：`frontend-react/playwright.config.ts:11-59`、`frontend-react/e2e/helpers.ts:3-30`、`frontend-react/hooks/useTheme.tsx:47,68-74`、`frontend-react/src/index.css:6,218`、`frontend-react/package.json:14,34,66`。
