import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:4000/api/v1';

// Default fixtures
export const mockUsers = [
  {
    id: 'user-1',
    email: 'admin@example.com',
    name: 'Admin User',
    tenant_id: 'tenant-1',
    role: 'admin',
  },
  {
    id: 'user-2',
    email: 'dev@example.com',
    name: 'Developer',
    tenant_id: 'tenant-1',
    role: 'developer',
  },
];

export const mockTenant = {
  id: 'tenant-1',
  name: 'Test Organization',
  subscription_tier: 'pro',
  status: 'active',
};

export const mockEntitlements = {
  plan_name: 'pro',
  features: {
    max_environments: { enabled: true, limit: 5 },
    max_team_members: { enabled: true, limit: 10 },
    workflow_ci_cd: { enabled: true },
    git_integration: { enabled: true },
    api_access: { enabled: true },
    environment_promotion: { enabled: true },
  },
};

export const mockEnvironments = [
  {
    id: 'env-1',
    tenant_id: 'tenant-1',
    n8n_name: 'Development',
    n8n_type: 'development',
    n8n_base_url: 'https://dev.n8n.example.com',
    is_active: true,
    workflow_count: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'env-2',
    tenant_id: 'tenant-1',
    n8n_name: 'Production',
    n8n_type: 'production',
    n8n_base_url: 'https://prod.n8n.example.com',
    is_active: true,
    workflow_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

export const mockWorkflows = [
  {
    id: 'wf-1',
    name: 'Test Workflow 1',
    active: true,
    environment_id: 'env-1',
    n8n_workflow_id: 'n8n-wf-1',
    tags: ['test', 'automation'],
    nodes: [
      { id: 'node-1', type: 'n8n-nodes-base.start', name: 'Start', position: [0, 0] },
      { id: 'node-2', type: 'n8n-nodes-base.httpRequest', name: 'HTTP Request', position: [200, 0] },
    ],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'wf-2',
    name: 'Test Workflow 2',
    active: false,
    environment_id: 'env-1',
    n8n_workflow_id: 'n8n-wf-2',
    tags: [],
    nodes: [],
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
];

export const mockPipelines = [
  {
    id: 'pipeline-1',
    tenant_id: 'tenant-1',
    name: 'Dev to Prod Pipeline',
    description: 'Promote workflows from development to production',
    is_active: true,
    environment_ids: ['env-1', 'env-2'],
    stages: [
      {
        source_environment_id: 'env-1',
        target_environment_id: 'env-2',
        gates: { require_clean_drift: true },
        approvals: { require_approval: true, approver_role: 'admin' },
      },
    ],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

export const handlers = [
  // Auth endpoints
  http.get(`${API_BASE}/auth/dev/users`, () => {
    return HttpResponse.json({ users: mockUsers });
  }),

  http.post(`${API_BASE}/auth/dev/login-as/:userId`, ({ params }) => {
    const user = mockUsers.find((u) => u.id === params.userId);
    if (!user) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      user,
      tenant: mockTenant,
    });
  }),

  http.get(`${API_BASE}/auth/status`, () => {
    return HttpResponse.json({
      authenticated: true,
      onboarding_required: false,
      has_environment: true,
      user: mockUsers[0],
      tenant: mockTenant,
      entitlements: mockEntitlements,
    });
  }),

  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json(mockUsers[0]);
  }),

  // Environment endpoints
  http.get(`${API_BASE}/environments`, () => {
    return HttpResponse.json(mockEnvironments);
  }),

  http.get(`${API_BASE}/environments/:id`, ({ params }) => {
    const env = mockEnvironments.find((e) => e.id === params.id);
    if (!env) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(env);
  }),

  http.post(`${API_BASE}/environments`, async ({ request }) => {
    const body = await request.json();
    const newEnv = {
      id: `env-${Date.now()}`,
      tenant_id: 'tenant-1',
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json(newEnv, { status: 201 });
  }),

  http.post(`${API_BASE}/environments/test-connection`, () => {
    return HttpResponse.json({ success: true, message: 'Connection successful' });
  }),

  http.post(`${API_BASE}/environments/:id/sync`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      message: 'Sync completed',
      results: {
        workflows: { synced: 5, errors: [] },
        executions: { synced: 10, errors: [] },
        credentials: { synced: 3, errors: [] },
        users: { synced: 2, errors: [] },
        tags: { synced: 4, errors: [] },
      },
    });
  }),

  // Workflow endpoints
  http.get(`${API_BASE}/workflows`, () => {
    return HttpResponse.json(mockWorkflows);
  }),

  http.get(`${API_BASE}/workflows/:id`, ({ params }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(workflow);
  }),

  http.post(`${API_BASE}/workflows/:id/activate`, ({ params }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...workflow, active: true });
  }),

  http.post(`${API_BASE}/workflows/:id/deactivate`, ({ params }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...workflow, active: false });
  }),

  http.put(`${API_BASE}/workflows/:id`, async ({ params, request }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    const body = await request.json();
    return HttpResponse.json({ ...workflow, ...body, updated_at: new Date().toISOString() });
  }),

  http.delete(`${API_BASE}/workflows/:id`, ({ params }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ success: true });
  }),

  http.put(`${API_BASE}/workflows/:id/tags`, async ({ params, request }) => {
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    const body = await request.json();
    return HttpResponse.json({ ...workflow, tags: body.tags || body });
  }),

  http.post(`${API_BASE}/workflows/sync-to-github`, () => {
    return HttpResponse.json({ success: true, synced: 2, skipped: 0, failed: 0 });
  }),

  // Execution endpoints
  http.get(`${API_BASE}/executions`, () => {
    return HttpResponse.json([
      { id: 'exec-1', workflowId: 'wf-1', status: 'success', startedAt: '2024-01-01T00:00:00Z' },
      { id: 'exec-2', workflowId: 'wf-1', status: 'success', startedAt: '2024-01-02T00:00:00Z' },
      { id: 'exec-3', workflowId: 'wf-2', status: 'error', startedAt: '2024-01-03T00:00:00Z' },
    ]);
  }),

  // Promotions endpoints
  http.get(`${API_BASE}/promotions`, () => {
    return HttpResponse.json([]);
  }),

  http.post(`${API_BASE}/promotions/initiate`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: `promo-${Date.now()}`,
      status: 'pending_approval',
      pipeline_id: body.pipeline_id,
      source_environment_id: body.source_environment_id,
      target_environment_id: body.target_environment_id,
      workflows: body.workflow_ids?.map((id: string) => ({ id, name: `Workflow ${id}` })) || [],
      gate_results: { all_passed: true },
      created_at: new Date().toISOString(),
    });
  }),

  http.post(`${API_BASE}/promotions/:id/approve`, ({ params }) => {
    return HttpResponse.json({ id: params.id, status: 'approved', approved_at: new Date().toISOString() });
  }),

  http.post(`${API_BASE}/promotions/:id/execute`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'completed',
      executed_at: new Date().toISOString(),
      results: { workflows_promoted: 2, errors: [] },
    });
  }),

  // Pipeline endpoints
  http.get(`${API_BASE}/pipelines`, () => {
    return HttpResponse.json(mockPipelines);
  }),

  http.get(`${API_BASE}/pipelines/:id`, ({ params }) => {
    const pipeline = mockPipelines.find((p) => p.id === params.id);
    if (!pipeline) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(pipeline);
  }),

  http.post(`${API_BASE}/pipelines`, async ({ request }) => {
    const body = await request.json();
    const newPipeline = {
      id: `pipeline-${Date.now()}`,
      tenant_id: 'tenant-1',
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json(newPipeline, { status: 201 });
  }),

  // Team endpoints
  http.get(`${API_BASE}/team/members`, () => {
    return HttpResponse.json(
      mockUsers.map((u) => ({
        ...u,
        created_at: '2024-01-01T00:00:00Z',
        status: 'active',
      }))
    );
  }),

  http.get(`${API_BASE}/team/limits`, () => {
    return HttpResponse.json({
      max_members: 10,
      current_members: 2,
      can_add_members: true,
    });
  }),

  // Deployments
  http.get(`${API_BASE}/deployments`, () => {
    return HttpResponse.json({
      deployments: [],
      total: 0,
      page: 1,
      page_size: 50,
      this_week_success_count: 0,
      pending_approvals_count: 0,
    });
  }),

  // Snapshots
  http.get(`${API_BASE}/snapshots`, () => {
    return HttpResponse.json([]);
  }),

  // Billing
  http.get(`${API_BASE}/billing/subscription`, () => {
    return HttpResponse.json({
      plan: 'pro',
      status: 'active',
      current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    });
  }),

  http.get(`${API_BASE}/billing/plans`, () => {
    return HttpResponse.json([
      { id: 'free', name: 'Free', price: 0 },
      { id: 'pro', name: 'Pro', price: 29 },
      { id: 'enterprise', name: 'Enterprise', price: 99 },
    ]);
  }),

  http.get(`${API_BASE}/billing/payment-history`, () => {
    return HttpResponse.json([]);
  }),

  // N8N Users endpoints
  http.get(`${API_BASE}/n8n-users`, () => {
    return HttpResponse.json({
      data: [
        {
          id: 'n8n-user-1',
          email: 'admin@example.com',
          first_name: 'Admin',
          last_name: 'User',
          role: 'owner',
          is_pending: false,
          environment: { id: 'env-1', name: 'Development', type: 'dev' },
          last_synced_at: '2024-01-15T10:00:00Z',
        },
        {
          id: 'n8n-user-2',
          email: 'member@example.com',
          first_name: 'Member',
          last_name: 'User',
          role: 'member',
          is_pending: false,
          environment: { id: 'env-1', name: 'Development', type: 'dev' },
          last_synced_at: '2024-01-14T10:00:00Z',
        },
      ],
      total: 2,
    });
  }),

  // Tags endpoints
  http.get(`${API_BASE}/tags`, () => {
    return HttpResponse.json([
      { id: 'tag-1', name: 'production', created_at: '2024-01-01T00:00:00Z' },
      { id: 'tag-2', name: 'staging', created_at: '2024-01-02T00:00:00Z' },
      { id: 'tag-3', name: 'automation', created_at: '2024-01-03T00:00:00Z' },
    ]);
  }),

  // Credentials endpoints
  http.get(`${API_BASE}/credentials`, () => {
    return HttpResponse.json([
      { id: 'cred-1', name: 'Slack API', type: 'slackApi', created_at: '2024-01-01T00:00:00Z' },
      { id: 'cred-2', name: 'GitHub Token', type: 'githubApi', created_at: '2024-01-02T00:00:00Z' },
    ]);
  }),

  // Dashboard stats
  http.get(`${API_BASE}/stats/dashboard`, () => {
    return HttpResponse.json({
      total_workflows: 10,
      active_workflows: 7,
      total_executions: 100,
      successful_executions: 85,
      failed_executions: 15,
    });
  }),

  // User profile update
  http.patch(`${API_BASE}/auth/me`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'user-1',
      ...body,
      updated_at: new Date().toISOString(),
    });
  }),
];

// Error handlers for testing error states
export const errorHandlers = {
  environments: {
    serverError: http.get(`${API_BASE}/environments`, () => {
      return new HttpResponse(JSON.stringify({ detail: 'Internal server error' }), {
        status: 500,
      });
    }),
    unauthorized: http.get(`${API_BASE}/environments`, () => {
      return new HttpResponse(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
      });
    }),
    forbidden: http.get(`${API_BASE}/environments`, () => {
      return new HttpResponse(JSON.stringify({ detail: 'Forbidden' }), {
        status: 403,
      });
    }),
  },
  workflows: {
    serverError: http.get(`${API_BASE}/workflows`, () => {
      return new HttpResponse(JSON.stringify({ detail: 'Internal server error' }), {
        status: 500,
      });
    }),
  },
  pipelines: {
    serverError: http.get(`${API_BASE}/pipelines`, () => {
      return new HttpResponse(JSON.stringify({ detail: 'Internal server error' }), {
        status: 500,
      });
    }),
  },
};
