import { apiClient } from './api-client';

// Always use live API client (no runtime mock data in dev/prod).
export const api = apiClient;
export { apiClient };
