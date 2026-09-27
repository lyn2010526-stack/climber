/**
 * Product defects found by the visual matrix, recorded rather than fixed.
 *
 * The rule this suite follows is: a test never changes product code to make
 * itself pass, and a real defect never gets silently absorbed into a passing
 * suite. So each entry below is a reproducible, measured finding that the matrix
 * re-verifies on every run. The structural assertion stays in place; when the
 * defect is fixed, the probe reports `reachable: true`, the known-defect branch
 * stops matching and the normal hard assertion takes over.
 *
 * Fixing any of these means editing product code, which is a separate change
 * from establishing the baseline.
 */

export interface KnownDefect {
  /** Stable id, so a report line can be traced back to a finding. */
  id: string;
  /** Where in the product the fix belongs. */
  source: string;
  /** What a user experiences. */
  symptom: string;
  /** Which matrix rows it applies to. */
  scope: {
    page: string;
    /** Inclusive pixel-width range. */
    minWidth: number;
    maxWidth: number;
  };
  /**
   * Selectors of the controls that must be reachable. One entry can list several
   * when a single root cause covers them, which is the case for an overlay that
   * covers a whole composer row.
   */
  controls: string[];
}

export const KNOWN_DEFECTS: KnownDefect[] = [
  {
    id: 'UI-001',
    source: 'src/components/workspace/WorkspaceLayout.tsx:19-21,72-79',
    symptom:
      'The chat composer row, including the Send button and the message input, is covered by the ' +
      'Run inspector drawer at 768-1279px. ' +
      'rightPanelOpen defaults to true (src/store/workspace.ts:242) and useIsWideDesktop() only matches at ' +
      'WIDE_DESKTOP = 1280 (src/layout/breakpoints.ts), so between 768 and 1279 the right panel renders as an ' +
      'absolute z-20 overlay that spans the full column height including the composer row. A user on a ' +
      '1024x1024 or 768x1024 window cannot send a message until they first dismiss the drawer. The drawer also ' +
      'has no backdrop, so the covered composer gives no hint that it is inactive.',
    scope: { page: 'chat', minWidth: 768, maxWidth: 1279 },
    controls: ['button[aria-label="Send"]', 'textarea', 'input[placeholder]', '[contenteditable="true"]', 'button[type="submit"][aria-label]'],
  },
  {
    id: 'UI-002',
    source: 'src/App.tsx:253-264',
    symptom:
      'In the auto-collapsed 64px sidebar rail, the Language Settings control is wider than the rail, so it ' +
      'hangs outside the left viewport edge and reaches into the main content area. The rail is 64px wide ' +
      'while the control is about 97px, leaving roughly 17px off-screen and about 16px overlapping main. Only ' +
      'about 82% of the control stays visible, and the 44px touch height no longer matches the 44px width the ' +
      'collapsed layout assumes. The Theme Toggle beside it does fit (44x44 at x=9.5), so the overflow is ' +
      'specific to the language control.',
    scope: { page: 'rail', minWidth: 768, maxWidth: 1023 },
    controls: ['aside[aria-label="Main navigation"]'],
  },
];

export function findKnownDefect(options: {
  page: string;
  width: number;
  control: string;
}): KnownDefect | null {
  return (
    KNOWN_DEFECTS.find(
      defect =>
        defect.scope.page === options.page &&
        options.width >= defect.scope.minWidth &&
        options.width <= defect.scope.maxWidth &&
        defect.controls.includes(options.control),
    ) ?? null
  );
}

/** A known defect observed during a run, with the numbers that prove it. */
export interface KnownDefectFinding extends KnownDefect {
  /** The matrix combination that observed the defect. */
  title: string;
  width: number;
  height: number;
  theme: string;
  state: string | null;
  /** The hit test that failed, verbatim. */
  evidence: {
    centerX: number;
    centerY: number;
    topmost: string;
    targetName: string;
  };
}

export function formatKnownDefect(finding: KnownDefectFinding): string {
  return [
    `[${finding.id}] ${finding.symptom}`,
    `  source: ${finding.source}`,
    `  repro: /#${finding.scope.page} at ${finding.width}x${finding.height} (${finding.theme}` +
      `${finding.state ? `, state=${finding.state}` : ''})`,
    `  measured: ${finding.evidence.targetName} centre (${finding.evidence.centerX},${finding.evidence.centerY}) ` +
      `is covered by ${finding.evidence.topmost}`,
  ].join('\n');
}
