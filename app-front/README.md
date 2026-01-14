# N8N Ops - Frontend Application

A multi-tenant governance platform for managing n8n instances across different environments with DevOps, CI/CD, workflow lifecycle management, and observability features.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Components**: shadcn/ui + Tailwind CSS
- **State Management**:
  - TanStack Query (server state)
  - Zustand (client state)
- **Routing**: React Router v6
- **Auth**: Mock Auth (Auth0 ready)
- **Icons**: Lucide React
- **Notifications**: Sonner

## Features

### Core Modules

1. **Dashboard** - Overview of workflows, environments, and metrics
2. **Environments** - Manage dev, staging, and production n8n instances
3. **Workflows** - Import, sync, and manage workflow lifecycles
4. **Snapshots** - Version control with restore and diff capabilities
5. **Deployments** - CI/CD pipeline for workflow deployments
6. **Observability** - Runtime metrics and environment health monitoring
7. **Team** - User management and role-based access control
8. **Billing** - Subscription management via Stripe

## Getting Started

### Prerequisites

- Node.js 20.17.0 or higher
- npm 11.4.2 or higher

### Installation

1. Clone the repository and navigate to the frontend directory:
```bash
cd app-front
```

2. Install dependencies:
```bash
npm install
```

3. Create environment configuration:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration (optional for development)

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── components/       # Reusable React components
│   ├── ui/          # shadcn/ui components
│   └── AppLayout.tsx # Main application layout
├── pages/           # Route-level page components
│   ├── DashboardPage.tsx
│   ├── EnvironmentsPage.tsx
│   ├── WorkflowsPage.tsx
│   ├── SnapshotsPage.tsx
│   ├── DeploymentsPage.tsx
│   ├── ObservabilityPage.tsx
│   ├── TeamPage.tsx
│   └── BillingPage.tsx
├── lib/             # Utilities and core logic
│   ├── api-client.ts    # Axios API client
│   ├── mock-api.ts      # Mock API for development
│   ├── auth.tsx         # Authentication context
│   └── utils.ts         # Utility functions
├── store/           # Zustand state stores
│   └── use-app-store.ts
├── types/           # TypeScript type definitions
│   └── index.ts
├── App.tsx          # Main app component with routing
└── main.tsx         # Application entry point
```

## Authentication

The application currently uses **mock authentication** for development. Any email/password combination will work.

Default credentials shown on login page:
- Email: `demo@example.com`
- Password: `password`

### Auth0 Integration (Production Ready)

The app is ready for Auth0 integration. To enable:

1. Set up Auth0 tenant and application
2. Update `.env` with Auth0 credentials:
   ```
   VITE_AUTH0_DOMAIN=your-domain.auth0.com
   VITE_AUTH0_CLIENT_ID=your-client-id
   VITE_AUTH0_AUDIENCE=your-api-audience
   ```
3. Update `src/lib/auth.tsx` to use Auth0 SDK instead of mock auth

## API Integration

### Mock API (Current)

The application uses mock API responses defined in `src/lib/mock-api.ts` for development. This allows frontend development without a running backend.

### Real API Integration

To connect to a real n8n backend:

1. Update `VITE_API_BASE_URL` in `.env`
2. Ensure your backend implements the API contracts defined in the functional specification
3. The API client in `src/lib/api-client.ts` will automatically use the configured base URL

## Key Components

### Layouts

- **AppLayout** - Main application shell with sidebar navigation and top bar

### UI Components (shadcn/ui)

- Button, Card, Input, Label, Badge
- Table, Dialog, Tabs
- Toast notifications via Sonner

### State Management

- **TanStack Query** - Handles all server state (API calls, caching, refetching)
- **Zustand** - Manages client state (selected environment, sidebar state, theme)

### Routing

Protected routes require authentication. Unauthenticated users are redirected to `/login`.

## Development Guidelines

### Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/AppLayout.tsx`
4. Define types in `src/types/index.ts` if needed
5. Add API mock in `src/lib/mock-api.ts` if needed

### Adding a New API Endpoint

1. Define TypeScript types in `src/types/index.ts`
2. Add mock response in `src/lib/mock-api.ts`
3. Create TanStack Query hook in the relevant page:
   ```tsx
   const { data, isLoading } = useQuery({
     queryKey: ['key'],
     queryFn: () => mockApi.yourFunction(),
   });
   ```

### Styling

- Use Tailwind CSS utility classes
- Use shadcn/ui components for consistent UI
- Follow the existing color scheme (CSS variables in `index.css`)

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:5678` |
| `VITE_AUTH0_DOMAIN` | Auth0 domain (optional) | - |
| `VITE_AUTH0_CLIENT_ID` | Auth0 client ID (optional) | - |
| `VITE_AUTH0_AUDIENCE` | Auth0 API audience (optional) | - |

## License

MIT

## Support

For issues and questions, please refer to the main project documentation.
