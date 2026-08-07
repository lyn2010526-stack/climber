export const dashboardApi = {
  list: async () => [],
  get: async (id: string) => ({ id }),
  create: async (data: any) => data,
  update: async (id: string, data: any) => ({ id, ...data }),
  delete: async (id: string) => ({ success: true }),
};
