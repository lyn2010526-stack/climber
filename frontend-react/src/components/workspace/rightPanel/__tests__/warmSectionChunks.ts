/**
 * Section modules are fetched the moment their group opens, and a cold module
 * graph turns that first fetch into a delay a test can mistake for a missing
 * result. Cases that assert on rendered section content warm the graph first;
 * the chunk gate keeps its own test file, where the first fetch is the subject.
 */
export async function warmSectionChunks(): Promise<void> {
  await Promise.all([
    import('../sections/ConfigSection'),
    import('../sections/ExecutionSection'),
    import('../sections/ChangesSection'),
    import('../sections/ActivitySection'),
  ]);
}
